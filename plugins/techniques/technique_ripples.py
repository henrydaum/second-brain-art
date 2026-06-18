from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import math
import numpy as np
from PIL import Image

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class RipplesTechnique(BaseTechnique):
    name = 'Interference Ripples'
    description = 'A wave tank: several point sources each emit concentric sine rings, summed so they interfere into pools, ridges and quiet nodes — like raindrops on a pond. Sweeping "phase" makes every ring travel outward by one wavelength over the loop, so the GIF cycles seamlessly (Boomerang off). "sources" sets how many drop points, "frequency" the ring density, "sharpness" the crest contrast. Good for "interference", "ripples", "pond", "wave tank", "concentric waves", "raindrops", or a rhythmic animated background.'
    kind = "background"

    palette = Palette()
    phase = Slider(0, 1, default=0, step=0.005)
    sources = Slider(1, 6, default=3, step=1)
    frequency = Slider(4.0, 40.0, default=16.0, step=0.5)
    sharpness = Slider(0.0, 1.0, default=0.3, step=0.02)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        rng = np.random.default_rng(int(canvas.seed))
        ph = 2 * math.pi * float(self.phase)
        n = int(self.sources)
        freq = float(self.frequency)
        sharp = float(self.sharpness)

        _, _, nx, ny = art_kit.centered_grid(W, H)
        field = np.zeros((H, W), dtype=np.float32)
        for _ in range(n):
            cx, cy = rng.uniform(-0.7, 0.7), rng.uniform(-0.7, 0.7)
            d = np.sqrt((nx - cx) ** 2 + (ny - cy) ** 2)
            field += np.sin(freq * d - ph)
        field /= max(1, n)                       # ~[-1, 1]

        v = (field + 1.0) * 0.5
        k = art_kit.lerp(1.0, 6.0, sharp)        # contrast around the midline
        v = np.clip(0.5 + (v - 0.5) * k, 0.0, 1.0)

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(0.05 + 0.9 * (j / (LUT - 1))))
             for j in range(LUT)],
            dtype=np.uint8,
        )
        idx = np.clip((v * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        canvas.commit(Image.fromarray(lut[idx], "RGB").convert("RGBA"))
