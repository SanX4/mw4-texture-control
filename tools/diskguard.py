#!/usr/bin/env python3
"""diskguard - protect free disk space during a streaming test.
Logs the size of xpak_cache/ every 10 s; if it exceeds the limit it terminates sp26-cod.exe
(cache is disposable) so the drive cannot fill. Locations/process names: GUI Game tab (tools/work/gui_settings.json).

  python tools/diskguard.py [limit_gib=18]                   (legacy positional form)
  python tools/diskguard.py --limit-gib 100 [--action kill|warn] [--status-json PATH] [--interval 10] [--cache DIR]

--action warn only logs LIMIT HIT and keeps watching (the GUI shows it); kill (default) terminates the game and exits.
--status-json: atomic snapshot {pid, cache_gib, free_gib, limit_gib, hit, ts} for the GUI.
"""
import argparse, json, os, sys, time, subprocess, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ccslib import paths            # cache folder, game folder and process names come from the GUI settings (Game tab)
ROOT = paths.GAME_ROOT
LOG = os.path.join(paths.WORK, 'diskguard.log')

def size(c):
    t = 0
    for dp, _, fn in os.walk(c):
        for f in fn:
            try: t += os.path.getsize(os.path.join(dp, f))
            except OSError: pass
    return t

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('limit', nargs='?', type=float, help='legacy positional limit in GiB')
    ap.add_argument('--limit-gib', type=float); ap.add_argument('--action', choices=('kill', 'warn'), default='kill')
    ap.add_argument('--status-json'); ap.add_argument('--interval', type=float, default=10); ap.add_argument('--cache', default=paths.XPAK_CACHE)
    ap.add_argument('--log', default=LOG)
    a = ap.parse_args(argv)
    limit = (a.limit_gib if a.limit_gib is not None else a.limit if a.limit is not None else 18) * 2**30
    os.makedirs(os.path.dirname(a.log), exist_ok=True)
    def log(line):
        line = f"{time.strftime('%H:%M:%S')} {line}"; print(line, flush=True)
        with open(a.log, 'a', encoding='utf-8') as f: f.write(line + '\n')
    log(f"READY diskguard pid={os.getpid()} limit={limit/2**30:.1f} GiB action={a.action} cache={a.cache}")
    last = -1; hit = False
    while True:
        s = size(a.cache); free = shutil.disk_usage(a.cache if os.path.isdir(a.cache) else ROOT).free
        if s != last:
            log(f"xpak_cache={s/2**30:.3f} GiB free={free/2**30:.1f} GiB"); last = s
        if s > limit and not hit:
            hit = True
            if a.action == 'kill':
                for exe in paths.KILL_EXES: subprocess.run(['taskkill', '/F', '/IM', exe], capture_output=True)
                log(f"LIMIT HIT (cache {s/2**30:.2f} GiB, free {free/2**30:.1f} GiB) -> {', '.join(paths.KILL_EXES)} terminated")
            else:
                log(f"LIMIT HIT (cache {s/2**30:.2f} GiB, free {free/2**30:.1f} GiB) -> warn only")
        elif s <= limit: hit = False
        if a.status_json:
            try:
                tmp = a.status_json + '.tmp'
                with open(tmp, 'w', encoding='utf-8') as f: json.dump(dict(pid=os.getpid(), cache_gib=s / 2**30, free_gib=free / 2**30, limit_gib=limit / 2**30, hit=hit, action=a.action, ts=time.time()), f)
                os.replace(tmp, a.status_json)
            except Exception as e: log(f"status-json write failed: {e}")
        if hit and a.action == 'kill': break
        time.sleep(a.interval)

if __name__ == '__main__':
    main()
