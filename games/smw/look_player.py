"""Dev: player poses (head unit over body unit) in the player palette. usage: look_player assets.dat out.png"""
import sys, json, os
import numpy as np
from games.smw import assetfile as A
from games.smw.look_sheets import sheets
from games.smw.sprites import _unit_of
from cleanroom.snes import tiles
from cleanroom.gfx import png

path, out = sys.argv[1], sys.argv[2]
it = dict(A.read(path))
w = np.frombuffer(it['kPlayerPalettes'][:20], '<u2').astype(np.int32)
pal = np.zeros((16, 3), np.uint8)
pal[0] = (90, 150, 230); pal[1] = 255; pal[2] = 0; pal[3] = (120, 72, 24); pal[4] = (200, 200, 200); pal[5] = (230, 230, 230)
pal[6:16] = np.stack([w & 31, w >> 5 & 31, w >> 10 & 31], -1) * 255 // 31
im = tiles.sheet(tiles.decode(sheets(path)[0x32], 4))
H, B = it['kPlayerGFXRt_HeadTilePointerIndex'], it['kPlayerGFXRt_BodyTilePointerIndex']
unit = lambda u: im[u // 8 * 16:u // 8 * 16 + 16, u % 8 * 16:u % 8 * 16 + 16]
poses = list(range(0, 0x3D)) + list(range(0x46, 0x46 + 0x3D))
cols = 31
canvas = np.zeros((-(-len(poses) // cols) * 34, cols * 18), np.uint8)
for k, p in enumerate(poses):
    y, x = k // cols * 34, k % cols * 18
    canvas[y:y + 16, x:x + 16] = unit(_unit_of(H[p]))
    canvas[y + 16:y + 32, x:x + 16] = unit(_unit_of(B[p]))
rgb = pal[canvas].repeat(3, 0).repeat(3, 1)
png.write(out, np.dstack([rgb, np.full(rgb.shape[:2], 255, np.uint8)]))
print(out, rgb.shape)
