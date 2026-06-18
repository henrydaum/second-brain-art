from plugins.BaseTechnique import BaseTechnique, Slider

import math
import numpy as np

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class LiquidWarpTechnique(BaseTechnique):
    name = 'Liquid Warp'
    description = 'A filter that ripples whatever is beneath it: pixels are resampled along a travelling sine displacement, like looking through water or heat haze. Drop it on top of any layer and sweep "phase" for a seamless underwater shimmer (Boomerang off) — the displacement returns to zero over a full sweep. "amplitude" is the wobble distance, "frequency" the ripple count, "swirl" mixes in a rotational current around the centre. Good for "liquid", "water", "underwater", "heat haze", "wobble", "displacement", "warp", or animating a static layer.'
    kind = "filter"

    phase = Slider(0, 1, default=0, step=0.005)
    amplitude = Slider(0.0, 0.08, default=0.03, step=0.002)
    frequency = Slider(1.0, 12.0, default=4.0, step=0.5)
    swirl = Slider(0.0, 1.0, default=0.2, step=0.02)

    def run(self, canvas):
        arr = canvas.image_array(mode="RGB", dtype="float")
        H, W = arr.shape[:2]
        ph = 2 * math.pi * float(self.phase)
        amp = float(self.amplitude) * max(W, H)
        freq = float(self.frequency)
        swirl = float(self.swirl)

        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        u = xx / max(1, W) * 2.0 * math.pi * freq
        v = yy / max(1, H) * 2.0 * math.pi * freq
        dx = amp * np.sin(v + ph)
        dy = amp * np.sin(u + ph)

        if swirl > 0:
            ang = np.arctan2(yy - H / 2.0, xx - W / 2.0)
            dx += swirl * amp * np.cos(ang + ph)
            dy += swirl * amp * np.sin(ang + ph)

        canvas.commit_array(art_kit.bilinear_sample(arr, xx + dx, yy + dy))
