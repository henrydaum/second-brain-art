from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import math
import numpy as np
from PIL import Image, ImageFilter

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class SpiralGalaxyTechnique(BaseTechnique):
    name = 'Spiral Galaxy'
    description = 'A spiral galaxy seen face-on: stars strewn along logarithmic arms that wind out of a bright bulging core, scattered with a faint halo and threaded by darker dust between the arms, all fading into deep space. Sweep "winding" to coil and uncoil the arms from a loose pinwheel to a tight whirlpool. Sweep "spin" instead for a seamless looping GIF — the galaxy rotates exactly one arm-step so the last frame rejoins the first (leave Boomerang off). "arms" sets the number of spiral arms, "glow" the soft bloom around the core and lanes. The core grades toward the palette accent. Good for "galaxy", "spiral galaxy", "nebula", "stars", "cosmos", "space", "milky way", "whirlpool", or a deep-space background.'
    kind = "background"

    palette = Palette()
    winding = Slider(0.4, 3.0, default=1.4, step=0.05)
    spin = Slider(0, 1, default=0, step=0.005)
    arms = Slider(2, 5, default=2, step=1)
    glow = Slider(0.5, 4.0, default=2.0, step=0.1)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        rng = np.random.default_rng(int(canvas.seed))
        winding = float(self.winding)
        arms = int(self.arms)
        spin_rot = float(self.spin) * 2.0 * math.pi / arms
        glow = float(self.glow)

        scale = 0.46 * min(W, H)
        cx, cy = W / 2.0, H / 2.0
        hist = np.zeros(H * W, dtype=np.float64)

        def splat(x, y, wgt):
            px = (cx + x * scale).astype(np.int64)
            py = (cy + y * scale).astype(np.int64)
            m = (px >= 0) & (px < W) & (py >= 0) & (py < H)
            hist[:] += np.bincount(py[m] * W + px[m],
                                   weights=wgt[m] if np.ndim(wgt) else None,
                                   minlength=H * W)

        # Spiral arms.
        per = 26000
        for a in range(arms):
            s = np.sqrt(rng.uniform(0.0, 1.0, per))           # radius fraction
            phi = (spin_rot + 2.0 * math.pi * a / arms
                   + winding * 2.0 * math.pi * s)
            jit = (0.018 + 0.05 * s)                          # arm thickens outward
            x = s * np.cos(phi) + rng.normal(0, 1, per) * jit
            y = s * np.sin(phi) + rng.normal(0, 1, per) * jit
            splat(x, y, np.ones(per))

        # Bright central bulge.
        nb = 30000
        rb = np.abs(rng.normal(0, 0.10, nb))
        ab = rng.uniform(0, 2 * math.pi, nb)
        splat(rb * np.cos(ab), rb * np.sin(ab), np.full(nb, 1.6))

        # Faint halo field.
        nf = 9000
        rf = np.sqrt(rng.uniform(0, 1, nf))
        af = rng.uniform(0, 2 * math.pi, nf)
        splat(rf * np.cos(af), rf * np.sin(af), np.full(nf, 0.35))

        dens = hist.reshape(H, W)
        v = np.log1p(dens)
        hi = float(np.percentile(v, 99.8)) or 1.0
        v = np.clip(v / hi, 0.0, 1.0)

        vimg = Image.fromarray((v * 255).astype(np.uint8), "L")
        vb = np.asarray(vimg.filter(ImageFilter.GaussianBlur(radius=glow)),
                        dtype=np.float64) / 255.0
        v = np.clip(v + 0.55 * vb, 0.0, 1.0) ** 0.85

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(0.02 + 0.96 * (j / (LUT - 1))))
             for j in range(LUT)],
            dtype=np.float64,
        )
        idx = np.clip((v * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        rgb = lut[idx]

        # Warm the core toward the accent.
        _, _, nx, ny = art_kit.centered_grid(W, H)
        core = np.exp(-(nx * nx + ny * ny) / (2 * 0.10 ** 2))[..., None]
        accent = np.array(art_kit.hex_to_rgb(canvas.palette.accent), dtype=np.float64)
        rgb = rgb * (1 - 0.5 * core) + accent * (0.5 * core) * (v[..., None])
        canvas.commit(Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB").convert("RGBA"))
