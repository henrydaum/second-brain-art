from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import math
from PIL import Image, ImageDraw

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class MandalaTechnique(BaseTechnique):
    name = 'Sacred Geometry Mandala'
    description = 'A line-art mandala overlaid on the current canvas: a Flower-of-Life ring of overlapping circles, nested rotating star-polygons, radial spokes and a bounding circle, all drawn in palette ink on transparent space so the background shows through the gaps. An object layer — run it over a background. Sweep "spin" for a seamless looping GIF: the whole figure rotates exactly one symmetry step, so the last frame matches the first (leave Boomerang off). "symmetry" sets the fold (6 gives the classic Flower of Life; 8 and 12 read as compass roses), "rings" the number of nested polygons, "scale" the overall size. Good for "mandala", "sacred geometry", "Flower of Life", "Metatron", "compass rose", "kaleidoscope overlay", "line art", "symmetry", or a spiritual geometric overlay.'
    kind = "object"

    palette = Palette()
    symmetry = Slider(4, 12, default=6, step=1)
    rings = Slider(2, 8, default=5, step=1)
    spin = Slider(0, 1, default=0, step=0.005)
    scale = Slider(0.5, 0.95, default=0.82, step=0.01)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        sym = int(self.symmetry)
        rings = int(self.rings)
        spin_rot = (2.0 * math.pi / sym) * float(self.spin)
        scale = float(self.scale)

        S = 2                                   # supersample for crisp strokes
        BW, BH = W * S, H * S
        img = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img, "RGBA")
        cx, cy = BW / 2.0, BH / 2.0
        R = 0.5 * min(BW, BH) * scale
        lw = max(1, int(round(1.5 * S)))

        def ring_color(t):
            return art_kit.with_alpha(art_kit.palette_color(0.2 + 0.7 * t), 235)

        # Bounding circle.
        draw.ellipse([cx - R, cy - R, cx + R, cy + R],
                     outline=art_kit.with_alpha(canvas.palette.secondary, 235), width=lw)

        # Flower of Life: central circle + a symmetry-ring of overlapping circles.
        pr = R / 2.0
        draw.ellipse([cx - pr, cy - pr, cx + pr, cy + pr],
                     outline=ring_color(0.5), width=lw)
        for i in range(sym):
            a = spin_rot + 2.0 * math.pi * i / sym
            px, py = cx + pr * math.cos(a), cy + pr * math.sin(a)
            draw.ellipse([px - pr, py - pr, px + pr, py + pr],
                         outline=ring_color(i / sym), width=lw)

        # Nested rotating star-polygons.
        for k in range(rings):
            rk = R * (0.22 + 0.78 * (k + 1) / rings)
            rot = spin_rot + k * (math.pi / sym) / max(1, rings)
            pts = art_kit.regular_polygon(cx, cy, rk, sym, rotation=rot)
            draw.line([tuple(p) for p in pts] + [tuple(pts[0])],
                      fill=ring_color((k + 1) / rings), width=lw, joint="curve")

        # Radial spokes to the rim.
        for i in range(sym):
            a = spin_rot + 2.0 * math.pi * i / sym
            draw.line([cx, cy, cx + R * math.cos(a), cy + R * math.sin(a)],
                      fill=art_kit.with_alpha(canvas.palette.accent, 200),
                      width=max(1, lw // 2))

        out = img.resize((W, H), Image.LANCZOS)
        canvas.commit(out)
