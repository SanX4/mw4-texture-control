#!/usr/bin/env python3
"""diskguard - protect free disk space during a streaming test.
Monitors cache size and free space. The default pauses new transfers without closing the game.
Forced shutdown is available only through the explicit kill action. Locations/process names: GUI Game tab (tools/work/gui_settings.json).

  python tools/diskguard.py [limit_gib=18]                   (legacy positional form)
  python tools/diskguard.py --limit-gib 100 [--action pause|warn|kill] [--status-json PATH] [--interval 10] [--cache DIR]

--action pause (default) signals the proxy and pauses the offline download. warn only logs; kill explicitly terminates the configured game process.
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
    ap.add_argument('--limit-gib', type=float); ap.add_argument('--action', choices=('pause', 'kill', 'warn'), default='pause')
    ap.add_argument('--min-free-gib', type=float, default=2)
    ap.add_argument('--status-json'); ap.add_argument('--interval', type=float, default=10); ap.add_argument('--cache', default=paths.XPAK_CACHE)
    ap.add_argument('--log', default=LOG)
    ap.add_argument('--pause-file', default=os.path.join(paths.RUN, 'transfers-paused.json'))
    ap.add_argument('--mirror-stop-file', default=os.path.join(paths.MIRROR, 'STOP'))
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
        exceeded=s > limit or free < a.min_free_gib*2**30
        if exceeded and not hit:
            hit = True
            if a.action == 'kill':
                for exe in paths.KILL_EXES: subprocess.run(['taskkill', '/F', '/IM', exe], capture_output=True)
                log(f"LIMIT HIT (cache {s/2**30:.2f} GiB, free {free/2**30:.1f} GiB) -> {', '.join(paths.KILL_EXES)} terminated")
            else:
                log(f"LIMIT HIT (cache {s/2**30:.2f} GiB, free {free/2**30:.1f} GiB) -> " + ("new transfers paused" if a.action == "pause" else "warn only"))
        elif not exceeded: hit = False
        if a.action == 'pause':
            if hit:
                os.makedirs(os.path.dirname(a.pause_file), exist_ok=True)
                tmp = a.pause_file + '.tmp'
                with open(tmp, 'w', encoding='utf-8') as f:
                    json.dump(dict(pid=os.getpid(), reason='Disk space is low' if free < a.min_free_gib*2**30 else 'Cache limit reached', cache_gib=s/2**30, limit_gib=limit/2**30, ts=time.time()), f)
                os.replace(tmp, a.pause_file)
                if os.path.isdir(os.path.dirname(a.mirror_stop_file)):
                    with open(a.mirror_stop_file, 'w') as f: f.write('Disk protection: pause downloads')
            else:
                try: os.remove(a.pause_file)
                except FileNotFoundError: pass
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
