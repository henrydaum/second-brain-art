import pytest

from plugins.techniques.technique_buddhabrot import BuddhabrotTechnique, _zoom_multiplier as buddhabrot_zoom
from plugins.techniques.technique_burning_ship_explorer import BurningShipExplorerTechnique, _target_center as ship_center, _zoom_multiplier as ship_zoom
from plugins.techniques.technique_julia_explorer import JuliaExplorerTechnique, _zoom_multiplier as julia_zoom
from plugins.techniques.technique_mandelbrot_explorer import MandelbrotExplorerTechnique, _target_center, _zoom_multiplier
from plugins.techniques.technique_newton_basins import NewtonBasinsExplorerTechnique, _zoom_multiplier as newton_zoom


def test_full_set_center_controls_are_complex_coordinates():
    assert _target_center("full", -2.0, 0.0) == (-2.0, 0.0)


def test_landmark_presets_keep_their_known_center():
    assert _target_center("dendrite_tip", -0.5, 0.0) == (-2.0, 0.0)
    assert ship_center("main_ship", -0.5, -0.5) == (-1.762, -0.028)


def test_mandelbrot_center_control_defaults_match_full_view():
    schema = {c["name"]: c for c in MandelbrotExplorerTechnique.controls}
    assert schema["pan"]["label"] == "Center"


@pytest.mark.parametrize("technique", [
    MandelbrotExplorerTechnique,
    BurningShipExplorerTechnique,
    JuliaExplorerTechnique,
    NewtonBasinsExplorerTechnique,
    BuddhabrotTechnique,
])
def test_fractal_pan_controls_are_centers(technique):
    schema = {c["name"]: c for c in technique.controls}
    assert schema["pan"]["label"] == "Center"


@pytest.mark.parametrize("zoom_fn", [_zoom_multiplier, ship_zoom, julia_zoom, newton_zoom, buddhabrot_zoom])
def test_fractal_zoom_controls_move_in_even_doubling_steps(zoom_fn):
    assert zoom_fn(1.0) == 1.0
    assert zoom_fn(2.0) == 2.0
    assert zoom_fn(6.0) == 32.0
