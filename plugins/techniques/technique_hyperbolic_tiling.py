from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import math
import numpy as np
from PIL import Image

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class HyperbolicTilingTechnique(BaseTechnique):
    name = 'Hyperbolic Tiling'
    description = 'A regular {p, q} tessellation of the hyperbolic plane drawn in the Poincare disk: p-sided cells, q meeting at every vertex, shrinking forever toward the rim so infinitely many identical tiles crowd the edge — the Escher "Circle Limit" geometry. Each pixel is folded back into the central cell by rotational symmetry plus inversion across the cell-edge geodesic; the fold depth paints concentric shells and a kaleidoscopic two-colouring. Sweep "spin" for a seamless looping GIF — the disk rotates exactly one cell-step, so the last frame rejoins the first (leave Boomerang off). "p" sets the polygon sides, "q" how many meet per vertex (needs 1/p + 1/q < 1/2 for hyperbolic; auto-corrected otherwise), "depth" the fold limit near the rim. Good for "hyperbolic", "Poincare disk", "Circle Limit", "Escher", "tessellation", "non-euclidean", or a hypnotic infinite-tiling background.'
    kind = "background"

    palette = Palette()
    p = Slider(3, 8, default=5, step=1)
    q = Slider(4, 8, default=4, step=1)
    spin = Slider(0, 1, default=0, step=0.005)
    depth = Slider(6, 40, default=24, step=1)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        p = int(self.p)
        q = int(self.q)
        # Enforce a hyperbolic Schlafli pair: 1/p + 1/q < 1/2.
        while (p - 2) * (q - 2) <= 4:
            q += 1
        max_iter = int(self.depth)

        # Cell-edge geodesic (orthogonal to the unit circle, crossing +x):
        #   cx = cos(pi/q) / sqrt(cos^2(pi/q) - sin^2(pi/p)),  r = sqrt(cx^2 - 1)
        sp = math.sin(math.pi / p)
        cqq = math.cos(math.pi / q)
        cx = cqq / math.sqrt(cqq * cqq - sp * sp)
        r = math.sqrt(cx * cx - 1.0)
        r2 = r * r
        sector = 2.0 * math.pi / p

        _, _, nx, ny = art_kit.centered_grid(W, H)
        # Rotate the whole disk by one cell-step over a spin sweep -> seamless.
        rot = sector * float(self.spin)
        ca, sa = math.cos(rot), math.sin(rot)
        x = nx * ca - ny * sa
        y = nx * sa + ny * ca

        inside_disk = (x * x + y * y) < 0.999
        depth = np.zeros((H, W), dtype=np.int32)
        parity = np.zeros((H, W), dtype=np.int32)

        for _ in range(max_iter):
            ang = np.arctan2(y, x)
            k = np.round(ang / sector)
            ang2 = ang - sector * k
            rad = np.hypot(x, y)
            x = rad * np.cos(ang2)
            y = rad * np.sin(ang2)
            neg = y < 0.0
            y = np.abs(y)
            parity += neg.astype(np.int32) + np.abs(k).astype(np.int32)

            dx = x - cx
            d2 = dx * dx + y * y
            inside = (d2 < r2) & (d2 > 1e-12)
            scale = np.where(inside, r2 / np.where(d2 == 0, 1.0, d2), 1.0)
            x = np.where(inside, cx + dx * scale, x)
            y = np.where(inside, y * scale, y)
            depth += inside.astype(np.int32)
            if not inside.any():
                break

        # Colour: fold-depth shells along the ramp, alternate triangles darkened.
        t = 0.12 + 0.8 * np.clip(depth / max(6.0, max_iter * 0.6), 0.0, 1.0)
        t = t - 0.16 * (parity % 2)
        t = np.clip(t, 0.0, 1.0)

        LUT = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(j / (LUT - 1)))
             for j in range(LUT)],
            dtype=np.uint8,
        )
        idx = np.clip((t * (LUT - 1)).astype(np.int32), 0, LUT - 1)
        rgb = lut[idx]
        bg = np.array(art_kit.hex_to_rgb(canvas.palette.background), dtype=np.uint8)
        rgb[~inside_disk] = bg
        canvas.commit(Image.fromarray(rgb, "RGB").convert("RGBA"))
