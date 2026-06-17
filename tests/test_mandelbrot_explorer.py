from plugins.techniques.technique_mandelbrot_explorer import MandelbrotExplorerTechnique, _target_center, _zoom_multiplier


def test_full_set_center_controls_are_complex_coordinates():
    assert _target_center("full", -2.0, 0.0) == (-2.0, 0.0)


def test_landmark_presets_keep_their_known_center():
    assert _target_center("dendrite_tip", -0.5, 0.0) == (-2.0, 0.0)


def test_mandelbrot_center_control_defaults_match_full_view():
    schema = {c["name"]: c for c in MandelbrotExplorerTechnique.controls}
    assert schema["pan"]["label"] == "Center"


def test_zoom_control_moves_in_even_doubling_steps():
    assert _zoom_multiplier(1.0) == 1.0
    assert _zoom_multiplier(2.0) == 2.0
    assert _zoom_multiplier(6.0) == 32.0
