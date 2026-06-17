from plugins.BaseTechnique import BaseTechnique, Enum, Palette, Slider, Pan

import numpy as np
from PIL import Image

try:
    art_kit
except NameError:
    art_kit = None

_SPOTS = {
    "full":      (-0.5,      -0.5,      0.0,  220),
    "main_ship": (-1.762,    -0.028,    5.0,  300),
    "antenna":   (-1.625,    -0.0085,   7.5,  400),
    "mini_ship": (-1.7755,   -0.0335,  10.0,  500),
    "mast":      (-1.7395,   -0.000045,11.0,  500),
    "deep_keel": (-1.76225,  -0.03415, 13.0,  600),
}


def _target_center(spot, pan_x, pan_y):
    key = str(spot)
    if key == "full" or key not in _SPOTS:
        return float(pan_x), float(pan_y)
    return _SPOTS[key][0], _SPOTS[key][1]


def _zoom_multiplier(zoom_extra):
    return float(2.0 ** (float(zoom_extra) - 1.0))


class BurningShipExplorerTechnique(BaseTechnique):
    name = 'Burning Ship Explorer'
    description = 'A guided tour of the Burning Ship fractal -- the inferno cousin of the Mandelbrot set. Full Set uses Center as literal complex-plane coordinates; landmark presets supply their own center, zoom, and iteration depth. Optimized: paired-real working set (the |Re|/|Im| step doesn\'t fit numpy complex), live-buffer compaction every 3 iterations.'
    kind = "background"

    palette = Palette()
    spot    = Enum([
        ('full',      'Full Set'),
        ('main_ship', 'Main Ship'),
        ('antenna',   'Antenna'),
        ('mini_ship', 'Embedded Mini-Ship'),
        ('mast',      'Mast Spire'),
        ('deep_keel', 'Deep Keel'),
    ], default='main_ship')
    pan_x = Slider(-2.5, 1.0, default=-0.5, step=0.05)
    pan_y = Slider(-2.0, 1.0, default=-0.5, step=0.05)
    pan = Pan(x='pan_x', y='pan_y', label='Center')
    zoom_extra = Slider(0.0, 20.0, default=1.0, step=1, label='Zoom')
    iterations = Slider(0, 3000, default=1500, step=10, label='Iterations')

    def run(self, canvas):
        _, _, zoom_exp, detail = _SPOTS.get(str(self.spot), _SPOTS["main_ship"])
        cx_eff, cy_eff = _target_center(self.spot, self.pan_x, self.pan_y)
        W, H = int(canvas.width), int(canvas.height)
        zoom = float(2.0 ** zoom_exp) * _zoom_multiplier(self.zoom_extra)
        iter_override = int(self.iterations)
        n_iter = iter_override if iter_override >= 50 else int(detail)

        # Step up to f64 once total zoom passes ~2^10, regardless of whether
        # the extra zoom came from the preset or the user slider.
        use_f64 = zoom > 1024.0
        real = np.float64 if use_f64 else np.float32

        view = 3.0 / zoom
        half = view * 0.5
        # Render natively at the canvas aspect: long edge spans the full
        # half-view, short edge proportionally less, so pixels stay square and
        # the ship is framed on center instead of cropped from a square.
        long_edge = max(W, H)
        half_x = half * W / long_edge
        half_y = half * H / long_edge
        re = np.linspace(cx_eff - half_x, cx_eff + half_x, W, dtype=real)
        # im linspace is reversed so the ship silhouette reads right-side up.
        im = np.linspace(cy_eff + half_y, cy_eff - half_y, H, dtype=real)
        R, I = np.meshgrid(re, im)  # both (H, W)

        N = W * H
        out_flat = np.zeros(N, dtype=np.float64)
        inside_flat = np.zeros(N, dtype=bool)

        zr = np.zeros(N, dtype=real)
        zi = np.zeros(N, dtype=real)
        cr = R.ravel().copy()
        ci = I.ravel().copy()

        live_idx = np.arange(N)
        bailout2 = real(16 * 16) if not use_f64 else real(1 << 16)
        inv_log2 = 1.0 / np.log(2.0)
        compact_every = 3

        with np.errstate(over="ignore", invalid="ignore"):
            for i in range(n_iter):
                azr = np.abs(zr)
                azi = np.abs(zi)
                zr_new = azr * azr - azi * azi + cr
                zi_new = 2.0 * azr * azi + ci
                zr = zr_new
                zi = zi_new
                if (i + 1) % compact_every == 0 or i == n_iter - 1:
                    absZ2 = zr * zr + zi * zi
                    esc = absZ2 > bailout2
                    if esc.any():
                        log_mod = 0.5 * np.log(absZ2[esc].astype(np.float64))
                        nu = np.log(log_mod * inv_log2) * inv_log2
                        out_flat[live_idx[esc]] = (i + 1) - nu
                        keep = ~esc
                        live_idx = live_idx[keep]
                        zr = zr[keep]
                        zi = zi[keep]
                        cr = cr[keep]
                        ci = ci[keep]
                        if live_idx.size == 0:
                            break

        inside_flat[live_idx] = True

        valid = ~inside_flat
        t = np.zeros_like(out_flat)
        if valid.any():
            v = np.log(out_flat[valid] + 1.0)
            vmin = float(v.min())
            vmax = float(v.max())
            if vmax - vmin > 1e-9:
                v = (v - vmin) / (vmax - vmin)
            else:
                v = np.zeros_like(v)
            t[valid] = v

        LUT_SIZE = 512
        lut = np.array(
            [art_kit.hex_to_rgb(art_kit.palette_color(k / (LUT_SIZE - 1))) for k in range(LUT_SIZE)],
            dtype=np.uint8,
        )
        idx_lut = np.clip((t * (LUT_SIZE - 1)).astype(np.int32), 0, LUT_SIZE - 1)
        rgb = lut[idx_lut].reshape(H, W, 3)

        bg = np.array(art_kit.hex_to_rgb(canvas.palette.background), dtype=np.uint8)
        rgb[inside_flat.reshape(H, W)] = bg

        canvas.commit(Image.fromarray(rgb, "RGB").convert("RGBA"))
