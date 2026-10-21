"""Connection details shown by the window; no network or file writes."""
import time


def stamp(value):
    if not value: return 'None yet'
    return time.strftime('%H:%M:%S', time.localtime(value))


def rows(snapshot):
    ps = snapshot.get('pstat') or snapshot.get('last_pstat') or {}; c = ps.get('connection') or {}; mp = snapshot.get('mprog') or {}
    live = bool((snapshot.get('pproc') or {}).get('alive'))
    downloading = bool((snapshot.get('mproc') or {}).get('alive'))
    offline=bool((ps.get('args') or {}).get('offline'))
    out = [dict(label='Streaming CDN', value=('Offline — local copy only' if offline else c.get('active_cdn')) if live else 'Streaming stopped', action='open_check', button='Check connection'),
           dict(label='Fallback address', value='Not used in offline mode' if offline else ('Yes — reconnect to find a nearer edge' if c.get('fallback') else 'No') if live else 'Not connected', action='open_check', button='Check my PC')]
    if downloading:
        out.append(dict(label='Download CDN', value=mp.get('edge') or 'Resolving address', action='pack_pause', button='Pause downloads'))
        out.append(dict(label='Download fallback', value='Yes' if mp.get('fallback') else 'No', action='open_check', button='Check connection'))
    successes = [x for x in (c.get('last_success'), dict(ts=mp.get('last_success'), source='offline download') if mp.get('last_success') else None) if x]
    last = max(successes, key=lambda x:x.get('ts') or 0) if successes else {}
    out.append(dict(label='Last successful delivery', value=stamp(last.get('ts')) + (' · ' + {'upstream':'internet','mirror':'local copy'}.get(last.get('source'),last.get('source','')) if last else ''), action='activity', button='View logs'))
    failures = [x for x in (c.get('last_failure'), mp.get('last_failure')) if x]
    last = max(failures, key=lambda x:x.get('ts') or 0) if failures else {}
    out.append(dict(label='Last failure', value=(stamp(last.get('ts')) + ' · ' + last.get('reason','Unknown')) if last else 'None recorded', action='open_check', button='Diagnose'))
    paused = ps.get('paused') or (snapshot.get('gstat') or {}).get('hit')
    out.append(dict(label='Disk protection', value='Transfers paused — free cache space' if paused else 'No pause requested', action='open_check', button='Check disk space'))
    return out
