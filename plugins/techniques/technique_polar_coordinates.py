from plugins.BaseTechnique import BaseTechnique, Slider, Enum

import math
import numpy as np

try:
    art_kit
except NameError:
    art_kit = None


class PolarCoordinatesTechnique(BaseTechnique):
    name = 'Polar Coordinates'
    description = 'Remap rectangular ↔ polar coordinates. "to_polar" wraps the image as a circle; "from_polar" unrolls it into a strip.'
    kind = "filter"

    mode     = Enum([('to_polar', 'To Polar'), ('from_polar', 'From Polar')], default='to_polar')
    rotation = Slider(0, 360, default=0, step=1)

    def run(self, canvas):
        arr = canvas.image_array(mode="RGB", dtype="float")
        W, H = int(canvas.width), int(canvas.height)
        rot = math.radians(float(self.rotation))
        # Output a full W×H frame instead of a square that would be
        # center-cropped: angle runs across the width, radius across the height.
        xx, yy, _, _ = art_kit.centered_grid(W, H)
        cx = (W - 1) / 2.0
        cy = (H - 1) / 2.0
        if self.mode == 'to_polar':
            theta = (xx / max(W - 1, 1)) * 2.0 * math.pi + rot
            radius = (yy / max(H - 1, 1)) * (H / 2.0)
            sx = cx + np.cos(theta) * radius
            sy = cy + np.sin(theta) * radius
        else:
            dx = xx - cx
            dy = yy - cy
            r = np.sqrt(dx * dx + dy * dy)
            theta = (np.arctan2(dy, dx) - rot) % (2.0 * math.pi)
            sx = (theta / (2.0 * math.pi)) * (W - 1)
            sy = (r / (H / 2.0)) * (H - 1)
        canvas.commit_array(art_kit.bilinear_sample(arr, sx, sy))
