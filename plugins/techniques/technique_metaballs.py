from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import math
import numpy as np
from PIL import Image, ImageFilter

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class MetaballsTechnique(BaseTechnique):
    name = 'Metaball Lava'
    description = 'Lava-lamp metaballs: several blobs whose scalar fields (radius squared over distance squared) sum and merge, thresholded into a soft palette surface with an inner glow. Each blob drifts on its own closed elliptical orbit, so sweeping "phase" loops seamlessly (Boomerang off) — the blobs return exactly to where they started. "blobs" sets how many, "gooeyness" softens the merge so they stretch and neck together, "radius" sizes them. Good for "metaballs", "lava lamp", "blobs", "goo", "liquid merge", or an organic morphing background.'
    kind = "background"

    palette = Palette()
    phase = Slider(0, 1, default=0, step=0.005)
    blobs = Slider(2, 8, default=5, step=1)
    gooeyness = Slider(0.0, 1.0, default=0.5, step=0.02)
    radius = Slider(0.05, 0.35, default=0.18, step=0.01)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        rng = np.random.default_rng(int(canvas.seed))
        ph = 2 * math.pi * float(self.phase)
        n = int(self.blobs)
        goo = float(self.gooeyness)
        rad = float(self.radius)

        _, _, nx, ny = art_kit.centered_grid(W, H)
        field = np.zeros((H, W), dtype=np.float32)
        for _ in range(n):
            bx, by = rng.uniform(-0.45, 0.45), rng.uniform(-0.45, 0.45)
            ox, oy = rng.uniform(0.15, 0.45), rng.uniform(0.15, 0.45)
            kx, ky = int(rng.integers(1, 3)), int(rng.integers(1, 3))
            sx, sy = rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi)
            ri = rad * rng.uniform(0.7, 1.3)
            cx = bx + ox * math.cos(ph * kx + sx)
            cy = by + oy * math.sin(ph * ky + sy)
            field += (ri * ri) / ((nx - cx) ** 2 + (ny - cy) ** 2 + 1e-4)

        # Soft iso-surface around field == 1.0; gooeyness widens the transition.
        soft = art_kit.lerp(0.08, 0.7, goo)
        m = np.clip((field - (1.0 - soft)) / (2.0 * soft), 0.0, 1.0)
        m = m * m * (3.0 - 2.0 * m)
        interior = np.tanh(field * 0.6)
        v = np.clip(0.12 + 0.55 * m + 0.4 * m * interior, 0.0, 1.0)

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(0.04 + 0.92 * (k / (LUT - 1))))
             for k in range(LUT)],
            dtype=np.uint8,
        )
        idx = np.clip((v * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        out = Image.fromarray(lut[idx], "RGB").convert("RGBA")
        glow = out.filter(ImageFilter.GaussianBlur(radius=max(W, H) * 0.006))
        canvas.commit(Image.alpha_composite(glow, out))
