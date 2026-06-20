from plugins.BaseTechnique import BaseTechnique, Slider, Enum, Palette, Pan

from PIL import ImageDraw


W, H = 498.0, 433.0
PATHS = [
    [(211, 134), (249, 200), (154, 365), (496, 365), (458, 431), (40, 431)],
    [(211, 2), (2, 365), (40, 431), (211, 134), (306, 299), (382, 299)],
    [(496, 365), (287, 2), (211, 2), (382, 299), (192, 299), (154, 365)],
]


class PenroseTriangleTechnique(BaseTechnique):
    name = "Penrose Triangle"
    description = "Classic Penrose triangle from three filled SVG-style faces."
    kind = "object"
    palette = Palette()
    mode = Enum([("clean", "Clean")], default="clean")
    size = Slider(0.2, 0.9, default=0.68, step=0.02)
    pos_x = Slider(0.0, 1.0, default=0.5, step=0.02)
    pos_y = Slider(0.0, 1.0, default=0.52, step=0.02)
    position = Pan(x="pos_x", y="pos_y", label="Position")

    def run(self, canvas):
        scale = canvas.size * float(self.size) / W
        ox = canvas.size * float(self.pos_x) - W * scale / 2.0
        oy = canvas.size * float(self.pos_y) - H * scale / 2.0
        img = canvas.new_layer()
        draw = ImageDraw.Draw(img, "RGBA")
        colors = [canvas.palette.primary, canvas.palette.secondary, canvas.palette.tertiary]
        for pts, color in zip(PATHS, colors):
            poly = [(ox + x * scale, oy + y * scale) for x, y in pts]
            draw.polygon(poly, fill=color)
            draw.line(poly + [poly[0]], fill=canvas.palette.background, width=max(1, int(scale * 3)), joint="curve")
        canvas.commit(img)
