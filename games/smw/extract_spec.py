"""DIRTY ROOM. Reads the retail-derived smw_assets.dat and writes the spec of kept
facts: kept.dat (code-side tables, levels, text, sequences), gfx.json (per 16x16
sprite unit: silhouette + 4x4 index grid + edge index), pal.json (3 bit/channel
colours), samples.json (length, loop, coarse outline, pitch)."""
import sys, os, json, struct
import numpy as np
from games.smw import assetfile as A, layout as L
from cleanroom.snes import lz2, tiles, brr
from cleanroom.audio import descriptor

SPEC = os.path.join(os.path.dirname(__file__), 'spec')


def sheets(it):
    out = [lz2.decompress(c) for c in A.unpack_array(it['kGraphicsPtrs'])]
    return out + [it['kGfx32'], it['kGfx33']]


def mode(vals, default=0):
    vals = vals[vals > 0]
    return int(np.bincount(vals).argmax()) if len(vals) else default


def default_rgb(it, bpp):
    """A typical palette for sprite sheets (only used to pick one index per cell)."""
    def cols(v):
        w = np.frombuffer(v, '<u2').astype(np.int32)
        return np.stack([w & 31, w >> 5 & 31, w >> 10 & 31], -1).astype(float)
    spr = cols(it['kGlobalPalettes_Objects'])[48:54]         # black, 3 shades, 2 skin tones
    rgb = np.zeros((16, 3))
    rgb[1] = 31
    rgb[2:8] = spr
    if bpp == 4:
        rgb[6:16] = cols(it['kPlayerPalettes'])[:10]
    return rgb


def gfx_spec(raw, bpp, rgb=None):
    img = tiles.sheet(tiles.decode(raw, bpp))
    h, w = img.shape
    if h % 16:
        img = np.vstack([img, np.zeros((16 - h % 16, w), np.uint8)])
    sil = img > 0
    pad = np.pad(sil, 1, constant_values=True)
    edge = sil & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    units = []
    for uy in range(0, img.shape[0], 16):
        for ux in range(0, w, 16):
            u = img[uy:uy + 16, ux:ux + 16]
            s = sil[uy:uy + 16, ux:ux + 16]
            if not s.any():
                units.append(None)
                continue
            e = u[edge[uy:uy + 16, ux:ux + 16]]
            ec = mode(e) if len(e) >= 8 else 0      # an outline colour only for sprite-like shapes
            grid = []
            for y in range(0, 16, 4):
                for x in range(0, 16, 4):
                    c = u[y:y + 4, x:x + 4].ravel()
                    if not ec or rgb is None:   # background tile: commonest index
                        grid.append(mode(c))
                        continue
                    # sprite: the index nearest to the cell's mean colour (outline left out), so shades
                    # of one colour are not outvoted by a highlight
                    c2 = c[(c != ec) & (c > 0)]
                    if not len(c2):
                        grid.append(mode(c))
                        continue
                    have = np.unique(c2)
                    m = rgb[c2].mean(0)
                    grid.append(int(have[((rgb[have] - m) ** 2).sum(1).argmin()]))
            units.append({'sil': np.packbits(s).tobytes().hex(), 'grid': ''.join('%x' % g for g in grid), 'edge': ec})
    return {'bpp': bpp, 'bytes': len(raw), 'units': units}


def loop_outline(loop):
    """Coarse outline of a looping section: cycles per loop + harmonic levels in whole dB."""
    x = loop.astype(np.float64)
    n = len(x)
    spec = np.abs(np.fft.rfft(x)) / n * 2
    f0, _ = descriptor._f0(np.tile(x, max(2, 4096 // n + 1))[:4096], L.RATE)
    cyc = int(np.clip(round(f0 * n / L.RATE), 1, n // 4)) if f0 > 0 else int(spec[1:n // 4].argmax() + 1)
    harm = []
    for k in range(1, 33):
        b = cyc * k
        harm.append(int(max(-60, round(20 * np.log10(spec[b] / 32768 + 1e-9)))) if b < len(spec) else -60)
    return {'cycles': cyc, 'harm_db': harm}


def sample_spec(d):
    n0, a0 = struct.unpack_from('<HH', d, 0)
    assert a0 == L.SAMPLE_DIR
    dirb = d[4:4 + n0]
    n1, a1 = struct.unpack_from('<HH', d, 4 + n0)
    assert a1 == L.SAMPLE_BASE
    blob = d[8 + n0:8 + n0 + n1]
    tail = d[8 + n0 + n1:]
    entries, bodies, order = [], {}, []
    for i in range(n0 // 4):
        s, l = struct.unpack_from('<HH', dirb, i * 4)
        if s not in bodies:
            pcm, used, loop = brr.decode(blob, s - a1)
            nb = used // 9
            e = {'offset': s - a1, 'blocks': nb, 'loop': loop}
            env = [int(max(-90, round(20 * np.log10(np.sqrt(np.mean((pcm[k:k + 64].astype(float) / 32768) ** 2)) + 1e-9))))
                   for k in range(0, len(pcm), 64)]
            e['env_db'] = env                      # level per 4 blocks (2 ms), whole dB
            e['desc'] = descriptor.describe(pcm, L.RATE)
            if loop:
                lb = (l - s) // 9
                e['loop_block'] = lb
                e['loop_outline'] = loop_outline(pcm[lb * 16:])
            bodies[s] = len(order)
            order.append(e)
        entries.append(bodies[s])
    print('sample bytes %d of %d used' % (sum(e['blocks'] for e in order) * 9, n1))
    return {'dir': entries, 'samples': order, 'dir_bytes': n0, 'blob_bytes': n1, 'tail': tail.hex()}


def main(path):
    items = A.read(path)
    it = dict(items)
    os.makedirs(SPEC, exist_ok=True)
    kept = [(n, b'' if L.is_regenerated(n) else v) for n, v in items]
    A.write(os.path.join(SPEC, 'kept.dat'), kept)
    ss = sheets(it)
    gfx = {'%02X' % i: gfx_spec(s, L.BPP[i], default_rgb(it, L.BPP[i]) if L.BPP[i] > 2 else None) for i, s in enumerate(ss)}
    json.dump(gfx, open(os.path.join(SPEC, 'gfx.json'), 'w'), separators=(',', ':'))
    pal = {}
    for n, v in items:
        if L.is_palette(n):
            w = np.frombuffer(v, '<u2').astype(np.int32)
            c = np.stack([w & 31, w >> 5 & 31, w >> 10 & 31], -1)
            pal[n] = ''.join('%d%d%d' % tuple(x) for x in ((c * 7 + 15) // 31))
    json.dump(pal, open(os.path.join(SPEC, 'pal.json'), 'w'), indent=0)
    smp = sample_spec(it['kSpcSamples'])
    json.dump(smp, open(os.path.join(SPEC, 'samples.json'), 'w'), separators=(',', ':'))
    nu = sum(1 for g in gfx.values() for u in g['units'] if u)
    print('kept entries %d (%d bytes), regenerated %d' % (sum(1 for n, v in kept if v), sum(len(v) for _, v in kept),
                                                         sum(1 for n, _ in kept if L.is_regenerated(n))))
    print('gfx sheets %d, sprite units %d; palettes %d (%d colours); samples %d (dir %d)' % (
        len(gfx), nu, len(pal), sum(len(v) // 3 for v in pal.values()), len(smp['samples']), len(smp['dir'])))
    print('loops:', [(i, s['blocks'] - s['loop_block'], s['loop_outline']['cycles']) for i, s in enumerate(smp['samples']) if s['loop']])


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'D:/n64work/smw/dirty/smw_assets.dat')
