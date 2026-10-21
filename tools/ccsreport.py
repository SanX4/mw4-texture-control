#!/usr/bin/env python3
"""ccsreport - analyse a proxy run from tools/work/ccsproxy.log and write tools/work/sessions/<run>.md/.json

  python tools/ccsreport.py --list                       # runs found in the log
  python tools/ccsreport.py [--segment N|last] [--baseline FILE] [--from HH:MM:SS --to HH:MM:SS] [--no-post] [--no-save] [--log PATH]

--baseline: engine-cache id snapshot taken before the run (the GUI saves one at session start; for the old run 3 use tools/work/e3_baseline_index.json).
Without --no-post the current xpak_cache is snapshotted as the "after" state (close the game first for a consistent read).
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ccslib import report, paths


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--list', action='store_true'); ap.add_argument('--segment', default='last'); ap.add_argument('--log'); ap.add_argument('--baseline')
    ap.add_argument('--date', help='YYYY-MM-DD for runs from before the log had START lines (old runs only have a time of day)')
    ap.add_argument('--from', dest='t_from', help='HH:MM:SS: analyse only one game launch inside the run (start of the launch)'); ap.add_argument('--to', dest='t_to', help='HH:MM:SS: end of that launch')
    ap.add_argument('--no-post', action='store_true'); ap.add_argument('--no-save', action='store_true'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    segs = report.segments(a.log)
    if a.list or not segs:
        for s in segs: print(f"#{s['idx']:<3} {s.get('date') or '----------'} {s['first']}-{s['last']}  requests={s['nreq']}")
        if not segs: print('no runs found in the log')
        return 0
    seg = segs[-1] if a.segment == 'last' else segs[int(a.segment)]
    if a.date: seg['date'] = a.date
    window = None
    if a.t_from and a.t_to and seg.get('date'):
        import datetime
        def ep(hms, plus=0): return datetime.datetime.strptime(seg['date'] + ' ' + hms, '%Y-%m-%d %H:%M:%S').timestamp() + plus
        window = (ep(a.t_from), ep(a.t_to)); window = (window[0], window[1] + (86400 if window[1] < window[0] else 0))
    base = report.load_snapshot(a.baseline) if a.baseline else (report.baseline_for(seg, t0=window[0]) if window else report.baseline_for(seg))
    post = None if a.no_post else report.snapshot_cache()
    rep = report.build(seg, mirror_ids=report.load_mirror_ids(), baseline=base, post=post, window=window)
    prev = report.previous_report(rep)
    md = report.to_markdown(rep, prev)
    print(json.dumps(rep, indent=1) if a.json else md)
    if not a.no_save:
        m, j = report.save(rep, prev); print('saved', m, j, file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
