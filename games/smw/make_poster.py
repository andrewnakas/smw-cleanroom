"""poster.png (16:9) for the catalogue: a scene from the CLEAN build with the title typeset by us.

    python -m games.smw.make_poster <clean screenshot.png> poster.png
"""
import sys
import numpy as np
from PIL import Image
from cleanroom.gfx import pixfont

W, H = 1280, 720


def text(canvas, s, x, y, scale, col, shadow=(16, 18, 28)):
    m = pixfont.line(s, True, 1).repeat(scale, 0).repeat(scale, 1)
    h, w = m.shape
    if x is None:
        x = (W - w) // 2
    for dx, dy, c in ((scale, scale, shadow), (0, 0, col)):
        reg = canvas[y + dy:y + dy + h, x + dx:x + dx + w]
        reg[m[:reg.shape[0], :reg.shape[1]]] = c


def main(shot, out):
    im = Image.open(shot).convert('RGB')
    s = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * s + .5), int(im.height * s + .5)), Image.NEAREST)
    x0, y0 = (im.width - W) // 2, int((im.height - H) * 0.75)
    a = np.array(im)[y0:y0 + H, x0:x0 + W].copy()
    band = a[60:330].astype(float)
    a[60:330] = (band * 0.35 + np.array([20, 24, 40]) * 0.65).astype(np.uint8)
    text(a, 'SUPER', None, 92, 10, (240, 84, 60))
    text(a, 'MARIO WORLD', None, 178, 13, (250, 214, 70))
    text(a, 'clean room build', None, 286, 4, (232, 230, 225))
    Image.fromarray(a).save(out)
    print('poster ->', out, a.shape)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
