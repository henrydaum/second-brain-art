from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import math
import numpy as np
from PIL import Image, ImageFilter

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class PlasmaFlowTechnique(BaseTechnique):
    name = 'Plasma Flow'
    description = 'Demoscene plasma: a field summed from several travelling sine waves plus a radial and a swirling term, lightly domain-warped, then pushed through the palette ramp. Sweep "phase" for a seamless looping GIF — every wave advances by exactly one period over a full sweep, so frame zero and the last frame match (leave Boomerang off). "scale" sets the spatial frequency, "warp" bends the grid, "swirl" adds a rotational arm. Good for "plasma", "demoscene", "flow", "liquid color", "organic gradient", or a hypnotic animated background.'
    kind = "background"

    palette = Palette()
    phase = Slider(0, 1, default=0, step=0.005)
    scale = Slider(0.5, 6.0, default=2.2, step=0.1)
    warp = Slider(0.0, 1.0, default=0.4, step=0.02)
    swirl = Slider(0.0, 1.0, default=0.3, step=0.02)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        ph = 2 * math.pi * float(self.phase)
        sc = float(self.scale)
        warp = float(self.warp)
        swirl = float(self.swirl)

        _, _, nx, ny = art_kit.centered_grid(W, H)
        x = nx * sc * math.pi
        y = ny * sc * math.pi
        # Domain warp: displace the sample coordinates by a slow travelling wave.
        wx = x + warp * np.sin(y * 1.7 + ph)
        wy = y + warp * np.cos(x * 1.3 - ph)
        r = np.sqrt(nx * nx + ny * ny)
        ang = np.arctan2(ny, nx)

        field = (np.sin(wx + ph)
                 + np.sin(wy * 0.9 - ph)
                 + np.sin((wx + wy) * 0.6 + ph)
                 + np.sin(r * sc * 3.0 - 2.0 * ph)
                 + swirl * np.sin(ang * 3.0 + r * sc * 2.0 + ph))

        v = field / (4.0 + swirl)            # to ~[-1, 1]
        v = np.clip((v + 1.0) * 0.5, 0.0, 1.0)
        v = v * v * (3.0 - 2.0 * v)          # smoothstep contrast

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(0.05 + 0.9 * (k / (LUT - 1))))
             for k in range(LUT)],
            dtype=np.uint8,
        )
        idx = np.clip((v * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        out = Image.fromarray(lut[idx], "RGB").convert("RGBA")
        glow = out.filter(ImageFilter.GaussianBlur(radius=max(W, H) * 0.004))
        canvas.commit(Image.alpha_composite(glow, out))
