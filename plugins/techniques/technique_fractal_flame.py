from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import numpy as np
from PIL import Image, ImageFilter

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class FractalFlameTechnique(BaseTechnique):
    name = 'Fractal Flame'
    description = 'A fractal flame in the Apophysis / Electric Sheep style: a random affine map is chosen each step and the point pushed through a blend of nonlinear "variations" (sinusoidal, spherical, swirl) before being plotted, building up the gauzy, luminous, smoke-like filaments that ordinary IFS fractals (attractor_cloud) cannot. Density is log-tonemapped for that glowing translucency and coloured along the palette by orbit. Sweep "variation" to morph the whole organism from rounded sinusoidal lobes to spiky spherical tendrils — a striking shape-shifting GIF. "swirl" twists the flame, "gamma" controls the glow/contrast of the tonemap, and the seed reshapes the affine maps entirely. Good for "fractal flame", "Apophysis", "Electric Sheep", "IFS", "plasma tendrils", "glow", "smoke", or a luminous abstract background.'
    kind = "background"

    palette = Palette()
    variation = Slider(0, 1, default=0.5, step=0.01)
    swirl = Slider(0.0, 1.0, default=0.3, step=0.02)
    gamma = Slider(0.3, 1.0, default=0.55, step=0.02)
    zoom = Slider(0.5, 1.6, default=0.9, step=0.05)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        rng = np.random.default_rng(int(canvas.seed))
        var = float(self.variation)
        swirl = float(self.swirl)
        gamma = float(self.gamma)
        zoom = float(self.zoom)

        nmaps = 3
        coeff = rng.uniform(-1.0, 1.0, (nmaps, 6))           # affine a..f
        mcol = rng.uniform(0.0, 1.0, nmaps)                  # per-map colour coord

        M = 9000
        K = 130
        warm = 20
        scale = 0.30 * min(W, H) * zoom
        cx, cy = W / 2.0, H / 2.0

        x = rng.uniform(-1, 1, M)
        y = rng.uniform(-1, 1, M)
        col = rng.uniform(0, 1, M)

        dens = np.zeros(H * W, dtype=np.float64)
        csum = np.zeros(H * W, dtype=np.float64)

        for step in range(K):
            idx = rng.integers(0, nmaps, M)
            c = coeff[idx]
            ax = c[:, 0] * x + c[:, 1] * y + c[:, 2]
            ay = c[:, 3] * x + c[:, 4] * y + c[:, 5]

            r2 = np.maximum(ax * ax + ay * ay, 1e-6)
            sphere_x, sphere_y = ax / r2, ay / r2
            sr2 = np.sin(r2)
            cr2 = np.cos(r2)
            swx = ax * sr2 - ay * cr2
            swy = ax * cr2 + ay * sr2

            x = (1 - var) * np.sin(ax) + var * sphere_x + swirl * swx
            y = (1 - var) * np.sin(ay) + var * sphere_y + swirl * swy
            col = 0.5 * (col + mcol[idx])

            if step >= warm:
                px = (cx + x * scale).astype(np.int64)
                py = (cy + y * scale).astype(np.int64)
                m = (px >= 0) & (px < W) & (py >= 0) & (py < H) & np.isfinite(x) & np.isfinite(y)
                flat = py[m] * W + px[m]
                dens += np.bincount(flat, minlength=H * W)
                csum += np.bincount(flat, weights=col[m], minlength=H * W)

        dens = dens.reshape(H, W)
        cavg = (csum.reshape(H, W) / np.maximum(dens, 1.0))

        bright = np.log1p(dens)
        hi = float(np.percentile(bright, 99.7)) or 1.0
        bright = np.clip(bright / hi, 0.0, 1.0) ** gamma
        bimg = Image.fromarray((bright * 255).astype(np.uint8), "L")
        bb = np.asarray(bimg.filter(ImageFilter.GaussianBlur(radius=0.8)),
                        dtype=np.float64) / 255.0
        bright = np.clip(bright + 0.4 * bb, 0.0, 1.0)

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(j / (LUT - 1)))
             for j in range(LUT)],
            dtype=np.uint8,
        )
        # Brightness drives ramp position (dark space -> glowing core), orbit
        # colour shifts where along the ramp — every pixel is an exact palette
        # colour, so no drift.
        t = np.clip(bright * (0.15 + 0.85 * cavg), 0.0, 1.0)
        idx = np.clip((t * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        canvas.commit(Image.fromarray(lut[idx], "RGB").convert("RGBA"))
