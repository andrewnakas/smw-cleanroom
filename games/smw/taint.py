"""Taint report for the SNES build (dev: reads the dirty file to compare).

    python -m games.smw.taint [dirty.dat] [clean.dat] [shipped files...]

Stored forms compared, retail vs clean, per regenerated entry:
  GFX      LC_LZ2 block, raw planar tiles, decoded index pixels (1 byte per pixel)
  palettes 15-bit colour words
  samples  BRR bytes, decoded 16-bit PCM
Rule (see STATUS.md Decisions):
  * byte runs: any run >= 32 bytes shared with a retail stream fails (16-byte windows;
    windows with period <= 4 or fewer than 6 distinct byte values are ignored). In GFX
    streams, bytes of a tile that is only the kept silhouette filled with one kept colour
    on its border pixels and one colour inside are "explained by kept facts" and break
    a run; an LZ2 byte is explained when every byte its command writes is explained.
    Planar streams fail at two whole adjacent tiles (32 B for 2bpp, 48 B for 3bpp).
    Windows made only of single-bit bytes (a diagonal line / a bit-mask table) are ignored;
  * pixels: a 16x16 sprite unit identical to the retail unit at the same place fails when it
    has >= 4 colours; identical 8x8 tiles with >= 3 colours (not explained) are counted as coincidences
    (small glyph-like tiles collide by chance) and fail above 2% of the informative tiles;
  * shipped files (smw.data, smw.wasm, smw.js) are scanned whole against every retail stream.
"""
import sys, os, struct
import numpy as np
from cleanroom import taint
from cleanroom.snes import lz2, tiles, brr
from games.smw import assetfile as A, layout as L

COINCIDENCE_LIMIT = 0.02


def forms(path):
    it = dict(A.read(path))
    comp = A.unpack_array(it['kGraphicsPtrs'])
    raw = [lz2.decompress(c) for c in comp] + [it['kGfx32'], it['kGfx33']]
    out = {}
    for i, c in enumerate(comp):
        out['gfx%02X.lz2' % i] = c
    px = {}
    for i, r in enumerate(raw):
        out['gfx%02X.planar' % i] = r
        px[i] = tiles.decode(r, L.BPP[i])
        out['gfx%02X.pixels' % i] = px[i].tobytes()
    for n, v in it.items():
        if L.is_palette(n):
            out['pal.' + n] = v
    d = it['kSpcSamples']
    n0, _ = struct.unpack_from('<HH', d, 0)
    n1, _ = struct.unpack_from('<HH', d, 4 + n0)
    blob = d[8 + n0:8 + n0 + n1]
    out['samples.brr'] = blob
    seen = set()
    for i in range(n0 // 4):
        s, _l = struct.unpack_from('<HH', d, 4 + i * 4)
        if s in seen:
            continue
        seen.add(s)
        pcm, _, _ = brr.decode(blob, s - L.SAMPLE_BASE)
        out['sample%02d.pcm' % len(seen)] = np.asarray(pcm, '<i2').tobytes()
    if it.get('kRom'):
        out['rom'] = it['kRom']
    return out, px


def lz2_spans(src):
    """Per compressed byte: (start, end) of the output its command writes."""
    spans, p, o = [], 0, 0
    while True:
        b = src[p]
        if b == 0xff:
            spans.append((o, o))
            break
        if (b & 0xe0) != 0xe0:
            cmd, n, h = b >> 5, (b & 0x1f) + 1, 1
        else:
            cmd, n, h = (b >> 2) & 7, (((b & 3) << 8) | src[p + 1]) + 1, 2
        size = h + (n if cmd == 0 else 1 if cmd in (1, 3) else 2)
        spans += [(o, o + n)] * size
        p += size
        o += n
    return spans


def flat_tiles(px):
    """Per tile: True when it is only kept facts: the silhouette, one colour on its border
    pixels and one colour inside (an outlined flat shape carries nothing else)."""
    n = len(px)
    img = tiles.sheet(px)
    sil = img > 0
    pad = np.pad(sil, 1, constant_values=True)
    edge = sil & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    et = tiles.unsheet(edge.astype(np.uint8))[:n].astype(bool)
    out = np.zeros(n, bool)
    for k in range(n):
        t, e = px[k], et[k]
        out[k] = len(np.unique(t[e])) <= 1 and len(np.unique(t[(t > 0) & ~e])) <= 1
    return out


def explained(cf, cpx):
    """label -> bool array (per byte) for the GFX streams of the clean file."""
    out = {}
    for i, px in cpx.items():
        tb = tiles.TILE_BYTES[L.BPP[i]]
        e = np.repeat(flat_tiles(px), tb)
        out['gfx%02X.planar' % i] = e
        key = 'gfx%02X.lz2' % i
        if key in cf:
            c = np.concatenate([[0], np.cumsum(~e)])
            sp = lz2_spans(cf[key])
            out[key] = np.array([c[min(b, len(e))] == c[min(a, len(e))] for a, b in sp] + [True] * (len(cf[key]) - len(sp)))
    return out


def runs(index, label, buf, expl=None):
    """Longest shared run in bytes, counting only unexplained bytes -> (run, offset, any)."""
    h, per = taint._hashes(buf)
    if not len(h) or not len(index):
        return 0, 0, False
    pos = np.minimum(np.searchsorted(index, h), len(index) - 1)
    a = np.frombuffer(buf, np.uint8)
    onebit = np.concatenate([[0], np.cumsum((a & (a - 1)) == 0)])     # bytes with at most one bit set
    walking = (onebit[taint.WINDOW:] - onebit[:-taint.WINDOW]) == taint.WINDOW
    m = (index[pos] == h) & ~per & ~walking[:len(h)]
    if not m.any():
        return 0, 0, False
    byte = np.zeros(len(buf) + 1, np.int32)
    idx = np.nonzero(m)[0]
    np.add.at(byte, idx, 1)
    np.add.at(byte, idx + taint.WINDOW, -1)
    matched = np.cumsum(byte)[:len(buf)] > 0
    if expl is not None:
        matched &= ~expl[:len(buf)]
    d = np.diff(np.concatenate([[0], matched.astype(np.int8), [0]]))
    st, en = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
    if not len(st):
        return 0, 0, True
    k = int((en - st).argmax())
    return int(en[k] - st[k]), int(st[k]), True


def pixel_report(dpx, cpx):
    same_tiles = info_tiles = bad_units = units = 0
    worst = []
    for i in dpx:
        d, c = dpx[i], cpx[i]
        n = min(len(d), len(c))
        d, c = d[:n].reshape(n, -1), c[:n].reshape(n, -1)
        ncol = np.array([len(np.unique(t)) for t in c])
        info = (ncol >= 3) & ~flat_tiles(cpx[i])[:n]
        same = (d == c).all(1) & info
        info_tiles += int(info.sum())
        same_tiles += int(same.sum())
        ds, cs = tiles.sheet(dpx[i][:n]), tiles.sheet(cpx[i][:n])
        f = flat_tiles(cpx[i])[:n]
        f = np.concatenate([f, np.ones(-n % 32, bool)]).reshape(-1, 16)
        flat = (f[0::2, 0::2] & f[0::2, 1::2] & f[1::2, 0::2] & f[1::2, 1::2]).repeat(2, 0).repeat(2, 1).ravel() if len(f) % 2 == 0 else np.zeros(n + 32, bool)
        k = 0
        for y in range(0, ds.shape[0] - 15, 16):
            for x in range(0, 128, 16):
                u = cs[y:y + 16, x:x + 16]
                if len(np.unique(u)) >= 4 and not flat[y // 8 * 16 + x // 8]:
                    units += 1
                    if (u == ds[y:y + 16, x:x + 16]).all():
                        bad_units += 1
                        k += 1
        if same.sum():
            worst.append((int(same.sum()), '%02X' % i))
    worst.sort(reverse=True)
    return same_tiles, info_tiles, bad_units, units, worst[:6]


def main(argv):
    dirty = argv[1] if len(argv) > 1 else 'D:/n64work/smw/dirty/smw_assets.dat'
    clean = argv[2] if len(argv) > 2 else 'D:/n64work/smw/clean/smw_assets.dat'
    shipped = argv[3:]
    df, dpx = forms(dirty)
    cf, cpx = forms(clean)
    assert 'rom' not in cf, 'clean asset file contains a ROM image'
    rom = df.pop('rom', None)
    index = taint.build_index(df.values())
    ex = explained(cf, cpx)
    res = [(lab,) + runs(index, lab, b, ex.get(lab)) for lab, b in cf.items()]
    hits = [r for r in res if r[3]]
    def limit(lab):          # planar tiles: two whole adjacent tiles (single tiles are the pixel rule's business)
        return 2 * tiles.TILE_BYTES[L.BPP[int(lab[3:5], 16)]] if lab.endswith('.planar') else taint.FAIL_RUN
    bad = sorted(((lab, off, 0, run) for lab, run, off, _ in res if run >= limit(lab)), key=lambda h: -h[3])
    ship_bad = []
    for p in shipped:
        b = open(p, 'rb').read()
        if os.path.basename(p) == os.path.basename(clean) or p.endswith('.data'):
            continue        # the asset package: scanned stream by stream above
        run, off, _ = runs(index, p, b)
        if run >= taint.FAIL_RUN:
            ship_bad.append((os.path.basename(p), off, 0, run))
    same, info, bad_units, units, worst = pixel_report(dpx, cpx)
    frac = same / max(info, 1)
    fail = len(bad) + len(ship_bad) + bad_units + (1 if frac > COINCIDENCE_LIMIT else 0)
    print('taint: %d clean streams vs %d retail streams; %d with short coincidental matches; %d failing (run >= %d B)' % (
        len(cf), len(df), len(hits) - len(bad), len(bad), taint.FAIL_RUN))
    for label, off, n, run in bad[:8]:
        print('  FAIL %s run %d B at %d' % (label, run, off))
    print('pixels: %d of %d informative 8x8 tiles identical (%.2f%%, limit %.0f%%) %s; %d of %d 16x16 units identical' % (
        same, info, 100 * frac, 100 * COINCIDENCE_LIMIT, worst, bad_units, units))
    print('shipped: %d files scanned, %d failing' % (len(shipped), len(ship_bad)))
    for label, off, n, run in ship_bad[:8]:
        print('  FAIL %s run %d B at %d' % (label, run, off))
    print('TOTAL failing: %d' % fail)
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
