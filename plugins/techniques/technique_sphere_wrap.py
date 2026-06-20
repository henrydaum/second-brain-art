from plugins.BaseTechnique import BaseTechnique, Slider, Bool

import math
import numpy as np

try:
    art_kit  # injected by sandbox at exec time
except NameError:
    art_kit = None


class SphereWrapTechnique(BaseTechnique):
    name = 'Sphere Wrap'
    description = 'Wraps the current canvas around a 3-D sphere seen face-on, turning any image into a planet or marble: each pixel inside the disk is back-projected to a longitude and latitude on the globe, the source sampled there, then shaded with a sun-lit terminator and a soft rim so it reads as a solid ball floating on the background. The pinched poles dissolve into smooth caps so even a texture with dark or mismatched edges wraps cleanly. By default it wraps like a globe (a world-map look), but a texture whose left and right edges differ will show a faint vertical seam; turn on "seamless" to instead read the texture in polar coordinates so there is no seam at all — the content swirls radially around the poles (the same result as running Polar Coordinates "to polar" before this filter, but in one layer). Sweep "rotation" for a seamless looping GIF — the planet spins exactly once around its axis so the last frame rejoins the first (leave Boomerang off). "tilt" leans the axis toward or away, "light" moves the sun (and the shadow), "zoom" sizes the globe. Distinct from polar_coordinates ("little planet") and fisheye. A filter — run over any background. Good for "sphere", "planet", "globe", "marble", "wrap", "3D ball", "world", or turning a texture into a rotating orb.'
    kind = "filter"

    rotation = Slider(0, 1, default=0, step=0.005)
    tilt = Slider(-0.7, 0.7, default=0.2, step=0.02)
    light = Slider(0, 6.28, default=2.2, step=0.05)
    zoom = Slider(0.5, 0.98, default=0.85, step=0.01)
    seamless = Bool(default=False, label="Seamless (polar)")

    def run(self, canvas):
        W, H = int(canvas.width), int(canvas.height)
        arr = canvas.image_array(mode="RGB", dtype="float")
        lon0 = 2 * math.pi * float(self.rotation)
        tl = float(self.tilt)
        lang = float(self.light)
        globe = float(self.zoom)

        _, _, nx, ny = art_kit.centered_grid(W, H)
        px = nx / globe
        py = ny / globe
        r2 = px * px + py * py
        mask = r2 <= 1.0
        pz = np.sqrt(np.clip(1.0 - r2, 0.0, 1.0))

        # Surface normal in view space (for shading), before spinning the texture.
        nlx, nly, nlz = math.cos(lang) * 0.6, math.sin(lang) * 0.6, 0.55
        ln = math.sqrt(nlx * nlx + nly * nly + nlz * nlz)
        lambert = np.clip((px * nlx + py * nly + pz * nlz) / ln, 0.0, 1.0)
        shade = 0.22 + 0.78 * lambert
        rim = (1.0 - pz) ** 3 * 0.25                       # soft limb brightening

        # Spin + tilt the sphere, then read off longitude / latitude.
        ty = py * math.cos(tl) - pz * math.sin(tl)
        tz = py * math.sin(tl) + pz * math.cos(tl)
        sx3 = px * math.cos(lon0) + tz * math.sin(lon0)
        sz3 = -px * math.sin(lon0) + tz * math.cos(lon0)
        lat = np.arcsin(np.clip(ty, -1.0, 1.0))
        lon = np.arctan2(sx3, sz3)

        u = (lon / (2 * math.pi)) % 1.0
        v = np.clip(lat / math.pi + 0.5, 0.0, 1.0)

        if self.seamless:
            # Read the texture in polar coordinates: longitude -> angle (which is
            # inherently periodic, so the left/right edges meet -> no seam) and
            # latitude -> radius (the content swirls around the poles). Equivalent
            # to Polar Coordinates "to polar" feeding this filter, in one step.
            theta = u * 2.0 * math.pi
            radius = v * (min(W, H) / 2.0)
            sx = (W - 1) / 2.0 + np.cos(theta) * radius
            sy = (H - 1) / 2.0 + np.sin(theta) * radius
            sampled = art_kit.bilinear_sample(arr, sx, sy)
        else:
            # Globe wrap. Longitude wraps; latitude clamps. (art_kit.bilinear_sample
            # only clamps, leaving a hard seam where u wraps 1->0, so sample manually
            # with x-wrap to blend the texture's left and right edges.)
            fx = u * W
            fy = v * (H - 1)
            x0f = np.floor(fx)
            y0f = np.floor(fy)
            wx = (fx - x0f)[..., None]
            wy = (fy - y0f)[..., None]
            x0 = x0f.astype(np.int64) % W
            x1 = (x0 + 1) % W
            y0 = np.clip(y0f.astype(np.int64), 0, H - 1)
            y1 = np.clip(y0 + 1, 0, H - 1)
            top = arr[y0, x0] * (1.0 - wx) + arr[y0, x1] * wx
            bot = arr[y1, x0] * (1.0 - wx) + arr[y1, x1] * wx
            sampled = top * (1.0 - wy) + bot * wy

        # Equirectangular pinches everything near the poles into a thin smear of
        # the texture's top/bottom rows — which goes ugly (often black) for any
        # texture with dark edges. Dissolve the caps into a representative colour
        # taken from the texture's middle band so the poles always read clean.
        lo, hi = int(H * 0.3), int(H * 0.7)
        cap = arr[lo:hi].mean(axis=(0, 1))
        latfrac = np.abs(lat) / (math.pi / 2.0)
        t = np.clip((latfrac - 0.55) / (0.95 - 0.55), 0.0, 1.0)
        capw = (t * t * (3.0 - 2.0 * t))[..., None]        # smoothstep cap weight
        tex = sampled * (1.0 - capw) + cap[None, None, :] * capw

        out = tex * shade[..., None] + rim[..., None]
        bg = np.array(art_kit.hex_to_rgb(canvas.palette.background), dtype=np.float64) / 255.0
        out = np.where(mask[..., None], np.clip(out, 0.0, 1.0), bg[None, None, :])
        canvas.commit_array(out)
