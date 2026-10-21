#!/usr/bin/env python3
"""cdnxpak — parse `*_cdn.xpak` (KAPI type 4) chunk lists.

Record (20 B, from 0x8000): [u64 id][u32 (size<<1)|flag][u32 0][u32 rawsize]
size = total CDN object bytes, flag = URL suffix (_0/_1), rawsize = decoded bytes.
"""
import struct, sys, glob, os
def parse(fn):
    d = open(fn, 'rb').read(); recs = []; p = 0x8000
    while p + 20 <= len(d):
        i, x, z, raw = struct.unpack_from('<QIII', d, p)
        if z != 0 or i == 0 or (x >> 1) == 0 or raw == 0: break
        recs.append(dict(id=i, size=x >> 1, flag=x & 1, raw=raw)); p += 20
    return recs
if __name__ == '__main__':
    for fn in sys.argv[1:]:
        r = parse(fn)
        print(os.path.basename(fn), len(r), "chunks", sum(x['size'] for x in r), "B compressed", sum(x['raw'] for x in r), "B raw")
