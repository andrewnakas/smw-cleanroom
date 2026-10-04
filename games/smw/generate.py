"""CLEAN ROOM. Builds smw_assets.dat from games/smw/spec (kept facts) + our own
drawing and synthesis code. Never reads the ROM or the dirty tree."""
import sys, os, json, struct
import numpy as np
from scipy.ndimage import uniform_filter
from games.smw import assetfile as A, layout as L
from cleanroom.snes import lz2, tiles, brr
from cleanroom.audio import descriptor

SPEC = os.path.join(os.path.dirname(__file__), 'spec')


# ---------------------------------------------------------------- graphics
def auto_sheet(g):
    """Index image of a sheet from its sprite units: kept silhouette, 4x4 colour
    grid per 16x16 unit, edge colour on the silhouette border."""
    units = g['units']
    rows = len(units) // 8
    img = np.zeros((rows * 16, 128), np.uint8)
    edgecol = np.zeros_like(img)
    for k, u in enumerate(units):
        if not u:
            continue
        y, x = k // 8 * 16, k % 8 * 16
        sil = np.unpackbits(np.frombuffer(bytes.fromhex(u['sil']), np.uint8)).reshape(16, 16).astype(bool)
        grid = np.array([int(c, 16) for c in u['grid']], np.uint8).reshape(4, 4)
        grid[sil.reshape(4, 4, 4, 4).sum((1, 3)) < 4] = 0     # a cell showing under 4 pixels carries no colour
        nz = grid[grid > 0]
        fill = int(np.bincount(nz).argmax()) if len(nz) else (u['edge'] or 1)
        # each pixel takes the colour with the largest blurred vote of the cells around it:
        # rounded region borders instead of 4 px blocks
        best, big = np.zeros((16, 16)), np.full((16, 16), fill, np.uint8)
        for k in np.unique(nz):
            v = uniform_filter(np.kron((grid == k).astype(float), np.ones((4, 4))), 5, mode='nearest')
            big[v > best] = k
            best = np.maximum(best, v)
        img[y:y + 16, x:x + 16] = np.where(sil, big, 0)
        edgecol[y:y + 16, x:x + 16] = u['edge']
    sil = img > 0
    pad = np.pad(sil, 1, constant_values=True)
    edge = sil & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    img[edge & (edgecol > 0)] = edgecol[edge & (edgecol > 0)]
    return img


def build_gfx(gfx, drawn=None):
    out = {}
    for key, g in gfx.items():
        i = int(key, 16)
        img = auto_sheet(g)
        if drawn:
            img = drawn(i, img, g)
        nt = g['bytes'] // tiles.TILE_BYTES[g['bpp']]
        out[i] = tiles.encode(tiles.unsheet(img)[:nt], g['bpp'])
        assert len(out[i]) == g['bytes']
    return out


# ---------------------------------------------------------------- palettes
def build_palette(code):
    c = np.array([int(ch) for ch in code], np.int32).reshape(-1, 3)
    c = (c * 31 + 3) // 7
    return (c[:, 0] | c[:, 1] << 5 | c[:, 2] << 10).astype('<u2').tobytes()


# ---------------------------------------------------------------- samples
def _impose_env(x, env_db, hold_from=None):
    """Scale 64-sample windows of x to the kept level outline."""
    y = x.copy()
    for k, db in enumerate(env_db):
        a, b = k * 64, min(len(x), k * 64 + 64)
        if hold_from is not None and a >= hold_from:
            break
        seg = y[a:b]
        r = np.sqrt(np.mean(seg ** 2)) + 1e-9
        y[a:b] = seg * min(10 ** (db / 20.0) / r, 50.0)
    return y


def synth_sample(e, seed):
    n = e['blocks'] * 16
    rng = np.random.default_rng(seed)
    if e['loop']:
        ls = e['loop_block'] * 16
        ln = n - ls
        o = e['loop_outline']
        t = np.arange(ln) / ln
        per = np.zeros(ln)
        for k, db in enumerate(o['harm_db'], 1):
            if db > -60 and o['cycles'] * k < ln / 2:
                per += 10 ** (db / 20.0) * np.sin(2 * np.pi * o['cycles'] * k * t + rng.uniform(0, 2 * np.pi))
        x = per[(np.arange(n) - ls) % ln]
        if ls:
            att = descriptor.synthesize(e['desc'], n, L.RATE, seed)[:ls]
            w = np.linspace(1, 0, ls) ** 2          # attack: descriptor timbre fading into the loop wave
            x[:ls] = x[:ls] * (1 - w) + att * w
            x = _impose_env(x, e['env_db'], hold_from=ls)
    else:
        x = descriptor.synthesize(e['desc'], n, L.RATE, seed).astype(np.float64)
        x = _impose_env(x, e['env_db'])
        x[-32:] *= np.linspace(1, 0, 32)
    x = np.clip(x, -0.98, 0.98)
    pcm = np.round(x * 32767).astype(np.int16)
    return brr.encode(pcm, e.get('loop_block') if e['loop'] else None)


def build_samples(sp):
    blob = bytearray(sp['blob_bytes'])
    dirb = bytearray()
    for i, e in enumerate(sp['samples']):
        b = synth_sample(e, 1000 + i)
        blob[e['offset']:e['offset'] + len(b)] = b
    for k in sp['dir']:
        e = sp['samples'][k]
        s = L.SAMPLE_BASE + e['offset']
        dirb += struct.pack('<HH', s, s + e.get('loop_block', 0) * 9)
    assert len(dirb) == sp['dir_bytes']
    return (struct.pack('<HH', len(dirb), L.SAMPLE_DIR) + dirb +
            struct.pack('<HH', len(blob), L.SAMPLE_BASE) + bytes(blob) + bytes.fromhex(sp['tail']))


# ---------------------------------------------------------------- main
def main(out):
    try:
        from games.smw import drawn
        hook = drawn.apply
    except ImportError:
        hook = None
    kept = A.read(os.path.join(SPEC, 'kept.dat'))
    gfx = build_gfx(json.load(open(os.path.join(SPEC, 'gfx.json'))), hook)
    pal = json.load(open(os.path.join(SPEC, 'pal.json')))
    smp = build_samples(json.load(open(os.path.join(SPEC, 'samples.json'))))
    items = []
    for n, v in kept:
        if n == 'kGraphicsPtrs':
            v = A.pack_array([lz2.compress(gfx[i]) for i in range(0x32)])
        elif n == 'kGfx32':
            v = gfx[0x32]
        elif n == 'kGfx33':
            v = gfx[0x33]
        elif n == 'kSpcSamples':
            v = smp
        elif L.is_palette(n):
            v = build_palette(pal[n])
        items.append((n, v))
    A.write(out, items)
    print('wrote %s: %d entries, %d bytes (gfx %d sheets, samples %d bytes, kRom %d bytes)' % (
        out, len(items), os.path.getsize(out), len(gfx), len(smp), len(dict(items)['kRom'])))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'D:/n64work/smw/clean/smw_assets.dat')
