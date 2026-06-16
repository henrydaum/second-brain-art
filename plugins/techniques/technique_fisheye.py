from plugins.BaseTechnique import BaseTechnique, Slider, Pan

import numpy as np

try:
    art_kit
except NameError:
    art_kit = None


class FisheyeTechnique(BaseTechnique):
    name = 'Fisheye'
    description = 'Lens distortion sample. Positive strength gives a fisheye bulge; negative gives pincushion (edges stretch). Pan moves the lens center.'
    kind = "filter"

    strength = Slider(-1.0, 1.0, default=0.6, step=0.1)
    zoom     = Slider(0.5, 3.0, default=2.0, step=0.1)
    cx       = Slider(0.0, 1.0, default=0.5, step=0.1)
    cy       = Slider(0.0, 1.0, default=0.5, step=0.1)
    center   = Pan(x='cx', y='cy')

    def run(self, canvas):
        arr = canvas.image_array(mode="RGB", dtype="float")
        W, H = int(canvas.width), int(canvas.height)
        ccx = self.cx * (W - 1)
        ccy = self.cy * (H - 1)
        # Normalize both axes by the same half-extent so the lens stays circular
        # on non-square canvases; sample the full W×H frame directly instead of
        # a square that would be center-cropped.
        half = max(W, H) / 2.0
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        nx = (xx - ccx) / half
        ny = (yy - ccy) / half
        r = np.sqrt(nx * nx + ny * ny)
        scale = (1.0 + self.strength * (r * r)) / max(self.zoom, 1e-3)
        sx = ccx + nx * scale * half
        sy = ccy + ny * scale * half
        canvas.commit_array(art_kit.bilinear_sample(arr, sx, sy))
