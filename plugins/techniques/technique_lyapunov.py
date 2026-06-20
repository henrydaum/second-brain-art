from plugins.BaseTechnique import BaseTechnique, Slider, Pan, Text, Palette

import numpy as np
from PIL import Image

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class LyapunovTechnique(BaseTechnique):
    name = 'Lyapunov Fractal'
    description = 'A Markus-Lyapunov fractal ("Zircon Zity"): the logistic map x -> r*x*(1-x) is iterated while its growth rate r alternates between two values a and b following a binary sequence string (A picks a, B picks b). The Lyapunov exponent at each (a, b) reveals swooping organic membranes of order against chaotic voids — not an escape-time fractal, so unlike the Mandelbrot/Julia/Newton family. "sequence" is the AB pattern that shapes everything (try "AB", "AABAB", "BBBBBBAAAAAA"). Sweep "zoom" for a smooth dive GIF; drag the center pad to explore the a-b plane. Good for "Lyapunov", "Zircon Zity", "logistic map", "chaos", "bifurcation", "organic fractal", or a strange ordered-vs-chaotic background.'
    kind = "background"

    palette = Palette()
    sequence = Text(default="AABAB", max_length=24, placeholder="A/B pattern")
    cx = Slider(2.0, 4.0, default=3.25, step=0.005)
    cy = Slider(2.0, 4.0, default=3.25, step=0.005)
    center = Pan(x="cx", y="cy")
    zoom = Slider(0.05, 0.85, default=0.75, step=0.005)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        seq = [c for c in str(self.sequence).upper() if c in ("A", "B")] or ["A", "B"]
        cx, cy = float(self.cx), float(self.cy)
        half = float(self.zoom)

        N = 320
        a_lo, a_hi = cx - half, cx + half
        b_lo, b_hi = cy - half, cy + half
        a = np.linspace(a_lo, a_hi, N)[None, :].repeat(N, axis=0)
        b = np.linspace(b_lo, b_hi, N)[:, None].repeat(N, axis=1)
        a = np.clip(a, 0.0, 4.0)
        b = np.clip(b, 0.0, 4.0)

        rs = [a if s == "A" else b for s in seq]
        L = len(rs)
        x = np.full((N, N), 0.5)
        for n in range(120):                       # warm-up, no accumulation
            x = rs[n % L] * x * (1.0 - x)
        lam = np.zeros((N, N))
        for n in range(240):                       # accumulate exponent
            r = rs[n % L]
            x = r * x * (1.0 - x)
            lam += np.log(np.abs(r * (1.0 - 2.0 * x)) + 1e-12)
        lam /= 240.0

        # Chaotic (lam > 0) -> dark background end; ordered (lam < 0) -> bright.
        t = np.clip(-lam / 1.2, 0.0, 1.0)
        t = np.where(lam > 0.0, 0.0, t)

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(j / (LUT - 1)))
             for j in range(LUT)],
            dtype=np.uint8,
        )
        idx = np.clip((t * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        small = Image.fromarray(lut[idx], "RGB")
        canvas.commit(small.resize((W, H), Image.BICUBIC).convert("RGBA"))
