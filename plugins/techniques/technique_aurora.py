from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import math
import numpy as np
from PIL import Image, ImageFilter

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class AuroraTechnique(BaseTechnique):
    name = 'Aurora'
    description = 'Northern-lights curtains: sinuous vertical sheets of light sway across the sky, streaked with fine rising rays and fading upward into the dark, their edges broken up by fractal noise so no two folds match. Sweep "shimmer" for a seamless looping GIF — the curtains sway through one full cycle and the last frame rejoins the first (leave Boomerang off). "bands" sets how many curtains, "height" how far the glow climbs the sky, "rays" the fine vertical filament detail. Reads best with a cool palette (greens, teals, violets). Good for "aurora", "northern lights", "borealis", "curtains of light", "night sky", or a slow shimmering atmospheric background.'
    kind = "background"

    palette = Palette()
    shimmer = Slider(0, 1, default=0, step=0.005)
    bands = Slider(2, 7, default=4, step=1)
    height = Slider(0.15, 0.55, default=0.32, step=0.01)
    rays = Slider(0.0, 1.0, default=0.6, step=0.02)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        seed = int(canvas.seed)
        ph = 2 * math.pi * float(self.shimmer)
        bands = int(self.bands)
        hv = float(self.height)
        rays = float(self.rays)

        ys, xs = np.mgrid[0:H, 0:W]
        X = xs / W
        Y = ys / H                                   # 0 = top, 1 = bottom

        fb = art_kit.fbm_grid(seed, X * 3.0, Y * 4.0, octaves=4)

        inten = np.zeros((H, W))
        width = (1.0 / bands) * 0.16            # thin, distinct sheets
        for i in range(bands):
            base = (i + 0.5) / bands
            # Gentle near-vertical sway so each curtain stays a coherent sheet.
            sway = 0.05 * np.sin(2 * math.pi * (0.5 * Y + ph) + i * 2.1) \
                + 0.025 * (fb - 0.5)
            d = X - (base + sway)
            inten += np.exp(-(d * d) / (2 * width * width))

        # Curtain hangs from above: brightest in the upper-mid sky, trailing down.
        vprof = np.exp(-((Y - 0.42) ** 2) / (2 * hv * hv))
        vprof *= np.clip((Y - 0.04) / 0.16, 0.0, 1.0)       # soft top edge
        ray_tex = 1.0 - rays * 0.45 * (0.5 + 0.5 * np.sin(X * bands * 22.0 + 6.0 * fb))

        v = inten * vprof * ray_tex
        lo, hi = float(v.min()), float(v.max())
        v = np.clip((v - lo) / ((hi - lo) or 1.0), 0.0, 1.0)
        v = v ** 0.8

        # Glow in value-space (screen with a blurred copy) so every pixel
        # still resolves to a palette colour — no off-ramp drift.
        vimg = Image.fromarray((v * 255).astype(np.uint8), "L")
        vb = np.asarray(vimg.filter(ImageFilter.GaussianBlur(radius=max(W, H) * 0.012)),
                        dtype=np.float64) / 255.0
        v = 1.0 - (1.0 - v) * (1.0 - 0.5 * vb)

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(j / (LUT - 1)))
             for j in range(LUT)],
            dtype=np.uint8,
        )
        idx = np.clip((v * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        canvas.commit(Image.fromarray(lut[idx], "RGB").convert("RGBA"))
