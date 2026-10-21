"""bundle.py - one-click support bundle: everything needed to analyse a run, in a single zip (tools/work/bundles/)."""
import json, os, platform, sys, time, zipfile
from . import config, doctor, hosts, paths, procs, proxyctl, report


def _tail(path, n=20000):
    return '\n'.join(procs.tail_lines(path, n))


def make(cfg=None):
    cfg = cfg or config.load(); out_dir = os.path.join(paths.WORK, 'bundles'); os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, time.strftime('ccs-support-%Y%m%d-%H%M%S.zip'))
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, p in (('proxy.log', proxyctl.PROXY_LOG), ('diskguard.log', proxyctl.GUARD_LOG), ('ccsmirror.log', proxyctl.MIRROR_LOG), ('ccsgui.log', os.path.join(paths.WORK, 'ccsgui.log')),
                        ('netwatch.log', os.path.join(paths.WORK, 'netwatch.log'))):
            if os.path.exists(p): z.writestr('logs/' + name, _tail(p))
        for fn in (proxyctl.PROXY_STATS, proxyctl.GUARD_STATS, os.path.join(paths.RUN, 'session.json'), os.path.join(paths.WORK, 'gui_settings.json')):
            if os.path.exists(fn): z.write(fn, 'state/' + os.path.basename(fn))
        try:
            st = hosts.status(); z.writestr('state/hosts.txt', json.dumps(dict(state=st['state'], block=st['block'], foreign=st['foreign'], resolver=hosts.resolve_check()), indent=1))
            z.writestr('state/hosts-file.txt', hosts.read()[0])
        except Exception as e: z.writestr('state/hosts.txt', f'error: {e}')
        try: z.writestr('state/doctor.txt', doctor.format_results(doctor.run_all(cfg)))
        except Exception as e: z.writestr('state/doctor.txt', f'error: {e}')
        z.writestr('state/processes.json', json.dumps({n: procs.status(n) for n in ('proxy', 'guard', 'netwatch')}, indent=1, default=str))
        z.writestr('state/env.txt', f'python {sys.version}\n{platform.platform()}\nadmin={procs.is_admin()}\ngame={procs.image_running(*paths.GAME_EXES)}\n')
        z.writestr('state/player_config.json', json.dumps(report.player_config(), indent=1))
        z.writestr('state/runs.txt', '\n'.join(f"#{s['idx']} {s.get('date')} {s['first']}-{s['last']} requests={s['nreq']}" for s in report.segments()))
        for fn in report.list_reports()[-3:]:
            z.write(fn, 'reports/' + os.path.basename(fn)); md = fn[:-5] + '.md'
            if os.path.exists(md): z.write(md, 'reports/' + os.path.basename(md))
    return out
