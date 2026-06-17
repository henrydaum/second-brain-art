from plugins.BaseTechnique import BaseTechnique, Slider

import math
import numpy as np

try:
    art_kit
except NameError:
    art_kit = None


class KaleidoscopeTechnique(BaseTechnique):
    name = 'Kaleidoscope'
    description = 'Fold N angular wedges around the center; the result is N-fold rotational symmetry from a single source slice.'
    kind = "filter"

    segments = Slider(3, 24, default=8, step=1)
    rotation = Slider(0, 360, default=0, step=1, loop=True)

    def run(self, canvas):
        n = int(self.segments)
        rot = math.radians(float(self.rotation))
        arr = canvas.image_array(mode="RGB", dtype="float")
        W, H = canvas.width, canvas.height
        xx, yy, _, _ = art_kit.centered_grid(W, H)
        cx = (W - 1) / 2.0
        cy = (H - 1) / 2.0
        dx = xx - cx
        dy = yy - cy
        r = np.sqrt(dx * dx + dy * dy)
        theta = np.arctan2(dy, dx) - rot
        wedge = 2.0 * math.pi / n
        t = np.mod(theta, 2.0 * wedge)
        t = np.where(t > wedge, 2.0 * wedge - t, t)
        sx = cx + np.cos(t + rot) * r
        sy = cy + np.sin(t + rot) * r
        canvas.commit_array(art_kit.bilinear_sample(arr, sx, sy))
