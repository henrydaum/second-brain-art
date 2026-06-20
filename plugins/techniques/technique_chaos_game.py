from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import math
import numpy as np
from PIL import Image, ImageFilter

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class ChaosGameTechnique(BaseTechnique):
    name = 'Chaos Game'
    description = 'The chaos game: drop a point, then repeatedly jump a fixed fraction of the way toward a randomly chosen corner of a polygon, plotting every landing. Order emerges from randomness — N corners with the right jump "ratio" condense into the Sierpinski triangle, Vicsek crosses, n-flake snowflakes, and a continuum of unnamed self-similar fractals in between. "ratio" is the master dial: sweeping it morphs smoothly from a dense blob through lacy fractals to scattered dust, which makes a mesmerising GIF. "points" sets the number of corners, "spin" rotates the corner ring (0-1 seamless loop). Distinct from barnsley_fern and sierpinski_triangle (fixed maps). Good for "chaos game", "Sierpinski", "Vicsek", "n-flake", "iterated function system", "fractal dust", or a morphing geometric background.'
    kind = "background"

    palette = Palette()
    points = Slider(3, 8, default=5, step=1)
    ratio = Slider(0.3, 0.7, default=0.5, step=0.005)
    spin = Slider(0, 1, default=0, step=0.005)
    glow = Slider(0.0, 2.0, default=0.8, step=0.05)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        rng = np.random.default_rng(int(canvas.seed))
        N = int(self.points)
        ratio = float(self.ratio)
        ang0 = float(self.spin) * 2.0 * math.pi / N
        glow = float(self.glow)

        k = np.arange(N)
        va = ang0 + 2.0 * math.pi * k / N - math.pi / 2.0
        verts = np.stack([np.cos(va), np.sin(va)], axis=1)

        M = 6000          # parallel walkers
        K = 150           # steps each
        warm = 15
        scale = 0.46 * min(W, H)
        cx, cy = W / 2.0, H / 2.0

        pos = verts[rng.integers(0, N, M)].astype(np.float64)
        hist = np.zeros(H * W, dtype=np.float64)
        for step in range(K):
            tgt = verts[rng.integers(0, N, M)]
            pos = pos * (1.0 - ratio) + ratio * tgt
            if step >= warm:
                px = (cx + pos[:, 0] * scale).astype(np.int64)
                py = (cy + pos[:, 1] * scale).astype(np.int64)
                m = (px >= 0) & (px < W) & (py >= 0) & (py < H)
                hist += np.bincount(py[m] * W + px[m], minlength=H * W)

        dens = hist.reshape(H, W)
        v = np.log1p(dens)
        hi = float(v.max()) or 1.0
        v = v / hi

        if glow > 0:
            vimg = Image.fromarray((np.clip(v, 0, 1) * 255).astype(np.uint8), "L")
            vb = np.asarray(vimg.filter(ImageFilter.GaussianBlur(radius=glow)),
                            dtype=np.float64) / 255.0
            v = np.clip(v + 0.6 * vb, 0.0, 1.0)

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(0.02 + 0.96 * (j / (LUT - 1))))
             for j in range(LUT)],
            dtype=np.uint8,
        )
        idx = np.clip((v * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        canvas.commit(Image.fromarray(lut[idx], "RGB").convert("RGBA"))
