from plugins.BaseTechnique import BaseTechnique, Slider

from PIL import Image

try:
    art_kit
except NameError:
    art_kit = None


class PixelateTechnique(BaseTechnique):
    name = 'Pixelate'
    description = 'Block-mean downsample then nearest-neighbour upsample. Classic chunky-pixel look. Bigger block_size = bigger pixels.'
    kind = "filter"

    block_size = Slider(2, 80, default=12, step=1)

    def run(self, canvas):
        b = int(self.block_size)
        W, H = int(canvas.width), int(canvas.height)
        small_w = max(1, W // b)
        small_h = max(1, H // b)
        img = canvas.image.convert("RGBA")
        tiny = img.resize((small_w, small_h), Image.BILINEAR)
        out = tiny.resize((W, H), Image.NEAREST)
        canvas.commit(out)
