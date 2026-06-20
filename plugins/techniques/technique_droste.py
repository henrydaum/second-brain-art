from plugins.BaseTechnique import BaseTechnique, Slider

import math
import numpy as np

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class DrosteTechnique(BaseTechnique):
    name = 'Droste'
    description = 'The Droste effect: the canvas spirals into a smaller, rotated copy of itself, forever. A conformal log-polar remap wraps the image onto a logarithmic spiral so each ring inward is the whole picture shrunk by "zoom" and turned by "arms" whole rotations — the seams match exactly, so it tiles seamlessly. Sweep "zoom_phase" for a hypnotic seamless infinite-zoom GIF: the spiral scrolls inward by exactly one ring over a full sweep, so the last frame is identical to the first (leave Boomerang off). "arms" sets the spiral turns per ring (0 = straight Droste tunnel, higher = tighter swirl), "zoom" the shrink ratio per ring. A filter — run it over any background. Good for "Droste", "infinite zoom", "recursive", "picture in picture", "Escher", "log spiral", "self-similar", or a mind-bending recursive effect.'
    kind = "filter"

    zoom_phase = Slider(0, 1, default=0, step=0.005)
    arms = Slider(0, 6, default=1, step=1)
    zoom = Slider(1.5, 8.0, default=3.0, step=0.1)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        arr = canvas.image_array(mode="RGB", dtype="float")
        ph = float(self.zoom_phase)
        arms = int(self.arms)
        ratio = float(self.zoom)

        _, _, nx, ny = art_kit.centered_grid(W, H)
        r = np.hypot(nx, ny) + 1e-6
        ang = np.arctan2(ny, nx)

        R1 = 1.0 / ratio                         # inner radius of the tiling ring
        P = math.log(1.0 / R1)                   # one ring in log-radius = ln(ratio)
        lr = np.log(r) - ph * P                  # scroll inward over the phase sweep
        u = np.mod(lr, P)                        # fold into one ring -> [0, P)

        sr = R1 * np.exp(u)                      # source radius in [R1, 1]
        # Rotate by `arms` whole turns across one ring so the seam matches.
        sa = ang + (u / P) * (2.0 * math.pi * arms)

        half = 0.5 * min(W, H)
        cx, cy = (W - 1) / 2.0, (H - 1) / 2.0
        sx = cx + sr * np.cos(sa) * half * (max(W, H) / min(W, H))
        sy = cy + sr * np.sin(sa) * half * (max(W, H) / min(W, H))

        canvas.commit_array(art_kit.bilinear_sample(arr, sx, sy))
