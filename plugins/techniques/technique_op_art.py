from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import math
import numpy as np
from PIL import Image

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class OpArtTechnique(BaseTechnique):
    name = 'Op Art'
    description = 'Bridget Riley / Vasarely optical-art: a field of crisp stripes whose position is warped by travelling waves, so the flat lines appear to swell, pinch, and ripple into three dimensions that are not there. Sweep "bend" to push the illusion from flat lines into a heaving bulge. Sweep "phase" instead for a seamless looping GIF — the warp waves travel through exactly one period and the last frame rejoins the first, so the surface seems to breathe forever (leave Boomerang off). "frequency" sets the stripe density, "contrast" the hardness of the edges. Reads strongest in a two-tone (light/dark) palette. Good for "op art", "optical illusion", "Bridget Riley", "Vasarely", "stripes", "moire", "bulge", "kinetic", or a hypnotic black-and-white background.'
    kind = "background"

    palette = Palette()
    bend = Slider(0.0, 1.2, default=0.5, step=0.02)
    phase = Slider(0, 1, default=0, step=0.005)
    frequency = Slider(8.0, 40.0, default=20.0, step=1.0)
    contrast = Slider(1.0, 8.0, default=4.0, step=0.25)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        seed = int(canvas.seed)
        bend = float(self.bend)
        ph = 2 * math.pi * float(self.phase)
        freq = float(self.frequency)
        contrast = float(self.contrast)

        _, _, nx, ny = art_kit.centered_grid(W, H)
        fb = art_kit.fbm_grid(seed, nx * 2.0 + 4.0, ny * 2.0, octaves=4) - 0.5

        # Stripes along x, displaced by two travelling waves + a static fbm bend.
        warp = bend * (np.sin(2 * math.pi * (1.3 * ny) + ph)
                       + 0.6 * np.sin(2 * math.pi * (0.7 * nx) - ph)
                       + 0.8 * fb)
        theta = 2 * math.pi * (freq * nx + warp)
        v = 0.5 + 0.5 * np.tanh(contrast * np.sin(theta))

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(j / (LUT - 1)))
             for j in range(LUT)],
            dtype=np.uint8,
        )
        idx = np.clip((v * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        canvas.commit(Image.fromarray(lut[idx], "RGB").convert("RGBA"))
