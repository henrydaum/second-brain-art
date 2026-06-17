from plugins.techniques.technique_mandelbrot_explorer import MandelbrotExplorerTechnique, _target_center


def test_full_set_center_controls_are_complex_coordinates():
    assert _target_center("full", -2.0, 0.0) == (-2.0, 0.0)


def test_landmark_presets_keep_their_known_center():
    assert _target_center("dendrite_tip", -0.5, 0.0) == (-2.0, 0.0)


def test_mandelbrot_center_control_defaults_match_full_view():
    schema = {c["name"]: c for c in MandelbrotExplorerTechnique.controls}
    assert schema["pan"]["label"] == "Center"
    assert schema["pan"]["x_default"] == -0.5
