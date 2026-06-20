from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import math
import numpy as np
from PIL import Image

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class CausticsTechnique(BaseTechnique):
    name = 'Caustics'
    description = 'Underwater light caustics: a smooth turbulent surface refracts parallel light, and wherever the warp folds and focuses, bright filaments flare into the rippling net of light you see on a pool floor. Computed from the Jacobian of an fbm displacement field — the folds (compression) glow, the flats stay dark. Sweep "phase" for a seamless looping GIF: the surface drifts through one full cycle and the net flows continuously back to the start (leave Boomerang off). "scale" sets the ripple size, "warp" how strongly the light is bent (and thus how tangled the web), "glow" the brightness falloff of the filaments. Good for "caustics", "underwater", "water light", "pool", "refraction", "ripples", "dappled light", or a calming flowing background.'
    kind = "background"

    palette = Palette()
    phase = Slider(0, 1, default=0, step=0.005)
    scale = Slider(1.0, 6.0, default=2.6, step=0.1)
    warp = Slider(0.2, 2.5, default=1.1, step=0.05)
    glow = Slider(0.3, 3.0, default=1.2, step=0.05)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        seed = int(canvas.seed)
        ph = 2 * math.pi * float(self.phase)
        sc = float(self.scale)
        warp = float(self.warp)
        glow = float(self.glow)

        yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
        xx = (xx / W) * sc
        yy = (yy / H) * sc * (H / W if W else 1.0)

        # Displacement field drifts on a circle over phase -> seamless loop.
        ox, oy = 0.5 * math.cos(ph), 0.5 * math.sin(ph)
        dx = art_kit.fbm_grid(seed, xx + ox, yy + oy, octaves=3) - 0.5
        dy = art_kit.fbm_grid(seed + 9, xx + 3.1 + ox, yy + 1.7 + oy, octaves=3) - 0.5

        # Jacobian determinant of the warp x -> x + warp*d ; |J|->0 at caustics.
        ux = np.gradient(dx, axis=1) * W / sc
        uy = np.gradient(dx, axis=0) * H / sc
        vx = np.gradient(dy, axis=1) * W / sc
        vy = np.gradient(dy, axis=0) * H / sc
        J = (1.0 + warp * ux) * (1.0 + warp * vy) - (warp * uy) * (warp * vx)

        bright = 1.0 / (1.0 + (np.abs(J) * 2.5) ** glow)
        lo, hi = float(np.percentile(bright, 2)), float(np.percentile(bright, 99.5))
        v = np.clip((bright - lo) / ((hi - lo) or 1.0), 0.0, 1.0)
        v = v ** 0.85

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(0.02 + 0.96 * (j / (LUT - 1))))
             for j in range(LUT)],
            dtype=np.uint8,
        )
        idx = np.clip((v * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        canvas.commit(Image.fromarray(lut[idx], "RGB").convert("RGBA"))
