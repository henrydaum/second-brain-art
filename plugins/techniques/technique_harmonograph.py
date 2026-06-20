from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import math
import random
import numpy as np
from PIL import Image, ImageDraw

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class HarmonographTechnique(BaseTechnique):
    name = 'Harmonograph'
    description = 'A simulated harmonograph: two damped pendulums trace a decaying Lissajous pen-plot, the curve spiralling inward as friction bleeds the swing away — the Victorian drawing machine, distinct from spirograph epicycloids. "ratio" is the frequency ratio between the pendulums and is the heart of the figure: small changes morph it from a simple loop through roses into dense knots, so sweeping it makes a mesmerising shape-shifting GIF. Sweep "phase" instead for a seamless looping GIF (every oscillator advances one full cycle, so the last frame rejoins the first; leave Boomerang off). "damping" sets how fast the curve decays inward, "detune" adds the slow drift that opens the lines into ribbons. Good for "harmonograph", "Lissajous", "pendulum", "damped curve", "spirograph alternative", "string art", or an elegant line-art background.'
    kind = "background"

    palette = Palette()
    ratio = Slider(1.0, 6.0, default=3.0, step=0.01)
    phase = Slider(0, 1, default=0, step=0.005)
    damping = Slider(0.0005, 0.02, default=0.004, step=0.0005)
    detune = Slider(0.0, 0.04, default=0.012, step=0.001)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        rng = random.Random(canvas.seed)
        ratio = float(self.ratio)
        ph = 2 * math.pi * float(self.phase)
        damp = float(self.damping)
        det = float(self.detune)

        img = canvas.create_image()
        draw = ImageDraw.Draw(img, "RGBA")

        cx, cy = W / 2.0, H / 2.0
        amp = 0.42 * min(W, H)
        # Four oscillators; seed gives each plot its own character.
        f1, f2 = 1.0, ratio
        f3, f4 = ratio + det, 1.0 + det
        p1 = ph + rng.uniform(0, math.pi)
        p2 = ph + rng.uniform(0, math.pi)
        p3 = ph + math.pi / 2 + rng.uniform(0, math.pi)
        p4 = ph + rng.uniform(0, math.pi)

        n = 9000
        t = np.linspace(0.0, 64.0 * math.pi, n)
        e = np.exp(-damp * t)
        x = cx + amp * 0.5 * (np.sin(f1 * t + p1) + np.sin(f2 * t + p2)) * e
        y = cy + amp * 0.5 * (np.sin(f3 * t + p3) + np.sin(f4 * t + p4)) * e

        pts = np.stack([x, y], axis=1)
        buckets = 96
        per = max(2, n // buckets)
        for k in range(0, n - 1, per):
            seg = pts[k:k + per + 1]
            color = art_kit.palette_color(0.12 + 0.86 * (k / (n - 1)))
            draw.line([tuple(p) for p in seg], fill=color, width=2, joint="curve")
        canvas.commit(img)
