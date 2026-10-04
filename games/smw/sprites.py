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
      '8': "111 1.1 111 1.1 111", 'O': "111 1.1 1.1 1.1 111", 'N': "1.1 111 111 111 1.1", 'F': "111 1.. 11. 1.. 1..", 'U': "1.1 1.1 1.1 1.1 111", 'P': "111 1.1 111 1.. 1..", ' ': "... ... ... ... ..."}


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


# ---- big sprite letters (MARIO START !, GAME OVER, TIME UP !): our own 8x16 block face ---------------
# The game builds each letter from a top and a bottom tile of sheet 0F (tiles 00-17), reusing tiles
# flipped: O bottom = O top upside down, T bottom = I, S = one tile turned, M = 11 px wide and shared
# with the E after it. P and R have no left outline (the letter before supplies it).
def _rects(w, *rs):
    m = np.zeros((16, w), bool)
    for x0, x1, y0, y1 in rs:
        m[y0:y1 + 1, x0:x1 + 1] = True
    return m


def _outlined_letter(m, fill=5, line=2):
    p = np.pad(m, 1)
    near = np.zeros_like(m)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            near |= p[dy:dy + m.shape[0], dx:dx + m.shape[1]]
    out = np.zeros(m.shape, np.uint8)
    out[near] = line
    out[m] = fill
    return out


def big_letters():
    """-> {sheet tile index: (8, 8) index tile}"""
    st = (1, 2), (5, 6)                                    # the two stems of a standard letter
    L = {
        'I': _rects(8, (3, 4, 1, 14)),
        '!': _rects(8, (3, 4, 1, 9), (3, 4, 12, 14)),
        'T': _rects(8, (1, 6, 1, 2), (3, 4, 3, 14)),
        'O': _rects(8, (1, 2, 2, 13), (5, 6, 2, 13), (2, 5, 1, 2), (2, 5, 13, 14)),
        'U': _rects(8, (1, 2, 1, 13), (5, 6, 1, 13), (2, 5, 13, 14)),
        'V': _rects(8, (1, 2, 1, 10), (5, 6, 1, 10), (2, 3, 11, 12), (4, 5, 11, 12), (3, 4, 13, 14)),
        'A': _rects(8, (1, 2, 2, 14), (5, 6, 2, 14), (2, 5, 1, 2), (1, 6, 8, 9)),
        'G': _rects(8, (1, 2, 2, 13), (2, 6, 1, 2), (2, 5, 13, 14), (5, 6, 8, 13), (4, 6, 8, 9)),
        'E': _rects(8, (1, 2, 1, 14), (1, 6, 1, 2), (1, 6, 7, 8), (1, 6, 13, 14)),
        'L': _rects(8, (1, 2, 1, 14), (1, 6, 13, 14)),
        'S': _rects(8, (2, 6, 1, 2), (1, 2, 2, 7), (2, 5, 7, 8), (5, 6, 8, 13), (1, 5, 13, 14)),
        'P': _rects(8, (0, 1, 1, 14), (0, 5, 1, 2), (5, 6, 2, 7), (0, 5, 7, 8)),
        'R': _rects(8, (0, 1, 1, 14), (0, 5, 1, 2), (5, 6, 2, 7), (0, 5, 7, 8), (3, 4, 9, 10), (5, 6, 11, 14)),
    }
    g = {k: _outlined_letter(v) for k, v in L.items()}
    # M (11 wide) followed by a narrow E: one 24-wide strip
    me = _rects(24, (1, 2, 1, 14), (8, 9, 1, 14), (3, 3, 1, 4), (7, 7, 1, 4), (4, 4, 3, 6), (6, 6, 3, 6), (5, 5, 5, 8),
                (11, 12, 1, 14), (11, 16, 1, 2), (11, 16, 7, 8), (11, 16, 13, 14))
    me = _outlined_letter(me)
    stem = np.zeros((16, 8), np.uint8)
    stem[:, 5:8] = me[:, 0:3]
    top, bot = (lambda a: a[:8]), (lambda a: a[8:])
    return {
        0x00: top(g['I']), 0x01: top(g['P']), 0x02: top(g['G']), 0x03: top(g['O']), 0x04: top(me[:, 0:8]), 0x05: top(me[:, 8:16]),
        0x06: bot(g['!']), 0x07: bot(g['P']), 0x08: bot(g['G']), 0x09: bot(g['A']), 0x0A: bot(me[:, 0:8]), 0x0B: top(stem),
        0x0C: top(g['U']), 0x0D: top(g['E']), 0x0E: top(g['R']), 0x0F: top(g['T']), 0x10: top(g['L']),
        0x12: bot(g['V']), 0x13: bot(g['E']), 0x14: bot(g['R']), 0x15: top(g['S']), 0x16: bot(g['L']), 0x17: top(me[:, 16:24]),
    }


def sheet_0F(img):
    for t, tile in big_letters().items():
        y, x = t // 16 * 8, t % 16 * 8
        img[y:y + 8, x:x + 8] = tile


# ---- dinosaur head (sheet 0x33): ours, facing left: tall eye, nostril, white cheek, back spines ------
DINO_HEAD = [
    ".........222....",
    "........21112...",
    "........211212..",
    "........211212..",
    "...22222.21112..",
    ".22555552211122.",
    "2555555555511272",
    "2525555555511772",
    "2555555555554772",
    "2555555555554272",
    "2455555555544772",
    ".245555555544272",
    "..24444111144772",
    "...2221111114272",
    "......211111422.",
    ".......2222222..",
]
DINO_HEAD_UNITS = (16, 18, 22)


def place(img, u, rows):
    """Replace unit u with our drawing, its bottom-right corner on the corner of the kept silhouette's box."""
    v = unit_view(img, u)
    art = np.array([[int(c, 16) if c != '.' else 0 for c in r] for r in rows], np.uint8)
    ys, xs = np.nonzero(v)
    ay, ax = np.nonzero(art)
    dy, dx = (ys.max() - ay.max(), xs.max() - ax.max()) if len(ys) else (0, 0)
    out = np.zeros_like(art)
    h, w = art.shape
    src = art[max(0, -dy):h - max(0, dy), max(0, -dx):w - max(0, dx)]
    out[max(0, dy):max(0, dy) + src.shape[0], max(0, dx):max(0, dx) + src.shape[1]] = src
    v[:] = out


# ---- animated tiles (sheet 0x33): a frame is 4 consecutive 8x8 tiles (TL, TR, BL, BR) -----------------
def quad(img, tile_row, q, art):
    y, x = tile_row * 8, q * 32
    a = np.asarray(art, np.uint8)
    img[y:y + 8, x:x + 8], img[y:y + 8, x + 8:x + 16] = a[:8, :8], a[:8, 8:]
    img[y:y + 8, x + 16:x + 24], img[y:y + 8, x + 24:x + 32] = a[8:, :8], a[8:, 8:]


def block(body, top, low, line=2):
    """Square block: `top` on the upper/left rim, `low` on the lower/right rim, cut corners."""
    a = np.full((16, 16), body, np.uint8)
    a[1, :], a[:, 1] = top, top
    a[14, :], a[:, 14] = low, low
    a[0, :], a[15, :], a[:, 0], a[:, 15] = line, line, line, line
    for y, x in ((0, 0), (0, 15), (15, 0), (15, 15)):
        a[y, x] = 0
    return a


_QMARK = ["11111", "11.11", "11.11", "...11", "..11.", ".11..", ".11..", ".....", ".11..", ".11.."]


def question_block(k):
    a = block(6, 5, 3)
    for y, r in enumerate(_QMARK):
        for x, c in enumerate(r):
            if c == '1':
                a[3 + y, 6 + x] = 2
                a[2 + y, 5 + x] = 1        # white mark over its own shadow
    a[2, 2 + 3 * k] = 1                    # a glint that walks along the top
    return a


def eye_block():
    a = block(6, 7, 5)
    for x in (4, 10):
        a[4:7, x:x + 2] = 1
        a[5:7, x + 1] = 2
    return a


def coin(width):
    a = np.zeros((16, 16), np.uint8)
    for y in range(16):
        t = abs(y - 7.5) / 7.5
        half = max(1.0, width / 2 * (1 - t ** 3) ** 0.5) if width > 4 else width / 2
        x0, x1 = int(round(8 - half)), int(round(8 + half)) - 1
        a[y, x0:x1 + 1] = 7
        a[y, x0], a[y, x1] = 2, 2
        if x1 - x0 >= 4:
            a[y, x0 + 1], a[y, x1 - 1] = 1, 5
    a[0, a[0] > 0] = 2
    a[15, a[15] > 0] = 2
    if width >= 8:
        a[4:12, 7:9] = 6
    return a


def word_block(text, body, top, low):
    """Block with a short word in our 3x5 letters, doubled in height."""
    a = block(body, top, low)
    x = (16 - (4 * len(text) - 1)) // 2
    for ch in text:
        g = np.array([[c == '1' for c in r] for r in _D[ch].split()]).repeat(2, 0)
        a[4:14, x + 1:x + 4][g] = 2
        a[3:13, x:x + 3][g] = 1
        x += 4
    return a


def sheet_33(img):
    quad(img, 10, 0, word_block('ON', 4, 5, 3))
    quad(img, 11, 0, word_block('OFF', 6, 7, 5))
    for u in DINO_HEAD_UNITS:
        place(img, u, DINO_HEAD)
    for k, row in enumerate((12, 13, 14, 15)):
        quad(img, row, 0, question_block(k))
    quad(img, 12, 2, eye_block())
    for row, w in ((12, 12), (13, 8), (14, 4), (15, 8)):
        quad(img, row, 3, coin(w))


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
    if i == 0x0F:
        sheet_0F(img)
    if i == 0x33:
        sheet_33(img)
    paint_units(i, img)
    return img
