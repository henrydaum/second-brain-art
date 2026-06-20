// Suggested prompts shown as chips on the first tutorial step. Edit freely —
// the tutorial randomly picks three from this pool each time it's built.
// Each entry: { prompt: <sent to the chat>, label: <shown on the chip> }.
const PROMPT_SUGGESTIONS = [
  // Iconic single-technique showcases — technique-name labels
  { prompt: "Show me the Mandelbrot Explorer.", label: "Mandelbrot set" },
  { prompt: "Show me the Newton Basins Explorer with five roots and a Fisheye lens filter. Also, make it coral-colored.", label: "Newton Basins" },
  { prompt: "Show me a Lorenz Attractor zoomed out, with the Synthwave palette.", label: "Lorenz Attractor" },
  { prompt: "Run Conway's Life with the Aurora palette and add Bloom Glow and Scanlines.", label: "Conway's Life" },
  { prompt: "Show me Isometric Terrain with the Tower Village scene and Botanical palette. After that, add a border.", label: "Isometric terrain" },
  { prompt: "Show me an Elementary Cellular Automaton with the Obsidian palette, with rule 90 (Sierpinski triangle). Then, Mirror it top to bottom and add an Anaglyph 3D filter.", label: "Cellular automaton" },
  { prompt: "Show me an Attractor Cloud using the Clifford attractor with the Aurora palette.", label: "Attractor cloud" },
  { prompt: "Show me the Buddhabrot with Bloom Glow and a white Border.", label: "Buddhabrot" },

  // Background + object combos
  { prompt: "Add a Color Field background with a 3D Menger Sponge on top, and increase the depth to 3.", label: "3D Menger Sponge" },

  // Filter-heavy showcases — evocative labels
  { prompt: "Load the Julia Explorer and give it the Ink & Paper palette. Then invert the colors with the Invert filter. Finally, add the Glitch Slice and Kaleidoscope filters.", label: "Oriental rug pattern" },
  { prompt: "Add the Wave Sea background, then change the palette to Synthwave. After that, add the Pixel Sort and Dot Screen filters.", label: "80s synthwave" },
  { prompt: "Show me the Julia Explorer at the Dendrite location, then add the Fisheye lens and Chromatic Aberration filters.", label: "Mythical fractal orb" },
  { prompt: "Show me the Terdragon variant of the Dragon Curve with the Anaglyph 3D filter.", label: "Trippy dragon curve" },
  { prompt: "Show me the L-System Grove with the Coral palette and a touch of Film Grain.", label: "Stylish artificial plant" },
  { prompt: "Show me the Julia Explorer at the Spiral location, and zoom in slightly.", label: "Julia spiral" },
  { prompt: "Show me Wave Sea with Posterize To Palette using the Coral Reef palette and a Vignette.", label: "Background material" },
  { prompt: "Show me the Mandelbrot Explorer at Elephant Valley. Add a border as well.", label: "Mandelbrot elephants" },
  { prompt: "Show me a Gray-Scott reaction-diffusion, then apply polar coordinates.", label: "Reaction-diffusion blob" },
  { prompt: "Show me a Gray-Scott reaction-diffusion, then apply polar coordinates, and change it to 'From Polar' mode.", label: "Inverted reaction-diffusion" },
  { prompt: "Show me the Burning Ship Explorer at the Embedded Mini-Ship with the Magma palette and a Vignette. Crank the zoom.", label: "Burning Ship fractal" },
  { prompt: "Show me a Barnsley Fern with the Neutral Mono palette.", label: "Silver fern" },

  // GIF material
  { prompt: "Show me the Color Field background with the Tesseract technique, then put the CRT filter on it. Explain how to make a GIF using the Rot Zw slider.", label: "Tesseract" },
  { prompt: "Apply the 'Op Art' background, then add Sphere Wrap to make it look like a planet.", label: "Striped Planet" },
  { prompt: "Apply the 'Marble' background, then put the Oil Slick filter on it. Explain how to use the 'thickness' slider control to make a seamless GIF.", label: "Iridescence" },
  { prompt: "Apply the 'Quasicrystal' background, and make the settings a bit better. Then add Posterize to Palette. Explain how to use the 'phase' slider to make a seamless GIF.", label: "Sun Flow" },
  { prompt: "Do the Inverted Julia background, then add Chromatic Aberration and the Fisheye lens. Change to Neutral Mono palette. Explain how to make a GIF using the Fisheye and Aberration 'Strength' sliders to make a seamless GIF with the boomerang effect.", label: "Sun Flow" },
];
