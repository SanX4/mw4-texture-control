"""session.py - start/stop orchestration shared by the GUI (and usable from scripts).

start(): hosts override -> proxy (wait for READY) -> diskguard -> optional netwatch -> doctor
stop():  diskguard + proxy (+ hosts per policy)
`say(msg)` is a callback for progress lines. Hosts writes go through tools/ccshosts.py elevated via UAC.
"""
import json, os, shutil, socket, subprocess, sys, time, uuid
from . import config, doctor, hosts, launch, logrot, paths, procs, proxyctl, upstream

SESSION_FILE = lambda: os.path.join(paths.RUN, 'session.json')


def hosts_cmd(cmd, say=print, extra=()):
    """Run ccshosts.py <cmd> elevated (UAC unless already admin). -> (ok, result dict)"""
    paths.ensure_dirs(); rf = os.path.join(paths.RUN, 'hosts-result-' + uuid.uuid4().hex + '.json')
    try: os.remove(rf)
    except OSError: pass
    say(f'hosts: {cmd} (UAC prompt may appear)')
    code = procs.run_elevated(launch.argv_for('ccshosts', cmd, *extra, '--result-file', rf, *paths.helper_context_args()))
    if code is None: return False, dict(error='UAC declined')
    try: res = json.load(open(rf, encoding='utf-8'))
    except Exception: return False, dict(error=f'no result from elevated helper (exit {code})')
    return bool(res.get('ok')), res


def _wait_proxy_ready(port, say, timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not procs.status('proxy')['alive']:
            tail = '\n'.join(procs.tail_lines(proxyctl.PROXY_LOG, 5)); return False, 'proxy exited during startup:\n' + tail
        if proxyctl.fetch_stats(port, timeout=1.0): return True, 'READY'
        time.sleep(0.5)
    return False, f'proxy not ready after {timeout}s'


def _start(cfg, say, attempt):
    """-> (ok, summary). Stops at the first hard failure; everything started so far stays up (Stop session cleans up)."""
    paths.ensure_dirs(); paths.reload(); eff = config.effective(cfg); port = eff['proxy']['port']
    bad = [r for r in paths.validate() if r['level'] == 'fail']
    if bad: return False, 'setup needed - ' + '; '.join(f"{r['name']}: {r['detail']}" for r in bad) + '  (Game tab -> Locations)'
    try: upstream.system_edges() and upstream.remember(upstream.system_edges())      # nearest edge, while the system resolver still gives it (the override hides it)
    except Exception: pass
    st = hosts.status()['state']; rc = hosts.resolve_check()
    if st in ('FOREIGN', 'MIXED') and rc['ok']:
        say(f'hosts: override active as {st} lines (works; use Hosts tab -> Apply to adopt them into the managed block)')
    elif st != 'OK' or not rc['ok']:
        if st == 'OK' and not rc['ok']: say(f"hosts: block present but resolver returns v4={rc['v4']} v6={rc['v6']} - flushing DNS")
        ok, res = hosts_cmd('apply', say)
        if not ok: return False, f"hosts override not applied: {res.get('error')}"
        if res.get('changed'): attempt['hosts'] = res
        say(f"hosts: {res.get('state')} (backup {res.get('backup')})")
    else:
        say('hosts: override already present')
    owners = procs.port_owner(port)
    if owners and not procs.status('proxy')['alive']:
        return False, f'port {port} already in use by ' + ', '.join(f"{o['name']} (pid {o['pid']})" for o in owners)
    if procs.status('proxy')['alive'] and not proxyctl.fetch_stats(port):
        say('proxy process alive but not answering - restarting'); procs.stop('proxy')
    if not procs.status('proxy')['alive']:
        try:
            alive = [logname for proc, logname in (('proxy', 'ccsproxy.log'), ('guard', 'diskguard.log'), ('mirror', 'ccsmirror.log'), ('netwatch', 'netwatch.log')) if procs.status(proc)['alive']]
            rot = logrot.rotate_all(cfg.get('log_max_mb', 25), skip_running=alive)
            if rot: say('log rotation: ' + ', '.join(rot) + f" (>{cfg.get('log_max_mb', 25)} MB; older copies kept as .1/.2/.3)")
        except Exception as e: say(f'log rotation skipped: {e}')
        if not procs.image_running(*paths.GAME_EXES):
            try:   # engine-cache id snapshot = the "before" state for the session report (re-request rate, growth)
                from . import report
                snap = report.snapshot_cache(); bp = os.path.join(paths.SESSIONS, time.strftime('baseline-%Y%m%d-%H%M%S.json')); report.save_snapshot(snap, bp)
                say(f"cache baseline: {snap['records']} records / {snap['unique']} unique ids saved")
            except Exception as e: say(f'cache baseline skipped: {e}')
        else: say('game is running - cache baseline skipped (report will have no re-request rate)')
        say('proxy: starting ' + ' '.join(os.path.basename(x) if i < 2 else x for i, x in enumerate(proxyctl.proxy_argv(cfg))))
        attempt['started'].add('proxy'); proxyctl.start_proxy(cfg)
    ok, msg = _wait_proxy_ready(port, say)
    if not ok: return False, msg
    say('proxy: READY')
    if eff['guard']['enabled']:
        if procs.status('guard')['alive']: say('diskguard: already running')
        else: attempt['started'].add('guard'); proxyctl.start_guard(cfg); say(f"diskguard: started (limit {eff['guard']['limit_gib']:g} GiB, action {eff['guard']['action']}, cache {paths.XPAK_CACHE})")
    if eff['watchers'].get('netwatch') and not procs.status('netwatch')['alive']:
        attempt['started'].add('netwatch'); procs.start('netwatch', launch.argv_for('netwatch', 7200), os.path.join(paths.RUN, 'netwatch.out')); say('netwatch: started')
    json.dump(dict(started=time.time(), profile=cfg.get('profile'), argv=proxyctl.proxy_argv(cfg)), open(SESSION_FILE(), 'w', encoding='utf-8'))
    res = doctor.run_all(cfg); say(doctor.format_results(res))
    bad = [r for r in res if r['level'] == 'fail']
    return (not bad), ('session running' if not bad else f"{len(bad)} check(s) failed: " + ', '.join(r['name'] for r in bad))


def start(cfg, say=print):
    """Preflight first; recover only changes and helpers owned by this attempt."""
    paths.ensure_dirs(); paths.reload(); eff = config.effective(cfg); port = eff['proxy']['port']
    bad = [r for r in paths.validate() if r['level'] == 'fail']
    if bad: return False, 'setup needed - ' + '; '.join(r['detail'] for r in bad)
    if shutil.disk_usage(paths.GAME_ROOT).free < 2 * 2**30:
        return False, 'Not enough free disk space: free at least 2 GiB before starting.'
    if not procs.status('proxy')['alive']:
        owners = procs.port_owner(port)
        if owners: return False, f'port {port} already in use by ' + ', '.join(o['name'] for o in owners)
        sockets = []
        try:
            for family, address in ((socket.AF_INET, '127.0.0.1'), (socket.AF_INET6, '::1')):
                sock = socket.socket(family, socket.SOCK_STREAM); sockets.append(sock)
                if family == socket.AF_INET6: sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'): sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                sock.bind((address, port))
        except OSError as e: return False, f'port {port} cannot be opened: {e}'
        finally:
            for sock in sockets: sock.close()
    attempt = dict(started=set(), hosts=None)
    previous = None
    try:
        with open(SESSION_FILE(), 'rb') as f: previous = f.read()
    except OSError: pass
    try: ok, message = _start(cfg, say, attempt)
    except Exception as e: ok, message = False, f'Startup failed: {e}'
    if ok: return True, message
    recovery = []
    for name in ('netwatch', 'guard', 'proxy'):
        if name in attempt['started'] and procs.status(name)['alive'] and not procs.stop(name):
            recovery.append(f'{name} could not be stopped')
    change = attempt['hosts']
    if change:
        try:
            restored, result = hosts_cmd('rollback', say, (change['backup'], '--expected-sha256', change['applied_sha256']))
            if not restored: recovery.append(result.get('error', 'hosts recovery failed'))
        except Exception as e: recovery.append(str(e))
    try:
        if previous is not None:
            with open(SESSION_FILE(), 'wb') as f: f.write(previous)
        elif os.path.exists(SESSION_FILE()): os.remove(SESSION_FILE())
    except OSError as e: recovery.append(f'session record: {e}')
    suffix = ' Recovery needs attention: ' + '; '.join(recovery) if recovery else ' Startup changes were undone.'
    say(message + suffix)
    return False, message + suffix


def stop(cfg, say=print, everything=False):
    """Stop tools. Returns dict(hosts_active=bool) so the caller can apply the on_exit policy (ask / keep / remove)."""
    names = ('netwatch', 'guard', 'proxy', 'mirror', 'mirror-verify', 'mirror-init', 'mirror-prune') if everything else ('netwatch', 'guard', 'proxy')
    for n in names:
        if procs.stop(n): say(f'{n}: stopped')
    try: os.remove(SESSION_FILE())
    except OSError: pass
    if not everything and procs.status('mirror')['alive']: say('Offline downloads are still running. Use Pause downloads or Stop everything to stop them.')
    active = hosts.status()['state'] != 'ABSENT'
    return dict(hosts_active=active)


def run_fix(cfg, fix, say=print):
    """Apply a Doctor fix (action, arg). -> (ok, message). Callers confirm destructive ones (kill_port_owner) first."""
    act, arg = fix; port = config.effective_proxy(cfg)['port']
    if act == 'hosts_apply':
        ok, res = hosts_cmd('apply', say); return ok, res.get('error') or f"hosts state {res.get('state')}"
    if act == 'flush_dns':
        ok, res = hosts_cmd('flush', say); return ok, res.get('error') or ('flushed' if res.get('flushed') else 'flush reported failure')
    if act in ('start_proxy', 'restart_proxy'):
        if act == 'restart_proxy': procs.stop('proxy')
        proxyctl.start_proxy(cfg); return _wait_proxy_ready(port, say)
    if act == 'game_fix':
        from . import gamefix; return gamefix.apply_elevating(say=say)
    if act == 'game_undo':
        from . import gamefix; return gamefix.undo_elevating(say=say)
    if act == 'kill_port_owner':
        for pid, name in arg:
            r = subprocess.run(['taskkill', '/PID', str(pid), '/F'], capture_output=True, text=True, errors='replace', creationflags=procs.CREATE_NO_WINDOW)
            say(f'killed {name} pid {pid}: ' + ('ok' if r.returncode == 0 else (r.stdout + r.stderr).strip()))
        return True, 'port owner(s) terminated'
    return False, f'unknown fix {act}'


def session_info():
    try: return json.load(open(SESSION_FILE(), encoding='utf-8'))
    except Exception: return None
