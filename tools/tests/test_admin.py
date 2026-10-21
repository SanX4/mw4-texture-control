"""Tests for running as administrator by default: the window relaunches itself elevated once (source runs), the packaged program asks in its manifest, setup starts it through
ShellExecute, and the helpers the elevated window started can still be stopped by setup. Nothing here elevates anything or touches the real settings."""
import contextlib, io, os, sys, unittest
from unittest import mock
import test_ccs                                    # sets CCS_WORK / CCS_HOSTS_PATH before ccslib is imported
sys.path.insert(0, test_ccs.TOOLS)
from ccslib import launch, procs, uninstall
import ccsgui

REPO = os.path.abspath(os.path.join(test_ccs.TOOLS, '..'))


def read(*p):
    with open(os.path.join(REPO, *p), encoding='utf-8') as f: return f.read()


class WhenToElevate(unittest.TestCase):
    def test_the_window_never_requires_elevation(self):
        for argv in ([],['--tab','Doctor'],['--selftest']):
            self.assertFalse(ccsgui.wants_elevation(argv,admin=False,env={}))

    def test_main_starts_normally_without_requesting_admin(self):
        with mock.patch.object(procs,'relaunch_elevated') as run, mock.patch.object(ccsgui,'App') as app, \
             mock.patch.object(ccsgui,'single_instance',return_value=True),mock.patch.object(ccsgui,'hold_mutex'):
            self.assertEqual(ccsgui.main([]),0)
        run.assert_not_called();app.assert_called_once()


class Packaging(unittest.TestCase):
    def test_only_the_window_asks_for_administrator_rights(self):
        spec = read('packaging', 'ccs.spec'); gui = next(l for l in spec.splitlines() if l.startswith('gui = EXE(')); cli = next(l for l in spec.splitlines() if l.startswith('cli = EXE('))
        self.assertIn('uac_admin=False', gui); self.assertNotIn('uac_admin', cli, 'the installer calls ccs-cli.exe as the current user: it must not need elevation')

    def test_setup_starts_the_program_through_shellexec_so_the_elevation_prompt_can_appear(self):
        line = next(l for l in read('packaging', 'installer.iss').splitlines() if l.startswith('Filename: "{app}\\{#AppExe}"') and 'postinstall' in l)
        self.assertIn('shellexec', line); self.assertIn('skipifsilent', line)

    def test_setup_installs_for_all_users_by_default_and_still_offers_the_current_user(self):
        iss = read('packaging', 'installer.iss'); self.assertRegex(iss, r'(?m)^PrivilegesRequired=admin$'); self.assertRegex(iss, r'(?m)^PrivilegesRequiredOverridesAllowed=dialog$')

    def test_the_build_tests_both_ways_of_installing(self):
        bat = read('packaging', 'build.bat'); self.assertIn('--current-user', bat); self.assertIn('--all-users', bat)
        ti = read('packaging', 'test_installer.py'); self.assertIn("'/ALLUSERS' if allusers else '/CURRENTUSER'", ti), self.assertIn('HKEY_LOCAL_MACHINE', ti)

    def test_the_build_checks_the_manifest(self):
        self.assertIn('requireAdministrator', read('packaging', 'build.py'))


class HelpersStartedByAnElevatedWindow(unittest.TestCase):
    def prep(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf): code = uninstall.main(list(args))
        return code, buf.getvalue()

    def test_stop_reports_what_really_happened_and_keeps_the_record_of_a_survivor(self):
        gone = []
        with mock.patch.object(procs, 'status', return_value=dict(alive=True, pid=4242)), mock.patch.object(procs.subprocess, 'run'), mock.patch.object(procs, 'ctime', return_value=123), \
                mock.patch.object(procs, '_clear', side_effect=gone.append):
            self.assertFalse(procs.stop('proxy', wait=0.2)); self.assertEqual(gone, [])
        with mock.patch.object(procs, 'status', return_value=dict(alive=True, pid=4242)), mock.patch.object(procs.subprocess, 'run'), mock.patch.object(procs, 'ctime', return_value=None), \
                mock.patch.object(procs, '_clear', side_effect=gone.append):
            self.assertTrue(procs.stop('proxy', wait=0.2)); self.assertEqual(gone, ['proxy'])

    def test_setup_asks_for_permission_when_a_helper_is_out_of_reach_and_then_succeeds(self):
        alive = {'proxy': True}
        def status(n): return dict(alive=alive.get(n, False))
        def elevated(argv, wait_s=120): alive['proxy'] = False; self.seen = argv; return 0
        with mock.patch.object(uninstall, 'helper_names', return_value=['proxy']), mock.patch.object(procs, 'stop', return_value=False), mock.patch.object(procs, 'status', side_effect=status), \
                mock.patch.object(procs, 'is_admin', return_value=False), mock.patch.object(procs, 'run_elevated', side_effect=elevated):
            code, out = self.prep('stop-helpers')
        self.assertEqual(code, 0); self.assertIn('stop-helpers', self.seen); self.assertIn('--work-dir',self.seen);self.assertIn('--hosts-file',self.seen); self.assertNotIn('still running', out)

    def test_declined_permission_and_a_survivor_are_reported_with_exit_codes(self):
        with mock.patch.object(uninstall, 'helper_names', return_value=['proxy']), mock.patch.object(procs, 'stop', return_value=False), mock.patch.object(procs, 'status', return_value=dict(alive=True)), \
                mock.patch.object(procs, 'is_admin', return_value=False), mock.patch.object(procs, 'run_elevated', return_value=None):
            code, out = self.prep('stop-helpers'); self.assertEqual(code, 3); self.assertIn('declined', out)
        with mock.patch.object(uninstall, 'helper_names', return_value=['proxy']), mock.patch.object(procs, 'stop', return_value=False), mock.patch.object(procs, 'status', return_value=dict(alive=True)), \
                mock.patch.object(procs, 'is_admin', return_value=True), mock.patch.object(procs, 'run_elevated') as run:
            code, out = self.prep('stop-helpers'); self.assertEqual(code, 1); self.assertIn('still running: proxy', out); run.assert_not_called()

    def test_nothing_to_stop_is_quiet_and_asks_for_nothing(self):
        with mock.patch.object(uninstall, 'helper_names', return_value=[]), mock.patch.object(procs, 'run_elevated') as run:
            code, out = self.prep('stop-helpers'); self.assertEqual(code, 0); self.assertIn('nothing', out); run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
