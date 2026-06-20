from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import math
import numpy as np
from PIL import Image, ImageFilter

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class QuasicrystalTechnique(BaseTechnique):
    name = 'Quasicrystal'
    description = 'A quasicrystal interference field: several plane waves of equal frequency, fanned out at equal angles, summed into a shimmering N-fold lattice with no repeating cell (distinct from the two-grid moire_interference). Sweep "phase" for a seamless looping GIF — every wave advances by exactly one period over a full sweep, so frame zero and the last frame match (leave Boomerang off). "symmetry" sets the rotational fold (5-, 7-, 11-fold all give classic Penrose-like quasicrystals), "frequency" the band density, "contrast" the crispness of the fringes. Good for "quasicrystal", "interference", "shimmer", "Penrose pattern", "wave lattice", "trippy", "hypnotic", or a kaleidoscopic animated background.'
    kind = "background"

    palette = Palette()
    symmetry = Slider(3, 12, default=7, step=1)
    phase = Slider(0, 1, default=0, step=0.005)
    frequency = Slider(4.0, 40.0, default=16.0, step=0.5)
    contrast = Slider(0.2, 3.0, default=1.0, step=0.05)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        n = int(self.symmetry)
        ph = 2 * math.pi * float(self.phase)
        freq = float(self.frequency)
        contrast = float(self.contrast)

        _, _, nx, ny = art_kit.centered_grid(W, H)
        field = np.zeros_like(nx)
        for k in range(n):
            theta = math.pi * k / n
            field += np.cos(freq * (nx * math.cos(theta) + ny * math.sin(theta)) + ph)

        v = field / n                              # ~[-1, 1]
        v = np.tanh(v * contrast)                  # squash, contrast control
        v = np.clip((v + 1.0) * 0.5, 0.0, 1.0)

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(0.04 + 0.92 * (j / (LUT - 1))))
             for j in range(LUT)],
            dtype=np.uint8,
        )
        idx = np.clip((v * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        out = Image.fromarray(lut[idx], "RGB").convert("RGBA")
        glow = out.filter(ImageFilter.GaussianBlur(radius=max(W, H) * 0.003))
        canvas.commit(Image.alpha_composite(glow, out))
