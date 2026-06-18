from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import math
import numpy as np
from PIL import Image

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class VortexTechnique(BaseTechnique):
    name = 'Infinite Vortex'
    description = 'A Droste log-spiral tunnel: bands defined on log(radius) and angle wind into a swirling funnel, with a darkened core for depth. Because the pattern repeats every ring, sweeping "phase" scrolls the bands exactly one ring inward — a seamless infinite zoom (leave Boomerang off). "twist" sets how many spiral arms, "rings" the band density, "depth" the core vignette. Good for "vortex", "tunnel", "Droste", "infinite zoom", "log spiral", "hypnotic", "wormhole", or a spinning focal background.'
    kind = "background"

    palette = Palette()
    phase = Slider(0, 1, default=0, step=0.005)
    twist = Slider(0.0, 6.0, default=2.0, step=0.1)
    rings = Slider(2.0, 16.0, default=6.0, step=0.5)
    depth = Slider(0.3, 1.0, default=0.6, step=0.02)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        ph = float(self.phase)
        twist = float(self.twist)
        rings = float(self.rings)
        depth = float(self.depth)

        _, _, nx, ny = art_kit.centered_grid(W, H)
        r = np.sqrt(nx * nx + ny * ny) + 1e-4
        ang = np.arctan2(ny, nx)

        band = np.log(r) * rings + twist * ang / (2.0 * math.pi) - ph
        frac = band - np.floor(band)
        tri = 1.0 - np.abs(frac * 2.0 - 1.0)     # symmetric: no seam at the wrap
        tri = tri * tri * (3.0 - 2.0 * tri)

        vig = np.clip(r / 1.05, 0.0, 1.0)        # 0 at core, 1 at rim
        v = np.clip(tri * (depth + (1.0 - depth) * vig), 0.0, 1.0)

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(0.04 + 0.92 * (k / (LUT - 1))))
             for k in range(LUT)],
            dtype=np.uint8,
        )
        idx = np.clip((v * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        canvas.commit(Image.fromarray(lut[idx], "RGB").convert("RGBA"))
