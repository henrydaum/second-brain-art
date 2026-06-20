from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import math
import numpy as np
from PIL import Image

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class WaveInterferenceTechnique(BaseTechnique):
    name = 'Wave Interference'
    description = 'A ripple tank: several point sources each send out concentric waves that overlap and add, carving the bright antinodes and dark nodal lines of an interference pattern — at two sources it is the classic double-slit fringe, at more it becomes a woven lattice of light. Sweep "phase" for a seamless looping GIF: every source advances exactly one wavelength so the ripples flow outward forever and the last frame rejoins the first (leave Boomerang off). "sources" sets how many emitters (placed evenly on a ring), "frequency" the ripple density, "contrast" how hard the fringes read. Distinct from ripples (a single drop) and moire_interference (rotated grids). Good for "interference", "ripple tank", "double slit", "waves", "diffraction", "nodal lines", "standing wave", or a rhythmic physics-y background.'
    kind = "background"

    palette = Palette()
    sources = Slider(2, 6, default=3, step=1)
    phase = Slider(0, 1, default=0, step=0.005)
    frequency = Slider(5.0, 30.0, default=14.0, step=0.5)
    contrast = Slider(0.5, 4.0, default=1.5, step=0.1)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        seed = int(canvas.seed)
        n = int(self.sources)
        ph = 2 * math.pi * float(self.phase)
        freq = float(self.frequency)
        contrast = float(self.contrast)

        _, _, nx, ny = art_kit.centered_grid(W, H)
        offset = (seed % 360) * math.pi / 180.0     # seed rotates the emitter ring
        field = np.zeros_like(nx)
        R = 0.55
        for i in range(n):
            a = offset + 2.0 * math.pi * i / n
            sx, sy = R * math.cos(a), R * math.sin(a)
            d = np.sqrt((nx - sx) ** 2 + (ny - sy) ** 2)
            field += np.sin(2 * math.pi * freq * d - ph) / (0.35 + d)

        v = np.tanh(field * contrast / n)
        v = np.clip((v + 1.0) * 0.5, 0.0, 1.0)

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(0.03 + 0.94 * (j / (LUT - 1))))
             for j in range(LUT)],
            dtype=np.uint8,
        )
        idx = np.clip((v * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        canvas.commit(Image.fromarray(lut[idx], "RGB").convert("RGBA"))
