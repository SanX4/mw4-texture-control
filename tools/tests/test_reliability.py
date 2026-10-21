"""Recovery and offline HTTP regressions, using disposable local fixtures only."""
import copy
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock

import test_ccs
import ccsproxy
from ccslib import config, connection, hosts, paths, procs, session


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.hosts = self.root / 'hosts'
        self.prior = b'# local\r\n127.0.0.1 localhost\r\n'
        self.hosts.write_bytes(self.prior)
        self.env = mock.patch.dict(os.environ, CCS_HOSTS_PATH=str(self.hosts))
        self.env.start()
        self.cfg = copy.deepcopy(config.DEFAULTS)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_rollback_restores_exact_bytes(self):
        result = hosts.apply(flush=False)
        hosts.rollback_attempt(result['backup'], result['applied_sha256'], flush=False)
        self.assertEqual(self.hosts.read_bytes(), self.prior)

    def test_rollback_preserves_intervening_edits(self):
        result = hosts.apply(flush=False)
        self.hosts.write_bytes(self.hosts.read_bytes() + b'# added elsewhere\r\n')
        current = self.hosts.read_bytes()
        with self.assertRaisesRegex(hosts.HostsError, 'changed since startup'):
            hosts.rollback_attempt(result['backup'], result['applied_sha256'], flush=False)
        self.assertEqual(self.hosts.read_bytes(), current)

    def test_busy_port_never_changes_hosts(self):
        with mock.patch.object(paths, 'validate', return_value=[]), \
             mock.patch.object(paths, 'reload'), \
             mock.patch.object(session.shutil, 'disk_usage', return_value=types.SimpleNamespace(free=20*2**30)), \
             mock.patch.object(procs, 'status', return_value={'alive': False}), \
             mock.patch.object(procs, 'port_owner', return_value=[dict(name='busy', pid=42)]), \
             mock.patch.object(session, 'hosts_cmd') as helper:
            ok, message = session.start(self.cfg, lambda _: None)
        self.assertFalse(ok)
        self.assertIn('already in use', message)
        helper.assert_not_called()
        self.assertEqual(self.hosts.read_bytes(), self.prior)

    def test_failed_start_stops_only_its_helpers_and_rolls_back(self):
        alive = {'proxy': True, 'guard': True, 'mirror': True}
        stopped = []
        def fail(cfg, say, attempt):
            attempt['started'].add('proxy')
            attempt['hosts'] = dict(backup='backup', applied_sha256='abc')
            return False, 'proxy not ready'
        # An existing proxy means no temporary bind is needed for preflight.
        with mock.patch.object(paths, 'validate', return_value=[]), mock.patch.object(paths, 'reload'), \
             mock.patch.object(session.shutil, 'disk_usage', return_value=types.SimpleNamespace(free=20*2**30)), \
             mock.patch.object(procs, 'status', side_effect=lambda n:dict(alive=alive.get(n, False))), \
             mock.patch.object(procs, 'stop', side_effect=lambda n:stopped.append(n) or True), \
             mock.patch.object(session, '_start', side_effect=fail), \
             mock.patch.object(session, 'hosts_cmd', return_value=(True, {})) as helper:
            ok, message = session.start(self.cfg, lambda _: None)
        self.assertFalse(ok)
        self.assertEqual(stopped, ['proxy'])
        self.assertEqual(helper.call_args.args[0], 'rollback')
        self.assertIn('undone', message)

    def test_real_startup_failure_recovers_hosts_and_new_proxy(self):
        alive={'proxy':False}
        self.cfg['proxy']['port']=test_ccs.free_port()
        def helper(command,say,extra=()):
            if command=='apply': return True,dict(hosts.apply(flush=False),state='OK')
            return True,hosts.rollback_attempt(extra[0],extra[2],flush=False)
        def start_proxy(cfg): alive['proxy']=True
        def stop_proxy(name):alive[name]=False;return True
        with mock.patch.object(paths,'validate',return_value=[]),mock.patch.object(paths,'reload'), \
             mock.patch.object(procs,'status',side_effect=lambda n:dict(alive=alive.get(n,False))), \
             mock.patch.object(procs,'port_owner',return_value=[]),mock.patch.object(procs,'image_running',return_value=True), \
             mock.patch.object(procs,'stop',side_effect=stop_proxy), \
             mock.patch.object(hosts,'resolve_check',return_value=dict(ok=False)), \
             mock.patch.object(session.upstream,'system_edges',return_value=[]), \
             mock.patch.object(session,'hosts_cmd',side_effect=helper), \
             mock.patch.object(session.proxyctl,'start_proxy',side_effect=start_proxy), \
             mock.patch.object(session,'_wait_proxy_ready',return_value=(False,'proxy readiness failed')):
            ok,message=session.start(self.cfg,lambda _:None)
        self.assertFalse(ok);self.assertFalse(alive['proxy'])
        self.assertEqual(self.hosts.read_bytes(),self.prior)

    def test_preexisting_hosts_override_survives_failed_start(self):
        hosts.apply(flush=False); prior=self.hosts.read_bytes()
        def fail(cfg,say,attempt):return False,'No new changes'
        with mock.patch.object(paths,'validate',return_value=[]),mock.patch.object(paths,'reload'), \
             mock.patch.object(procs,'status',return_value=dict(alive=True)), \
             mock.patch.object(session,'_start',side_effect=fail),mock.patch.object(session,'hosts_cmd') as helper:
            self.assertFalse(session.start(self.cfg,lambda _:None)[0])
        helper.assert_not_called();self.assertEqual(self.hosts.read_bytes(),prior)

    def test_context_survives_an_environment_free_helper_launch(self):
        result = self.root / 'result.json'
        work = self.root / 'work'
        env = {k:v for k,v in os.environ.items() if not k.startswith('CCS_')}
        argv = [sys.executable, str(Path(test_ccs.TOOLS)/'ccshosts.py'), 'apply', '--no-flush',
                '--hosts-file', str(self.hosts), '--work-dir', str(work), '--result-file', str(result)]
        p = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
        data = json.loads(result.read_text())
        self.assertTrue(data['ok'])
        self.assertEqual(Path(data['backup']).parent, work/'hosts-backups')
        self.assertIn(hosts.BEGIN.encode(), self.hosts.read_bytes())

    def test_stop_streaming_keeps_downloads_and_stop_all_stops_them(self):
        for everything in (False, True):
            stopped = []
            with mock.patch.object(procs, 'stop', side_effect=lambda n:stopped.append(n) or True), \
                 mock.patch.object(procs, 'status', return_value=dict(alive=True)), \
                 mock.patch.object(hosts, 'status', return_value=dict(state='ABSENT')):
                session.stop(self.cfg, lambda _:None, everything=everything)
            self.assertEqual('mirror' in stopped, everything)


class OfflineRangeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.body = b'0123456789'
        self.path = '/pc/iw9_3/23/01/0000000000000001_0000000a_0'
        obj = self.root/'objects'/'01'/'0000000000000001_0000000a_0'
        obj.parent.mkdir(parents=True)
        obj.write_bytes(self.body)
        self.saved = (ccsproxy.LOG, dict(ccsproxy.RAW), dict(ccsproxy.MKEY))
        ccsproxy.LOG = str(self.root/'proxy.log')
        ccsproxy.RAW.clear(); ccsproxy.MKEY[1] = ('test-etag', 'key')
        self.server = ccsproxy.S4(('127.0.0.1', 0), ccsproxy.H)
        self.server.args = types.SimpleNamespace(origin=str(self.root), offline=True, max_raw_mib=4096,
                budget_gib=120, pause_file=str(self.root/'pause'), retries=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        ccsproxy.LOG = self.saved[0]
        ccsproxy.RAW.clear(); ccsproxy.RAW.update(self.saved[1])
        ccsproxy.MKEY.clear(); ccsproxy.MKEY.update(self.saved[2])
        self.tmp.cleanup()

    def request(self, headers=None, method='GET', path=None):
        c = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        c.request(method, path or self.path, headers=headers or {})
        r = c.getresponse(); data = r.read(); code = r.status; hdr = dict(r.getheaders()); c.close()
        return code, hdr, data

    def test_bounded_open_ended_and_suffix_ranges(self):
        for value, expected, header in [('bytes=2-5', b'2345', 'bytes 2-5/10'),
                 ('bytes=7-', b'789', 'bytes 7-9/10'), ('bytes=-3', b'789', 'bytes 7-9/10'),
                 ('bytes=8-99', b'89', 'bytes 8-9/10')]:
            code, headers, body = self.request({'Range':value})
            self.assertEqual((code, body, headers['Content-Range']), (206, expected, header))
            self.assertEqual(headers['Content-Length'], str(len(expected)))

    def test_unsatisfiable_range(self):
        code, headers, body = self.request({'Range':'bytes=10-'})
        self.assertEqual((code, headers['Content-Range'], body), (416, 'bytes */10', b''))

    def test_head_ignores_range_and_reports_full_length(self):
        before=ccsproxy.stat['local']
        code, headers, body = self.request({'Range':'bytes=2-5'}, method='HEAD')
        self.assertEqual(ccsproxy.stat['local'],before)
        self.assertEqual((code, headers['Content-Length'], body), (200, '10', b''))

    def test_if_range_match_and_mismatch(self):
        self.assertEqual(self.request({'Range':'bytes=2-5','If-Range':'"test-etag"'})[0], 206)
        for validator in ('"stale"', 'W/"test-etag"'):
            code, headers, body = self.request({'Range':'bytes=2-5','If-Range':validator})
            self.assertEqual((code, body), (200, self.body))

    def test_multiple_or_malformed_ranges_are_ignored(self):
        for value in ('bytes=0-1,4-5', 'bytes=oops', 'bytes=7-2'):
            self.assertEqual(self.request({'Range':value})[::2], (200, self.body))

    def test_disk_pause_refuses_new_transfers_then_recovers(self):
        flag = self.root/'pause'; flag.write_text('{}')
        self.assertEqual(self.request()[0], 503)
        flag.unlink()
        self.assertEqual(self.request()[::2], (200, self.body))

    def test_missing_offline_object_never_contacts_upstream(self):
        code, _, body = self.request(path=self.path.replace('_0000000a_', '_0000000b_'))
        self.assertEqual((code, body), (404, b''))


class DiskProtectionTests(unittest.TestCase):
    def test_pause_marks_transfers_and_downloads_and_clears_after_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); cache=root/'cache';cache.mkdir(); chunk=cache/'chunk';chunk.write_bytes(b'x'*2048)
            flag=root/'paused.json';stop=root/'STOP';status=root/'guard.json'
            work=root/'work';work.mkdir();(work/'gui_settings.json').write_text(json.dumps(dict(paths=dict(game_root=str(root),kill_exes='MW4-TEST-NONEXISTENT.exe'))))
            p=subprocess.Popen([sys.executable, str(Path(test_ccs.TOOLS)/'diskguard.py'), '--limit-gib','0.000001',
                '--interval','0.1','--cache',str(cache),'--pause-file',str(flag),'--mirror-stop-file',str(stop),
                '--status-json',str(status),'--log',str(root/'guard.log')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=dict(os.environ,CCS_WORK=str(work)))
            try:
                deadline=time.monotonic()+10
                while not (flag.exists() and stop.exists() and status.exists()) and time.monotonic()<deadline:time.sleep(.05)
                self.assertTrue(flag.exists());self.assertTrue(stop.exists())
                self.assertEqual(json.loads(status.read_text())['action'],'pause')
                self.assertIsNone(p.poll(), 'pause must keep the guard alive')
                chunk.unlink();deadline=time.monotonic()+5
                while flag.exists() and time.monotonic()<deadline:time.sleep(.05)
                self.assertFalse(flag.exists())
            finally:p.terminate();p.wait(5)

    def test_legacy_kill_requires_explicit_confirmation(self):
        cfg=copy.deepcopy(config.DEFAULTS);cfg['guard']['action']='kill'
        self.assertEqual(config.effective(cfg)['guard']['action'],'pause')
        cfg['guard']['force_close_confirmed']=True
        self.assertEqual(config.effective(cfg)['guard']['action'],'kill')

    def test_diagnostics_distinguish_fallback_and_last_delivery(self):
        data=dict(pproc=dict(alive=True),pstat=dict(connection=dict(active_cdn='192.0.2.1',fallback=True,
            last_success=dict(ts=100,source='mirror'),last_failure=dict(ts=101,reason='Connection reset'))))
        rows=connection.rows(data)
        self.assertEqual(rows[0]['value'],'192.0.2.1')
        self.assertIn('Yes',rows[1]['value'])
        self.assertTrue(any('Connection reset' in r['value'] for r in rows))


if __name__ == '__main__': unittest.main()
