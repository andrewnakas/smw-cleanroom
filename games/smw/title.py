"""CLEAN ROOM. Our own title logo.

The title screen draws its logo on layer 3 from a "stripe image" (rows of tile number + attribute).
The retail arrangement reuses tiles between letters, so instead of drawing into it we lay the logo
area out ourselves: SUPER / MARIO WORLD in our block face (games/smw/sprites.big letters, doubled),
cut into 8x8 tiles, identical tiles stored once in the tile slots the logo owned (sheet 0x29), and the
stripe rows rewritten to point at them with a palette per letter.
"""
import numpy as np
from games.smw import sprites

STRIPE = 1                                   # index in kLoadStripeImagePtrs
TILEMAP = 0x5000
BLANK = 0x0FC
# tile slots (layer-3 tile numbers) used only by the logo; 0x80.. = sheet 0x29
POOL = [n for n in list(range(0x89, 0x8E)) + [0x90] + list(range(0x98, 0xB7)) + list(range(0xC6, 0xD4)) +
        list(range(0xD7, 0xF9)) + [0xFA, 0xFB] if n not in (0xE3, 0xC7, 0xCD, 0xF3, 0xD7, 0xDD, 0xD3, 0xF6)]      # F6 = copyright sign
# (palette, face index): layer-3 palettes 2/6/7 are black + two colours each
RED, YELLOW, GREEN, CYAN = (7, 2), (6, 3), (2, 2), (2, 3)
WORDS = [  # text, first row, first column, colours per letter
    ('SUPER', 5, 10, [RED, YELLOW, GREEN, CYAN, RED]),
    ('MARIO', 9, 5, [GREEN, RED, YELLOW, CYAN, RED]),
    ('WORLD', 9, 16, [YELLOW, GREEN, CYAN, RED, YELLOW]),
]
ROWS = {0x50AA: 10, 0x50CA: 11, 0x50EA: 11, 0x510A: 10, 0x5123: 24, 0x5143: 25, 0x5163: 25, 0x5183: 25, 0x51A3: 24}


def letters():
    R = sprites._rects
    L = {
        'S': R(8, (2, 6, 1, 2), (1, 2, 2, 7), (2, 5, 7, 8), (5, 6, 8, 13), (1, 5, 13, 14)),
        'U': R(8, (1, 2, 1, 13), (5, 6, 1, 13), (2, 5, 13, 14)),
        'P': R(8, (1, 2, 1, 14), (1, 5, 1, 2), (5, 6, 2, 7), (1, 5, 7, 8)),
        'E': R(8, (1, 2, 1, 14), (1, 6, 1, 2), (1, 5, 7, 8), (1, 6, 13, 14)),
        'R': R(8, (1, 2, 1, 14), (1, 5, 1, 2), (5, 6, 2, 7), (1, 5, 7, 8), (3, 4, 9, 10), (5, 6, 11, 14)),
        'M': R(8, (1, 2, 1, 14), (5, 6, 1, 14), (1, 6, 1, 2), (3, 4, 3, 7)),
        'A': R(8, (1, 2, 2, 14), (5, 6, 2, 14), (2, 5, 1, 2), (1, 6, 8, 9)),
        'I': R(8, (3, 4, 1, 14), (2, 5, 1, 2), (2, 5, 13, 14)),
        'O': R(8, (1, 2, 2, 13), (5, 6, 2, 13), (2, 5, 1, 2), (2, 5, 13, 14)),
        'W': R(8, (1, 2, 1, 14), (5, 6, 1, 14), (1, 6, 13, 14), (3, 4, 5, 12)),
        'L': R(8, (1, 2, 1, 14), (1, 6, 13, 14)),
        'D': R(8, (1, 2, 1, 14), (1, 5, 1, 2), (1, 5, 13, 14), (5, 6, 2, 13)),
    }
    return L


def build():
    """-> ({tile slot: (8, 8) index tile}, {(row, col): (slot, palette)})"""
    L = letters()
    slots, cells, seen = {}, {}, {}
    pool = list(POOL)
    for text, row, col, cols in WORDS:
        for k, ch in enumerate(text):
            pal, face = cols[k]
            big = sprites._outlined_letter(L[ch], face, 1).repeat(2, 0).repeat(2, 1)      # 32 x 16
            for ty in range(4):
                for tx in range(2):
                    t = big[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8]
                    key = t.tobytes()
                    if key not in seen:
                        seen[key] = pool.pop(0)
                        slots[seen[key]] = t
                    cells[(row + ty, col + 2 * k + tx)] = (seen[key], pal)
    return slots, cells


def patch_stripe(d):
    """Rewrite the logo rows of the title stripe image (plain rows: tile low byte, attribute)."""
    slots, cells = build()
    d = bytearray(d)
    p, done = 0, 0
    while d[p] != 0xFF:
        addr, f = d[p] << 8 | d[p + 1], d[p + 2]
        n = ((f & 0x3F) << 8 | d[p + 3]) + 1
        if addr in ROWS:
            assert not f & 0xC0 and n == ROWS[addr] * 2, 'title stripe layout changed'
            row, col = (addr - TILEMAP) // 32, (addr - TILEMAP) % 32
            for k in range(n // 2):
                keep = d[p + 5 + 2 * k] & 0x20                       # priority bit as it was
                slot, pal = cells.get((row, col + k), (BLANK, 2))
                d[p + 4 + 2 * k] = slot & 0xFF
                d[p + 5 + 2 * k] = keep | pal << 2 | slot >> 8
                done += (row, col + k) in cells
        p += 4 + (2 if f & 0x40 else n)
    assert done == len(cells), 'logo cells outside the stripe rows'
    return bytes(d)


def paint_sheet_29(img):
    slots, _ = build()
    for n in POOL:                                   # every slot the logo owned: ours or empty
        t = slots.get(n, np.zeros((8, 8), np.uint8))
        y, x = (n - 0x80) // 16 * 8, (n - 0x80) % 16 * 8
        img[y:y + 8, x:x + 8] = t
    return len(slots)
