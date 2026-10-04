"""CLEAN ROOM. Our own drawings laid over the automatic sheets: fonts and text
tiles re-typeset with cleanroom.gfx.pixfont, then sprite briefs (games/smw/briefs)."""
import numpy as np
from cleanroom.gfx import pixfont

# ---- helpers ---------------------------------------------------------------

def _tile(img, t):
    y, x = t // 16 * 8, t % 16 * 8
    return img[y:y + 8, x:x + 8]


def _outlined(mask, body, edge, bg=0):
    """body pixels where mask, `edge` on their 8-neighbours, bg elsewhere."""
    p = np.pad(mask, 1)
    near = np.zeros_like(mask)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            near |= p[dy:dy + mask.shape[0], dx:dx + mask.shape[1]]
    out = np.full(mask.shape, bg, np.uint8)
    out[near] = edge
    out[mask] = body
    return out


def hud_char(img, t, c, body=3, edge=1):
    """Outlined glyph on transparent (status bar style)."""
    _tile(img, t)[:] = _outlined(pixfont.cell(c, 8, 8, True, 1, 0), body, edge)


def box_char(img, t, c, body=3, bg=1):
    """Glyph on a filled cell (message box style)."""
    _tile(img, t)[:] = np.where(pixfont.cell(c, 8, 8, True, 1, 0), body, bg)


def menu_char(img, t, c, body=2, bg=3):
    """Dark glyph on a rounded light plate (file select / border text)."""
    m = pixfont.cell(c, 8, 8, True, 1, 0)
    out = np.where(m, body, bg).astype(np.uint8)
    out[7, :] = bg
    for y, x in ((0, 0), (0, 7), (7, 0), (7, 7)):
        out[y, x] = 0
    _tile(img, t)[:] = out


def strip(img, t, ntiles, text, body, edge=None, bg=0, bold=False, dx=0):
    """A word spread over `ntiles` tiles in a row."""
    m = np.zeros((8, ntiles * 8), bool)
    ln = pixfont.line(text, bold)
    x = max(0, (m.shape[1] - ln.shape[1]) // 2) if dx is None else dx
    w = min(ln.shape[1], m.shape[1] - x)
    m[0:7, x:x + w] = ln[:, :w]
    out = _outlined(m, body, edge, bg) if edge is not None else np.where(m, body, bg).astype(np.uint8)
    y, x0 = t // 16 * 8, t % 16 * 8
    img[y:y + 8, x0:x0 + ntiles * 8] = out


def tall_char(img, t, c, body=3, edge=1):
    """8x16 outlined glyph (credits font): tile t and the tile below it."""
    g = pixfont.cell(c, 8, 7, True, 1, 0).repeat(2, 0)
    m = np.zeros((16, 8), bool)
    m[1:15] = g
    y, x = t // 16 * 8, t % 16 * 8
    img[y:y + 16, x:x + 8] = _outlined(m, body, edge)


# ---- sheets ----------------------------------------------------------------

def sheet_28(img):
    for i, c in enumerate('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
        hud_char(img, i, c)
    hud_char(img, 0x24, '.')
    hud_char(img, 0x25, ',')
    hud_char(img, 0x26, 'x_')
    hud_char(img, 0x27, '-')
    hud_char(img, 0x28, '!')
    strip(img, 0x30, 5, 'MARIO', 2, 1, bold=True, dx=1)
    hud_char(img, 0x36, '1', 2)
    hud_char(img, 0x37, '9', 2)
    strip(img, 0x3D, 3, 'TIME', 3, 1, bold=False, dx=0)
    strip(img, 0x40, 5, 'LUIGI', 3, 1, bold=True, dx=1)
    menu_char(img, 0x4E, '3')
    for i, c in enumerate('4567'):
        menu_char(img, 0x50 + i, c)
    hud_char(img, 0x54, '0', 2)
    hud_char(img, 0x77, '=')
    hud_char(img, 0x78, ':')
    for i, c in enumerate('NOUD'):
        menu_char(img, 0x79 + i, c)


def sheet_29(img):
    for i, c in enumerate('VWIOH'):
        menu_char(img, i, c)


def sheet_2A(img):
    for i, c in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ!.-,?'):
        box_char(img, i, c)
    hud_char(img, 0x20, ',', 2)
    for i, c in enumerate('Z0123456789BC'):
        menu_char(img, 0x21 + i, c)
    hud_char(img, 0x2E, '>', 2)
    menu_char(img, 0x2F, 'T')
    menu_char(img, 0x30, 'N')
    menu_char(img, 0x31, 'S')
    y, x = 0x32 // 16 * 8, 0x32 % 16 * 8
    row = np.ones((8, 88), bool) & False
    for i, c in enumerate('ILLUSIYELLOW'):
        g = pixfont.cell(c, 8, 8, True, 1, 0)
        w = min(8, 88 - (4 + i * 8))
        if w > 0:
            row[:, 4 + i * 8:4 + i * 8 + w] = g[:, :w]
    img[y:y + 8, x:x + 88] = np.where(row, 3, 1)
    box_char(img, 0x3D, '?')
    menu_char(img, 0x3E, 'O')
    box_char(img, 0x3F, '/')
    for i, c in enumerate("abcdefghijklmnopqrstuvwxyz#()'"):
        box_char(img, 0x40 + i, c)
    for i, c in enumerate('12345670'):
        box_char(img, 0x64 + i, c)
    for i, c in enumerate('12P'):
        menu_char(img, 0x6D + i, c)
    for i, c in enumerate('LAYERGM'):
        menu_char(img, 0x70 + i, c)
    box_char(img, 0x7A, 'R')
    strip(img, 0x7B, 2, 'TM', 2, 1, bold=False, dx=1)


def sheet_2F(img):
    for i, c in enumerate('ABCDEFGHIJKLMNOP'):
        tall_char(img, i, c)
    for i, c in enumerate('QRSTUVWXYZ-.'):
        tall_char(img, 0x20 + i, c)


SHEETS = {0x28: sheet_28, 0x29: sheet_29, 0x2A: sheet_2A, 0x2F: sheet_2F}


def apply(i, img, spec):
    f = SHEETS.get(i)
    if f:
        f(img)
    try:
        from games.smw import sprites
        img = sprites.apply(i, img, spec)
    except ImportError:
        pass
    return img
