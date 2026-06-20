## Generative art encyclopedia

This is a math/philosophy reference for established generative methods —
fractals, L-systems, attractors, noise, tilings, and the rest. Each entry:
the bare formula, a minimal Python snippet showing the math, and the
trade-off that decides when to reach for it.

The implementation contract (sandbox rules, the `canvas` surface, every
`art_kit` helper) lives in `templates/technique_template.py`. Read it via
`read_technique_guide` before authoring — this file assumes you already know
the contract and just need the math.

Do not copy snippets verbatim. Adapt for palette, composition, and the
canvas dimensions you're rendering into. The canvas is **not always square** — build grids and place focal points from `canvas.width`/`canvas.height` (and
center on `(width/2, height/2)`), not a single side length. Snippets here that take a scalar `size` assume a square; generalize them to width×height when the canvas aspect isn't 1:1. Every color in the final technique must trace back to a palette slot or `art_kit.palette_color(t)`.

### §1 Fractals

**Mandelbrot** — escape-time for `z² + c` over the complex plane.
```python
import numpy as np
def mandelbrot(size, cx=-0.5, cy=0.0, zoom=1.0, max_iter=200):
    s = 3.0 / zoom
    x = np.linspace(cx - s/2, cx + s/2, size)
    y = np.linspace(cy - s/2, cy + s/2, size)
    C = x[None, :] + 1j * y[:, None]
    Z = np.zeros_like(C); out = np.zeros(C.shape, dtype=np.float32)
    for i in range(max_iter):
        m = np.abs(Z) < 2.0
        Z[m] = Z[m]*Z[m] + C[m]
        out[m] = i + 1
    # Smooth: out = out + 1 - log(log(|Z|))/log(2)  (clamp to handle |Z|<=1)
    return out / max_iter   # t∈[0,1]; map via art_kit.palette_color
```

**Julia** — same iteration, parameter `c` is fixed; sample `Z₀` from the plane.
**Burning Ship** — `z = (|Re(z)| + i|Im(z)|)² + c`.
**Newton** — `z = z - f(z)/f'(z)`; for `f(z) = z³-1` the three roots split
the plane into three basins. Color by basin index + iteration count.

Always render with numpy meshgrid + boolean masks. Never iterate per-pixel
in Python.

### §2 L-systems

```python
def expand(axiom, rules, depth):
    s = axiom
    for _ in range(depth):
        s = "".join(rules.get(c, c) for c in s)
    return s

# Classic systems:
# Koch snowflake:  axiom="F--F--F", rules={"F":"F+F--F+F"}, angle=60°
# Dragon curve:    axiom="FX",     rules={"X":"X+YF+","Y":"-FX-Y"}, angle=90°
# Sierpinski:      axiom="F-G-G",  rules={"F":"F-G+F+G-F","G":"GG"}, angle=120°
# Plant:           axiom="X", rules={"X":"F+[[X]-X]-F[-FX]+X","F":"FF"}, angle=25°
# Fractal tree:    axiom="F", rules={"F":"FF+[+F-F-F]-[-F+F+F]"}, angle=22.5°
```

Turtle interpreter: `F` forward+draw, `f` forward+nodraw, `+`/`-` turn,
`[`/`]` push/pop. Depth 6–9 is the sweet spot; depth 10+ explodes string
length. Narrow stroke width toward leaves; shift palette ramp toward
`accent` near the tips. The `art_kit.lindenmayer(axiom, rules, depth)`
and `art_kit.turtle_segments(string, start, angle, step, angle_deg)`
helpers do this for you.

### §3 Cellular automata

**Elementary CA** — 1D, 2-state, 3-cell neighborhood. Rule N's bit `i`
gives the next state for neighborhood `i`. Famous: 30 (chaos), 90
(Sierpinski), 110 (Turing-complete).
```python
import numpy as np
def elementary(rule, size, steps):
    grid = np.zeros((steps, size), dtype=np.uint8)
    grid[0, size//2] = 1
    bits = np.array([(rule >> i) & 1 for i in range(8)], dtype=np.uint8)
    for t in range(1, steps):
        row = grid[t-1]
        n = (np.roll(row, 1) << 2) | (row << 1) | np.roll(row, -1)
        grid[t] = bits[n]
    return grid
```

**Conway's Life** — 2D, B3/S23. Use a 3×3 convolution to count neighbors:
```python
from scipy.signal import convolve2d  # NOT AVAILABLE — use numpy roll
def life_step(g):
    n = sum(np.roll(np.roll(g, dx, 0), dy, 1)
            for dx in (-1,0,1) for dy in (-1,0,1) if (dx or dy))
    return ((n == 3) | ((g == 1) & (n == 2))).astype(np.uint8)
```

**Gray-Scott reaction-diffusion** — two-species PDE; produces spots,
stripes, mazes depending on `f` and `k`.
```
A' = A + (Du·∇²A - A·B² + f·(1-A)) · dt
B' = B + (Dv·∇²B + A·B² - (k+f)·B) · dt
```
Coarse grid (≤256) and ≤200 steps to fit the 30s budget.

### §4 Strange attractors

Iterate a map for ~200k steps, accumulate into a 2D density buffer, color
by `log(1 + density)` and map via the palette ramp.

- **Lorenz**: `dx=σ(y-x), dy=x(ρ-z)-y, dz=xy-βz`. σ=10, ρ=28, β=8/3.
  Project (x,y) or (x,z) into 2D.
- **Rössler**: `dx=-y-z, dy=x+ay, dz=b+z(x-c)`. a=b=0.1, c=14.
- **De Jong**: `x' = sin(a·y) - cos(b·x); y' = sin(c·x) - cos(d·y)`.
- **Clifford**: `x' = sin(a·y) + c·cos(a·x); y' = sin(b·x) + d·cos(b·y)`.
- **Pickover**: `x' = sin(a·y) - z·cos(b·x); y' = z·sin(c·x) - cos(d·y);
  z' = sin(x)`.

```python
import numpy as np
def clifford(n, a, b, c, d, seed):
    rng = np.random.default_rng(seed)
    xs = np.empty(n); ys = np.empty(n); x = y = 0.1
    for i in range(n):
        x, y = np.sin(a*y) + c*np.cos(a*x), np.sin(b*x) + d*np.cos(b*y)
        xs[i] = x; ys[i] = y
    return xs, ys

# Density buffer:
H, _, _ = np.histogram2d(ys, xs, bins=size, range=[[-2.5,2.5],[-2.5,2.5]])
H = np.log1p(H); H = H / max(H.max(), 1e-9)   # t∈[0,1]
```

### §5 Noise & flow fields

**Value noise** — interpolate random values at integer lattice points
with smoothstep. **Perlin noise** — gradient noise; smoother high
frequencies. **Worley/Voronoi noise** — distance to the nearest of N
random seeds.

**Fractional Brownian motion (fbm)** — sum of octaves:
```
fbm(x,y) = Σ_{i=0..N-1} gain^i · noise(x · lacunarity^i, y · lacunarity^i)
```
Typical: 4–6 octaves, lacunarity=2.0, gain=0.5. Use `art_kit.fbm(seed, x, y, octaves)` — it's deterministic in `seed`.

**Flow field** — sample an angle from fbm, step particles along it:
```python
angle = art_kit.fbm(canvas.seed, x*0.003, y*0.003, octaves=4) * 2 * math.pi
x += math.cos(angle) * step
y += math.sin(angle) * step
```
Draw short segments per particle; tens of thousands of particles each
walked for ~100 steps fills the canvas.

### §6 Tilings & subdivision

**Voronoi assignment**: generate N seed points via `art_kit.jittered_grid(rng, cols, rows)`; for each pixel, assign the nearest seed; fill the cell with `palette_color(i / N)`.

```python
seeds = np.array(art_kit.jittered_grid(rng, 12, 12))   # (N, 2) in [0,1]²
ys, xs = np.mgrid[0:size, 0:size] / size
d2 = ((xs[..., None] - seeds[:, 0])**2 + (ys[..., None] - seeds[:, 1])**2)
cell = d2.argmin(axis=-1)                              # (size, size)
```

**Recursive rectangular subdivision** (Mondrian / low-poly):
```python
def split(rect, depth, rng):
    if depth == 0 or rng.random() < 0.15: yield rect; return
    x, y, w, h = rect
    if w >= h:
        t = rng.uniform(0.3, 0.7); cut = int(w * t)
        yield from split((x, y, cut, h), depth-1, rng)
        yield from split((x+cut, y, w-cut, h), depth-1, rng)
    else:
        t = rng.uniform(0.3, 0.7); cut = int(h * t)
        yield from split((x, y, w, cut), depth-1, rng)
        yield from split((x, y+cut, w, h-cut), depth-1, rng)
```

**Hex grid** — column-offset coordinates: `x = c·1.5·r`,
`y = (r + (c%2)·0.5)·√3·radius`.

### §7 Wave & interference

```
field(x,y) = Σ_i A_i · sin(k_i · (x·cos(θ_i) + y·sin(θ_i)) + φ_i)
```
Sum a handful (3–8) of plane waves with random `θ` and `φ`, normalize the
field to [0,1], color by palette ramp. Two close frequencies produce
moiré beats; same wave family in radial form (`k·r`) gives concentric
ripples.

### §8 Composition primitives

- **Vogel golden-angle spiral**: `θ = i · 137.50776°`, `r = sqrt(i/N)`.
  `art_kit.vogel_spiral(n)` returns n unit-disc points. Sunflowers, star
  fields, packed-disc anything.
- **Rule of thirds**: `art_kit.rule_of_thirds(size).points` → the four
  intersections. Place a focal subject on one; place horizons on a
  `.horizons` line, not center.
- **Jittered grid**: `art_kit.jittered_grid(rng, cols, rows)` cell-centered
  points with jitter in [0,1]². Used for Voronoi seeds, skyline columns,
  procedural forests.
- **Radial falloff**: `art_kit.radial_falloff(w, h)` closure returns 1 at
  center, 0 at corners. Suns, vignettes, glow masks.

Leave 30–50% of the canvas as `palette.background`. Density without focus
reads as noise.

### §9 Pseudo-3D without a 3D engine

There is no GL, no real depth buffer. Fake it in 2D:

- **Isometric projection**: `screen_x = (x - y) · cos(30°)`,
  `screen_y = (x + y) · sin(30°) - z`. Voxels as flat-shaded rhombi sorted
  back-to-front. Three palette shades for top/left/right faces.
- **2D raymarching** of implicit surfaces: for each pixel, step along a
  ray; signed-distance function gives the next step size. Output:
  distance map → palette ramp. Coarse pixel grid (≤512) for speed.
- **Depth fog**: blend each draw with `palette.background` by a depth
  weight; works for landscapes and crowd scenes.
- **Atmospheric perspective**: shift hue toward background palette slot
  as `y` (height) decreases or `z` (depth) increases.

### §10 How to make GIFs

Second Brain Art has the ability to make GIFs. GIFs can only be made using techniques that have slider controls. Each frame of a GIF is made with a slightly different slider value. The slider value is swept from start to finish. Once all of the frames are rendered, they are collected in order and turned into the final animation. Rendering GIFs can take a while, since there are so many frames. 

You cannot make GIFs. If the user asks to make a GIF, here is what you should say to them: "To make a GIF, open the control panel and find the magenta play buttons on the right. If you do not see one, it means that you do not have any layers that can render GIFs. When you have one or more of these buttons toggled, you can tap on the 'GIF' button to make one."

GIFs are best when the slider controls are smooth seamless, meaning they can be iterated with no jitters and they end how they start, making a perfect loop.

Even if GIFs don't end how they start, the 'Boomerang' setting in the GIF popup is an option to make any GIF a perfect loop.
