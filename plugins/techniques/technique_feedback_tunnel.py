from plugins.BaseTechnique import BaseTechnique, Slider

import math
import numpy as np

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class FeedbackTunnelTechnique(BaseTechnique):
    name = 'Feedback Tunnel'
    description = 'Video feedback, the camera-pointed-at-its-own-monitor effect: the canvas is layered over zoomed, rotated, fading copies of itself, each echo a little smaller and turned a little more, drilling the image into a spiralling tunnel. Sweep "rotation" for a great GIF — the whole tunnel winds tighter and spins as the echoes rotate. "zoom" sets how fast each echo shrinks (the tunnel depth), "decay" how quickly the echoes fade (low = short trail, high = deep infinite tunnel), "tint" pushes the receding copies toward the palette accent so depth reads as colour. A filter — run it over any background. Good for "feedback", "video feedback", "echo", "tunnel", "trails", "spiral", "infinite", "psychedelic", or a recursive depth effect.'
    kind = "filter"

    rotation = Slider(-0.6, 0.6, default=0.18, step=0.01)
    zoom = Slider(1.04, 1.6, default=1.18, step=0.01)
    decay = Slider(0.3, 0.95, default=0.78, step=0.01)
    tint = Slider(0.0, 1.0, default=0.45, step=0.02)

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        arr = canvas.image_array(mode="RGB", dtype="float")
        rot = float(self.rotation)
        zoom = float(self.zoom)
        decay = float(self.decay)
        tint = float(self.tint)

        ys, xs = np.mgrid[0:H, 0:W].astype(np.float64)
        cx, cy = (W - 1) / 2.0, (H - 1) / 2.0
        dx = xs - cx
        dy = ys - cy

        accent = np.array(art_kit.hex_to_rgb(canvas.palette.accent), dtype=np.float64) / 255.0

        N = 14
        out = np.zeros((H, W, 3), dtype=np.float64)
        wsum = 0.0
        for i in range(N):
            f = zoom ** i
            th = -rot * i
            c_, s_ = math.cos(th), math.sin(th)
            qx = cx + f * (dx * c_ - dy * s_)
            qy = cy + f * (dx * s_ + dy * c_)
            echo = art_kit.bilinear_sample(arr, qx, qy)
            ti = (i / (N - 1)) * tint
            echo = echo * (1.0 - ti) + accent * ti
            w = decay ** i
            out += w * echo
            wsum += w

        canvas.commit_array(out / (wsum or 1.0))
