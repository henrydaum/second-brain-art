from plugins.BaseTechnique import BaseTechnique, Slider, Pan, Palette

import numpy as np
from PIL import Image

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class BiomorphsTechnique(BaseTechnique):
    name = 'Biomorphs'
    description = 'Pickover biomorphs: the Julia iteration z -> z^n + c, but bailing out when EITHER the real or the imaginary part runs away, instead of the usual radius test. That one change grows the escape set into colonies of cell-like organisms — blobs trailing flagella and branching tendrils, looking eerily biological. Drag the center pad to move the complex constant c (the single biggest shape control: tiny moves morph the species). "power" sets the iteration exponent (2-6; higher = more symmetry arms), "bailout" the creature size, "detail" the iteration count. Good for "biomorph", "Pickover", "cells", "microorganisms", "Julia variant", "organic fractal", "amoeba", or a strange biological background.'
    kind = "background"

    palette = Palette()
    cx = Slider(-1.0, 1.0, default=0.5, step=0.005)
    cy = Slider(-1.0, 1.0, default=0.0, step=0.005)
    center = Pan(x="cx", y="cy")
    power = Slider(2, 6, default=3, step=1)
    bailout = Slider(2.0, 20.0, default=10.0, step=0.5)
    detail = Slider(12, 48, default=28, step=1)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        c = float(self.cx) + 1j * float(self.cy)
        power = int(self.power)
        T = float(self.bailout)
        maxiter = int(self.detail)

        span = 1.8
        ys, xs = np.mgrid[0:H, 0:W]
        re0 = (xs / (W - 1) * 2 - 1) * span
        im0 = (ys / (H - 1) * 2 - 1) * span * (H / W if W else 1.0)
        z = re0 + 1j * im0

        escaped = np.zeros((H, W), dtype=bool)
        itcount = np.zeros((H, W), dtype=np.float64)
        for i in range(maxiter):
            z = z ** power + c
            z = np.where(escaped, 0.0, z)
            newesc = (~escaped) & ((np.abs(z.real) > T) | (np.abs(z.imag) > T))
            itcount[newesc] = i
            escaped |= newesc

        # Exterior shells ramp up to the bright creature bodies (interior).
        t = np.where(escaped, 0.12 + 0.62 * (itcount / max(1, maxiter - 1)), 1.0)
        t = np.clip(t, 0.0, 1.0)

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(j / (LUT - 1)))
             for j in range(LUT)],
            dtype=np.uint8,
        )
        idx = np.clip((t * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        canvas.commit(Image.fromarray(lut[idx], "RGB").convert("RGBA"))
