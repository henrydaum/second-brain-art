from plugins.BaseTechnique import BaseTechnique, Slider, Palette

import math
from PIL import Image, ImageDraw, ImageFilter

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class PhyllotaxisBloomTechnique(BaseTechnique):
    name = 'Phyllotaxis Bloom'
    description = 'A sunflower seed head: dots placed by the golden angle (Vogel spiral) so they pack into the interlocking clockwise/counter-clockwise spirals of real phyllotaxis. The whole bloom rotates as "phase" sweeps and each ring of seeds breathes in and out, so a full sweep returns to the start for a seamless loop (Boomerang off). "count" is the seed count, "dot" scales the marks, "spread" the bloom radius; color ramps from core to rim. Good for "phyllotaxis", "sunflower", "golden angle", "Fermat spiral", "seed head", "Vogel", or a rotating botanical background.'
    kind = "background"

    palette = Palette()
    phase = Slider(0, 1, default=0, step=0.005)
    count = Slider(50, 1200, default=600, step=10)
    dot = Slider(0.2, 1.5, default=0.8, step=0.05)
    spread = Slider(0.6, 1.4, default=1.0, step=0.05)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        ph = 2 * math.pi * float(self.phase)
        n = int(self.count)
        dotmul = float(self.dot)
        spread = float(self.spread)

        img = Image.new("RGBA", (W, H), canvas.palette.background)
        draw = ImageDraw.Draw(img, "RGBA")
        cx, cy = W / 2.0, H / 2.0
        R = min(W, H) * 0.46 * spread
        base_dot = max(1.0, min(W, H) * 0.012 * dotmul)
        ca, sa = math.cos(ph), math.sin(ph)

        for px, py in art_kit.vogel_spiral(n, scale=1.0):
            rx = px * ca - py * sa                # rigid rotation by phase
            ry = px * sa + py * ca
            x, y = cx + rx * R, cy + ry * R
            rr = math.sqrt(px * px + py * py)     # 0 (core) .. 1 (rim)
            pulse = 0.7 + 0.3 * math.sin(ph + rr * 6.0)
            sz = base_dot * (0.4 + 0.9 * rr) * pulse
            col = art_kit.palette_color(0.15 + 0.8 * rr)
            draw.ellipse([x - sz, y - sz, x + sz, y + sz], fill=col)

        glow = img.filter(ImageFilter.GaussianBlur(radius=min(W, H) * 0.004))
        canvas.commit(Image.alpha_composite(glow, img))
