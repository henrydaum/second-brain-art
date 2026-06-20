from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import numpy as np
from PIL import Image

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class OilSlickTechnique(BaseTechnique):
    name = 'Oil Slick'
    description = 'Thin-film iridescence, the way a petrol sheen or a soap bubble splits light into shifting bands of colour. The canvas brightness, plus a slow fractal "film thickness", drives a cyclic walk through the palette, so equal-luminance contours of the image bloom into nested rainbow-like fringes — but every colour is drawn from the palette ramp, so it stays cohesive instead of garish. Sweep "thickness" for a seamless looping GIF: the interference bands flow through exactly one full cycle and the last frame rejoins the first (leave Boomerang off). "bands" sets how many fringes, "sharpness" how crisp their edges, "mix" how much of the original image shows through. A filter — run it over any background. Good for "oil slick", "iridescent", "thin film", "soap bubble", "petrol", "nacre", "interference", "holographic", or a colour-shifting sheen.'
    kind = "filter"

    palette = Palette()
    thickness = Slider(0, 1, default=0, step=0.005)
    bands = Slider(1.0, 8.0, default=4.0, step=0.25)
    sharpness = Slider(0.3, 3.0, default=1.0, step=0.05)
    mix = Slider(0.0, 0.8, default=0.3, step=0.02)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        seed = int(canvas.seed)
        arr = canvas.image_array(mode="RGB", dtype="float")
        thick = float(self.thickness)
        bands = float(self.bands)
        sharp = float(self.sharpness)
        mix = float(self.mix)

        lum = arr[..., 0] * 0.299 + arr[..., 1] * 0.587 + arr[..., 2] * 0.114

        yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
        film = art_kit.fbm_grid(seed, xx / W * 3.0, yy / H * 3.0, octaves=4)

        phase = lum * bands + 0.4 * film + thick
        frac = phase - np.floor(phase)
        tri = 1.0 - np.abs(2.0 * frac - 1.0)            # cyclic, seamless wrap
        t = tri ** sharp

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(j / (LUT - 1)))
             for j in range(LUT)],
            dtype=np.float64,
        ) / 255.0
        idx = np.clip((t * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        sheen = lut[idx]

        out = sheen * (1.0 - mix) + arr * mix
        canvas.commit_array(out)
