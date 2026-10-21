#!/usr/bin/env python3
"""xpakrec - parse chunk records of a KAPI .xpak (type 2 index or type 4 cdn index).

Record (20 B, table at the (offset,size) given by the section header at 0x7a0, usually 0x8000):
  [u64 id][u32 (wireSize<<1)|flag][u32 xsubOff>>7 (0 = not resident / CDN)][u32 rawSize]
"""
import struct, sys
def parse(fn):
    d = open(fn, 'rb').read(); recs = []; p = 0x8000
    while p + 20 <= len(d):
        i, x, o, raw = struct.unpack_from('<QIII', d, p)
        if i == 0 or i == 0xa7a7a7a7a7a7a7a7 or (x >> 1) == 0: break
        recs.append(dict(id=i, size=x >> 1, flag=x & 1, off=o << 7, raw=raw)); p += 20
    return recs
if __name__ == '__main__':
    for fn in sys.argv[1:]:
        r = parse(fn); res = sum(1 for x in r if x['off'])
        print(fn, len(r), 'records,', res, 'with xsub offset')
