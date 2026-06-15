from plugins.BaseTechnique import BaseTechnique, Pan, Slider

from PIL import Image


class CropTechnique(BaseTechnique):
    name = "Crop"
    description = "Filter: crop into the current image and resize back to canvas size; pan chooses the crop center."
    kind = "filter"
    zoom = Slider(1.0, 4.0, default=1.4, step=0.05)
    cx = Slider(0.0, 1.0, default=0.5, step=0.04)
    cy = Slider(0.0, 1.0, default=0.5, step=0.04)
    center = Pan(x="cx", y="cy")

    def run(self, canvas):
        W, H = canvas.width, canvas.height
        zoom = max(float(self.zoom), 1.0)
        # Crop a window with the canvas aspect ratio, then resize back to fill.
        cw = max(1, int(round(W / zoom)))
        ch = max(1, int(round(H / zoom)))
        hw, hh = cw / 2, ch / 2
        x = min(max(self.cx * W, hw), W - hw)
        y = min(max(self.cy * H, hh), H - hh)
        box = (int(round(x - hw)), int(round(y - hh)), int(round(x + hw)), int(round(y + hh)))
        canvas.commit(canvas.image.crop(box).resize((W, H), Image.Resampling.LANCZOS))
