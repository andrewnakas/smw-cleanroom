"""CLEAN ROOM. Our own sprite drawing on top of the automatic sheets.

Player sheet (0x32, 4bpp): the automatic pass gives cap / skin / overalls areas inside the kept
silhouette; here we add a face of our own design (eye, moustache, sideburn) placed from the
skin area of the automatic picture. Nothing in this file reads retail pixels.
"""
import os
import numpy as np
from scipy import ndimage
from games.smw import assetfile as A

SPEC = os.path.join(os.path.dirname(__file__), 'spec')
WHITE, BLACK, SKIN, SKIN_SH = 1, 2, 6, 0xE


def unit_view(img, u):
    y, x = u // 8 * 16, u % 8 * 16
    return img[y:y + 16, x:x + 16]


def _unit_of(r):
    return (r & 7) + 8 * (r >> 4) + (128 if r & 8 else 0)


def player_units():
    """(small face units, big head units) from the kept pose tables."""
    it = dict(A.read(os.path.join(SPEC, 'kept.dat')))
    head, body = it['kPlayerGFXRt_HeadTilePointerIndex'], it['kPlayerGFXRt_BodyTilePointerIndex']
    small = sorted({_unit_of(r) for r in body[:0x46]})
    big = sorted({_unit_of(r) for r in head[0x46:]})
    return small, big


def face_area(v, rows):
    """Largest skin-coloured blob of a unit within `rows` -> (x0, y0, x1, y1) or None."""
    skin = (v == SKIN) | (v == SKIN_SH)
    skin[:rows[0]] = False
    skin[rows[1]:] = False
    lab, n = ndimage.label(skin)
    if not n:
        return None
    sizes = ndimage.sum(skin, lab, range(1, n + 1))
    k = int(np.argmax(sizes)) + 1
    if sizes[k - 1] < 12:
        return None
    ys, xs = np.nonzero(lab == k)
    return xs.min(), ys.min(), xs.max(), ys.max()


def put(v, x, y, c):
    if 0 <= x < 16 and 0 <= y < 16 and v[y, x] != 0:
        v[y, x] = c


def small_face(v):
    """Left-facing small face: 2-pixel eye with a white glint, one-row moustache with a curl."""
    a = face_area(v, (0, 9))
    if a is None:
        return False
    x0, y0, x1, y1 = a
    w, h = x1 - x0 + 1, y1 - y0 + 1
    if w < 5 or h < 3:
        return False
    v[y0:y1 + 1, x0:x1 + 1][(v[y0:y1 + 1, x0:x1 + 1] == SKIN_SH)] = SKIN
    ex = x0 + max(2, int(w * 0.38))
    put(v, ex, y0, BLACK)
    put(v, ex, y0 + 1, BLACK)
    put(v, ex + 1, y0, WHITE)
    my = min(y1, y0 + 3)
    for x in range(x0 + 1, min(x1, ex + 2) + 1):
        put(v, x, my, BLACK)
    put(v, min(x1, ex + 3), my - 1, BLACK)          # curl
    for y in range(y0, min(y1, y0 + 2) + 1):          # sideburn at the back of the face
        put(v, x1, y, BLACK)
    for x in range(x0, x0 + 2):                       # nose shade
        put(v, x, min(y1, y0 + 2), SKIN_SH)
    return True


def big_face(v):
    """Left-facing big head: 2x3 eye, two-row moustache, ear and sideburn."""
    a = face_area(v, (0, 16))
    if a is None:
        return False
    x0, y0, x1, y1 = a
    w, h = x1 - x0 + 1, y1 - y0 + 1
    if w < 6 or h < 4:
        return False
    v[y0:y1 + 1, x0:x1 + 1][(v[y0:y1 + 1, x0:x1 + 1] == SKIN_SH)] = SKIN
    ex = x0 + max(3, int(w * 0.36))
    for dy in range(3):
        put(v, ex, y0 + dy, BLACK)
        put(v, ex + 1, y0 + dy, WHITE if dy < 2 else BLACK)
    my = min(y1 - 1, y0 + 4)
    for x in range(x0 + 2, min(x1, ex + 3) + 1):
        put(v, x, my, BLACK)
    for x in range(x0 + 3, min(x1, ex + 2) + 1):
        put(v, x, my + 1, BLACK)
    put(v, min(x1, ex + 4), my - 1, BLACK)
    bx = min(x1, ex + 6)
    for y in range(y0, min(y1, y0 + 3) + 1):          # sideburn
        put(v, bx, y, BLACK)
    put(v, bx - 2, y0 + 1, SKIN_SH)                   # ear
    put(v, bx - 2, y0 + 2, SKIN_SH)
    for x in range(x0, x0 + 2):
        put(v, x, min(y1, y0 + 3), SKIN_SH)
    return True


# ---- hand-drawn player parts (ours), stamped where a unit's kept silhouette matches the part's shape ----
# 8 dark outline, 9 red, D dark red, 6 skin, E skin shade, 3 brown, 2 black, 1 white; '.' = leave as is
SMALL_CAP = (40, {12: "....88888.......",
                  13: "...89999D88.....",
                  14: "...8991999D8....",
                  15: "..89999999DD8..."})
SMALL_FACE = (57, {0: ".8999999999DD8..",
                   1: "....E216662228..",
                   2: "..3662166662268.",
                   3: ".36666666662638.",
                   4: ".3E2222266622E8.",
                   5: "..E622226666E8..",
                   6: "...3EE66666E3..."})
BIG_HEAD = (56, {3: "....88888.......",
                 4: "...89999988.....",
                 5: "...899199D98....",
                 6: "..89999999DD8...",
                 7: ".8999999999DD8..",
                 8: ".88899999999DD8.",
                 9: "..88886222222D8.",
                 10: "....662166226E8.",
                 11: "..3666216662E63E",
                 12: "..3666666662663E",
                 13: "..3E22222666EEE.",
                 14: ".3EE222226666E3.",
                 15: "..33EEEE666EE3.."})


def stamp(img, part, units, need=0.85):
    """Paint `part` into every unit whose silhouette (over the part's rows, small shifts allowed) matches."""
    ref, rows = part
    art = np.zeros((16, 16), np.uint8)
    for y, r in rows.items():
        art[y] = [int(c, 16) if c != '.' else 0 for c in r]
    rmask = np.zeros((16, 16), bool)
    rmask[list(rows)] = True
    rs = (unit_view(img, ref) > 0) & rmask
    done = []
    for u in units:
        v = unit_view(img, u)
        sil = v > 0
        best = (0, 0, 0)
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                sh = np.roll(np.roll(rs, dy, 0), dx, 1)
                win = np.roll(np.roll(rmask, dy, 0), dx, 1)
                if dy > 0 and sh[:dy].any() or dy < 0 and sh[dy:].any() or dx > 0 and sh[:, :dx].any() or dx < 0 and sh[:, dx:].any():
                    continue
                inter, union = (sh & sil & win).sum(), ((sh | sil) & win).sum()
                score = inter / max(union, 1) - 0.01 * (abs(dx) + abs(dy))
                if score > best[0]:
                    best = (score, dy, dx)
        if best[0] >= need:
            a = np.roll(np.roll(art, best[1], 0), best[2], 1)
            m = (a > 0) & sil
            v[m] = a[m]
            done.append(u)
    return done


def sheet_32(img):
    small, big = player_units()
    it = dict(A.read(os.path.join(SPEC, 'kept.dat')))
    small_heads = sorted({_unit_of(r) for r in it['kPlayerGFXRt_HeadTilePointerIndex'][:0x46]})
    auto = img.copy()
    done_small = stamp(img, SMALL_FACE, small)
    done_big = stamp(img, BIG_HEAD, big)
    stamp(img, SMALL_CAP, small_heads)
    for u in small:
        if u not in done_small:
            small_face(unit_view(img, u))
    for u in big:
        if u not in done_big:
            big_face(unit_view(img, u))
    return len(done_small), len(small), len(done_big), len(big)


# ---- whole 16x16 units drawn by us --------------------------------------------------------------
# sprite sheets: 1 white, 2 black, 3/4/5 dark/mid/light of the sprite's palette row, 6/7 brown/orange
UNITS = {
    (0x00, 10): [  # mushroom: three white spots, narrow stem with two eyes
        ".....222222.....",
        "...2244444422...",
        "..241144441142..",
        ".24114444441142.",
        ".24444411444442.",
        "2444441111444442",
        "2444441111444442",
        "2344444114444432",
        "2334444444444332",
        ".23333333333332.",
        "..222222222222..",
        "...2111111112...",
        "...2112112112...",
        "...2112112112...",
        "...2111111112...",
        "....22222222....",
    ],
    (0x00, 11): [  # flower: ringed head with a white face, two leaves
        ".....222222.....",
        "...2266666622...",
        "..266777777662..",
        ".26771111117762.",
        ".26711211211762.",
        ".26711211211762.",
        ".26771111117762.",
        "..266777777662..",
        "...2266666622...",
        ".....222222.....",
        "......2542......",
        ".222..2542..222.",
        "25542.2542.24552",
        "2555422542245552",
        ".24444255244442.",
        "..222222222222..",
    ],
    (0x00, 20): [  # star with two eyes
        ".......22.......",
        "......2552......",
        "......2552......",
        ".....255552.....",
        ".....255552.....",
        "2222225555222222",
        "2555555555555552",
        ".25555255255552.",
        "..255525525552..",
        "...2555555552...",
        "...2555555552...",
        "..255555555552..",
        "..255552255552..",
        ".25552....25552.",
        ".2552......2552.",
        ".222........222.",
    ],
    (0x00, 17): [  # switch with a letter P
        "................",
        ".....222222.....",
        "...2255555522...",
        "..254444444432..",
        ".25441111444432.",
        ".25441444144432.",
        "2544414441444432",
        "2544411114444432",
        "2544414444444432",
        "2544414444444432",
        "2544444444444432",
        "2333333333333332",
        "2222222222222222",
        "2677777777777762",
        "2667777777777662",
        "2222222222222222",
    ],
}

_SHELL = [
    ".....222222.....",
    "...2245555422...",
    "..245555555542..",
    ".24555155555442.",
    ".24551555555442.",
    "2445555555554432",
    "2444555555544432",
    "2344444444444332",
    "2333444444443332",
    "2111111111111112",
    "2112222222222112",
    "2122222222222212",
    ".21222222222212.",
    ".21122222222112.",
    "..211111111112..",
    "...2222222222...",
]
_SHELL_B = _SHELL[:3] + [".24555555515442.", ".24555555551442."] + _SHELL[5:]
_SHELL_C = _SHELL[:3] + [".24555355355442.", ".24555355355442."] + _SHELL[5:]
_GOOM = [
    "................",
    ".....222222.....",
    "...2266666622...",
    "..266666666662..",
    ".26666666666662.",
    ".26112666621162.",
    "2661126666211662",
    "2661126666211662",
    "2666666666666662",
    "2666622222266662",
    ".26666666666662.",
    "..266666666662..",
    "...2222222222...",
]
UNITS.update({
    (0x01, 5): _SHELL, (0x01, 6): _SHELL_B, (0x01, 7): _SHELL_C,
    (0x01, 12): _GOOM + ["..27772..27772..", ".277772..277772.", ".222222..222222."],
    (0x01, 13): _GOOM + [".27772....27772.", "277772....277772", "222222....222222"],
    (0x01, 11): [  # bullet: dark body, top highlight, one eye, white tail band
        "................",
        "................",
        ".....2222222222.",
        "...2233333332112",
        "..23322222222112",
        ".233221112222112",
        ".232221121222112",
        "2322221121222112",
        "2322221111222112",
        ".232222222222112",
        ".233222222222112",
        "..23322222222112",
        "...2233333332112",
        ".....2222222222.",
        "................",
        "................",
    ],
})

# 3x5 digits and letters for the score pop-ups (ours)
_D = {'0': "111 1.1 1.1 1.1 111", '1': ".1. 11. .1. .1. 111", '2': "111 ..1 111 1.. 111", '4': "1.1 1.1 111 ..1 ..1",
      '8': "111 1.1 111 1.1 111", 'U': "1.1 1.1 1.1 1.1 111", 'P': "111 1.1 111 1.. 1..", ' ': "... ... ... ... ..."}


def tiny(text, body, shadow=2, w=16):
    """3x5 text with a one-pixel drop shadow -> (8, w) index image."""
    out = np.zeros((8, w), np.uint8)
    x = 0
    for ch in text:
        g = np.array([[c == '1' for c in r] for r in _D[ch].split()])
        out[2:7, x + 1:x + 4][g] = shadow
        x += 4
    x = 0
    for ch in text:
        g = np.array([[c == '1' for c in r] for r in _D[ch].split()])
        out[1:6, x:x + 3][g] = body
        x += 4
    return out


def sheet_00(img):
    # score pop-ups: left tile holds two digits, right tile the rest
    for tile, text in ((0x44, '100 '), (0x54, '2000'), (0x46, '4080')):
        y, x = tile // 16 * 8, tile % 16 * 8
        img[y:y + 8, x:x + 16] = tiny(text, 1)
    y, x = 0x56 // 16 * 8, 0x56 % 16 * 8
    img[y:y + 8, x:x + 16] = tiny('1UP', 5)


def paint_units(i, img):
    n = 0
    for (s, u), rows in UNITS.items():
        if s == i:
            assert len(rows) == 16 and all(len(r) == 16 for r in rows), (s, u)
            unit_view(img, u)[:] = [[int(c, 16) if c != '.' else 0 for c in r] for r in rows]
            n += 1
    return n


def apply(i, img, spec):
    if i == 0x32:
        print('player faces: small %d of %d hand-drawn, big %d of %d' % sheet_32(img))
    if i == 0x00:
        sheet_00(img)
    paint_units(i, img)
    return img
