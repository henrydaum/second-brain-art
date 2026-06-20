from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import numpy as np
from PIL import Image, ImageFilter

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class KleinianTechnique(BaseTechnique):
    name = 'Kleinian Pearls'
    description = 'Indra\'s Pearls: the limit set of a two-generator Kleinian group, built from the classic "Grandma\'s recipe" Mobius transforms. Iterating the group on a starting point traces a necklace of circles nested within circles within circles — the loxodromic cousin of the apollonian gasket, spiralling into itself without end. Sweep "tangency" for a striking morphing GIF: at 0 the pearls kiss in a tangent gasket, and as it rises the chains bloom into double-spiral whirls. "zoom" frames or dives into the necklace, "detail" trades render time for density. Built on the same vectorized point-iteration as the fractal flame. Good for "Kleinian", "Indra\'s pearls", "Mobius", "Schottky group", "limit set", "circle inversion", "quasi-fuchsian", or a deep recursive fractal background.'
    kind = "background"

    palette = Palette()
    tangency = Slider(0, 1, default=0.35, step=0.01)
    zoom = Slider(0.4, 2.0, default=0.85, step=0.02)
    detail = Slider(40, 140, default=90, step=5)
    glow = Slider(0.0, 2.0, default=0.7, step=0.05)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        rng = np.random.default_rng(int(canvas.seed))
        tang = float(self.tangency)
        zoom = float(self.zoom)
        K = int(self.detail)
        glow = float(self.glow)

        # Grandma's recipe (Maskit / "Indra's Pearls") for traces ta, tb.
        ta = 2.0 + 0.0j
        tb = 2.0 + tang * 1.2j
        tab = (ta * tb - np.sqrt((ta * tb) ** 2 - 4.0 * (ta * ta + tb * tb))) / 2.0
        z0 = (tab - 2.0) * tb / (tb * tab - 2.0 * ta + 2.0j * tab)

        a00 = ta / 2.0
        a01 = (ta * tab - 2.0 * tb + 4.0j) / ((2.0 * tab + 4.0) * z0)
        a10 = (ta * tab - 2.0 * tb - 4.0j) * z0 / (2.0 * tab - 4.0)
        a11 = ta / 2.0
        b00 = (tb - 2.0j) / 2.0
        b01 = tb / 2.0
        b10 = tb / 2.0
        b11 = (tb + 2.0j) / 2.0

        # Generators a, A=a^-1, b, B=b^-1 (SL2C, det 1 -> inverse swaps diag, negates off).
        G00 = np.array([a00, a11, b00, b11])
        G01 = np.array([a01, -a01, b01, -b01])
        G10 = np.array([a10, -a10, b10, -b10])
        G11 = np.array([a11, a00, b11, b00])

        # Reduced-word walk: never immediately undo the previous generator.
        allowed = np.array([[0, 2, 3], [1, 2, 3], [0, 1, 2], [0, 1, 3]])

        M = 16000
        warm = 25
        z = rng.normal(0, 0.4, M) + 1j * rng.normal(0, 0.4, M)
        last = rng.integers(0, 4, M)
        col = rng.uniform(0, 1, M)

        scale = 0.22 * min(W, H) * zoom
        cx, cy = W / 2.0, H / 2.0
        dens = np.zeros(H * W, dtype=np.float64)
        csum = np.zeros(H * W, dtype=np.float64)

        for step in range(K):
            r = rng.integers(0, 3, M)
            nxt = allowed[last, r]
            num = G00[nxt] * z + G01[nxt]
            den = G10[nxt] * z + G11[nxt]
            z = num / den
            last = nxt
            col = 0.5 * (col + nxt / 3.0)

            if step >= warm:
                fin = np.isfinite(z.real) & np.isfinite(z.imag)
                px = (cx + z.real * scale).astype(np.int64)
                py = (cy + z.imag * scale).astype(np.int64)
                m = fin & (px >= 0) & (px < W) & (py >= 0) & (py < H)
                flat = py[m] * W + px[m]
                dens += np.bincount(flat, minlength=H * W)
                csum += np.bincount(flat, weights=col[m], minlength=H * W)

        dens = dens.reshape(H, W)
        cavg = csum.reshape(H, W) / np.maximum(dens, 1.0)
        bright = np.log1p(dens)
        hi = float(np.percentile(bright, 99.7)) or 1.0
        bright = np.clip(bright / hi, 0.0, 1.0)

        if glow > 0:
            bimg = Image.fromarray((bright * 255).astype(np.uint8), "L")
            bb = np.asarray(bimg.filter(ImageFilter.GaussianBlur(radius=glow)),
                            dtype=np.float64) / 255.0
            bright = np.clip(bright + 0.5 * bb, 0.0, 1.0)

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(j / (LUT - 1)))
             for j in range(LUT)],
            dtype=np.uint8,
        )
        t = np.clip(bright * (0.15 + 0.85 * cavg), 0.0, 1.0)
        idx = np.clip((t * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        canvas.commit(Image.fromarray(lut[idx], "RGB").convert("RGBA"))
