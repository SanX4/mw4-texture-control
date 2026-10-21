#!/usr/bin/env python3
"""make_icon.py - draws packaging/app.ico (standard library only): a dark rounded square with a 3x3 grid of texture tiles that get brighter toward the corner, the
last one green (the piece that has just streamed in). Run it only when the design changes; the .ico is committed.

  python packaging/make_icon.py
"""
import os, struct, zlib

SIZES = (16, 24, 32, 48, 64, 128, 256)
BG, EDGE = (22, 24, 29), (46, 51, 62)
BLUES = [(30, 52, 92), (36, 64, 112), (44, 78, 136), (52, 92, 160), (60, 106, 184), (68, 120, 208), (76, 134, 232), (76, 141, 255)]
GREEN = (62, 207, 110)


def inside_round(x, y, r):                       # unit square [0,1]^2 with corner radius r
    if x < 0 or y < 0 or x > 1 or y > 1: return False
    cx = min(max(x, r), 1 - r); cy = min(max(y, r), 1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def polygon(x,y,points):
    inside=False
    for (ax,ay),(bx,by) in zip(points,points[1:]+points[:1]):
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax: inside=not inside
    return inside

def sample(x, y):
    if not inside_round(x,y,.22): return (0,0,0,0)
    if not inside_round((x-.018)/.964,(y-.018)/.964,.205): return (94,108,107,255)
    color=(int(31-10*y),int(41-11*y),int(40-9*y))
    # Three isometric texture planes; architectural geometry at every size.
    for offset,tone in ((.14,(62,81,76)),(.07,(78,100,90)),(0,(111,139,113))):
        if polygon(x,y,[(.16,.30+offset),(.50,.12+offset),(.84,.30+offset),(.50,.49+offset)]):
            color=tone
    # Original IV monogram in the game's tactical green visual vocabulary.
    if .245<=x<=.335 and .42<=y<=.80: color=(221,239,204)
    if polygon(x,y,[(.40,.42),(.50,.42),(.60,.69),(.70,.42),(.80,.42),(.65,.80),(.55,.80)]): color=(185,224,123)
    return color+(255,)

def render(size, ss=4):
    rows = []
    for py in range(size):
        row = bytearray()
        for px in range(size):
            r = g = b = a = 0
            for sy in range(ss):
                for sx in range(ss):
                    cr, cg, cb, ca = sample((px + (sx + 0.5) / ss) / size, (py + (sy + 0.5) / ss) / size)
                    r += cr * ca; g += cg * ca; b += cb * ca; a += ca
            n = ss * ss
            if a == 0: row += bytes((0, 0, 0, 0))
            else: row += bytes((round(r / a), round(g / a), round(b / a), round(a / n)))
        rows.append(bytes(row))
    return rows


def png_rgba(size, rows):
    raw = b''.join(b'\x00' + r for r in rows)
    def chunk(tag, data): return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')


def ico(images):
    head = struct.pack('<HHH', 0, 1, len(images)); offset = 6 + 16 * len(images); entries = b''; blobs = b''
    for size, data in images:
        entries += struct.pack('<BBBBHHII', 0 if size >= 256 else size, 0 if size >= 256 else size, 0, 0, 1, 32, len(data), offset + len(blobs)); blobs += data
    return head + entries + blobs


def main():
    images = [(s, png_rgba(s, render(s))) for s in SIZES]
    base = os.path.dirname(os.path.abspath(__file__)); open(os.path.join(base,'brand.png'),'wb').write(png_rgba(48,render(48))); open(os.path.join(base,'icon-preview.png'),'wb').write(images[-1][1]); out = os.path.join(base, 'app.ico'); open(out, 'wb').write(ico(images)); print(f'{out}: {os.path.getsize(out)} bytes')


if __name__ == '__main__':
    main()
