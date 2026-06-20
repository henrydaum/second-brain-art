from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import math
import numpy as np
from PIL import Image

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class MarbleTechnique(BaseTechnique):
    name = 'Marble'
    description = 'Iterative domain warping (fbm of fbm of fbm) in the Inigo Quilez style: a noise field samples itself twice over, folding smooth turbulence into liquid marble veins, agate banding, and nebula filaments — softer and more organic than the sine-based plasma_flow. Sweep "flow" for a seamless looping GIF: the inner warp offset travels one full circle, so the veins drift and the last frame rejoins the first (leave Boomerang off). "warp" sets how violently the field folds (0 = smooth bands, 3 = churned marble), "scale" the vein size, "octaves" the fine detail. Good for "marble", "domain warp", "agate", "nebula", "liquid", "ink", "turbulence", "fractal noise", or a slowly flowing abstract background.'
    kind = "background"

    palette = Palette()
    warp = Slider(0.0, 3.0, default=1.4, step=0.05)
    flow = Slider(0, 1, default=0, step=0.005)
    scale = Slider(0.8, 5.0, default=2.2, step=0.1)
    octaves = Slider(2, 7, default=5, step=1)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        seed = int(canvas.seed)
        warp = float(self.warp)
        ph = 2 * math.pi * float(self.flow)
        sc = float(self.scale)
        oct_ = int(self.octaves)

        # Coarse lattice, upscaled — fbm-of-fbm is 5 noise passes.
        N = 256
        yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
        xx = (xx / N) * sc
        yy = (yy / N) * sc * (H / W if W else 1.0)

        # Inner warp offset travels a full circle over flow → seamless loop.
        ox, oy = 0.4 * math.cos(ph), 0.4 * math.sin(ph)

        def fb(ax, ay, s):
            return art_kit.fbm_grid(seed + s, ax, ay, octaves=oct_)

        qx = fb(xx + ox, yy + oy, 0)
        qy = fb(xx + 5.2 + ox, yy + 1.3 + oy, 1)
        rx = fb(xx + warp * qx + 1.7, yy + warp * qy + 9.2, 2)
        ry = fb(xx + warp * qx + 8.3, yy + warp * qy + 2.8, 3)
        v = fb(xx + warp * rx, yy + warp * ry, 4)

        lo, hi = float(v.min()), float(v.max())
        v = np.clip((v - lo) / ((hi - lo) or 1.0), 0.0, 1.0)

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(j / (LUT - 1)))
             for j in range(LUT)],
            dtype=np.uint8,
        )
        idx = np.clip((v * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        small = Image.fromarray(lut[idx], "RGB")
        canvas.commit(small.resize((W, H), Image.BICUBIC).convert("RGBA"))
