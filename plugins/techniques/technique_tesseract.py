from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import math
import numpy as np
from PIL import Image, ImageDraw

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class TesseractTechnique(BaseTechnique):
    name = 'Tesseract'
    description = 'A rotating 4-D hypercube (tesseract): sixteen vertices spun in two four-dimensional planes, then perspective-projected 4D->3D->2D, so the inner cube appears to swell, pass through, and turn inside-out of the outer one — a motion impossible for any 3-D object. Edges are depth-cued (nearer edges brighter and thicker) and coloured along the palette by 4-D depth. Sweep "rot_xw" for a seamless looping GIF: the cube completes exactly one 4-D turn, so the last frame matches the first (leave Boomerang off). "rot_zw" turns it in the second 4-D plane, "perspective" sets the projection distance (lower = more dramatic warping). An object layer — run it over a dark background. Good for "tesseract", "hypercube", "4D", "four dimensional", "wireframe", "inside out", "geometry", or a mind-bending rotating object.'
    kind = "object"

    palette = Palette()
    rot_xw = Slider(0, 1, default=0, step=0.005)
    rot_zw = Slider(0, 1, default=0.12, step=0.005)
    perspective = Slider(2.2, 6.0, default=3.2, step=0.1)
    scale = Slider(0.4, 0.95, default=0.7, step=0.01)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        th = 2 * math.pi * float(self.rot_xw)
        ph = 2 * math.pi * float(self.rot_zw)
        d4 = float(self.perspective)
        view_scale = float(self.scale)

        # 16 vertices of {-1,+1}^4.
        i = np.arange(16)
        bits = (i[:, None] >> np.arange(4)[None, :]) & 1
        V = (bits * 2 - 1).astype(np.float64)
        x, y, z, w = V[:, 0].copy(), V[:, 1].copy(), V[:, 2].copy(), V[:, 3].copy()

        # Two 4-D rotations.
        x, w = x * math.cos(th) - w * math.sin(th), x * math.sin(th) + w * math.cos(th)
        z, w = z * math.cos(ph) - w * math.sin(ph), z * math.sin(ph) + w * math.cos(ph)
        # Static 3-D tilt so it never sits edge-on.
        a, b = 0.62, 0.5
        x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
        x, z = x * math.cos(b) - z * math.sin(b), x * math.sin(b) + z * math.cos(b)

        # Project 4D -> 3D -> 2D (perspective at each stage).
        k4 = 1.0 / (d4 - w)
        x, y, z = x * k4, y * k4, z * k4
        d3 = 3.0
        k3 = 1.0 / (d3 - z)
        X, Y = x * k3, y * k3

        S = 2
        BW, BH = W * S, H * S
        img = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img, "RGBA")
        spread = 2.6 * min(BW, BH) * view_scale
        sx = BW / 2.0 + X * spread
        sy = BH / 2.0 + Y * spread

        wn = (w - w.min()) / ((w.max() - w.min()) or 1.0)     # 4-D depth 0..1

        edges = [(p, q) for p in range(16) for q in range(p + 1, 16)
                 if (p ^ q) & ((p ^ q) - 1) == 0]
        for p, q in edges:
            depth = 0.5 * (wn[p] + wn[q])
            color = art_kit.with_alpha(art_kit.palette_color(0.18 + 0.72 * depth), 240)
            lw = max(1, int(round(S * (1.0 + 2.6 * depth))))
            draw.line([(sx[p], sy[p]), (sx[q], sy[q])], fill=color, width=lw, joint="curve")

        # Vertex nodes for a little sparkle.
        for k in range(16):
            rr = S * (1.5 + 2.0 * wn[k])
            draw.ellipse([sx[k] - rr, sy[k] - rr, sx[k] + rr, sy[k] + rr],
                         fill=art_kit.with_alpha(canvas.palette.accent, 240))

        canvas.commit(img.resize((W, H), Image.LANCZOS))
