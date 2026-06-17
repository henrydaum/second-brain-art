from plugins.BaseTechnique import BaseTechnique, Slider
from plugins.techniques.technique_3d_menger_sponge import MengerSponge3DTechnique
from plugins.techniques.technique_chladni_plate import ChladniPlateTechnique
from plugins.techniques.technique_conway_life import ConwayLifeTechnique
from plugins.techniques.technique_gray_scott import GrayScottTechnique
from plugins.techniques.technique_hue_shift import HueShiftTechnique
from plugins.techniques.technique_moire_interference import MoireInterferenceTechnique
from plugins.techniques.technique_wave_sea import WaveSeaTechnique


def _controls(cls):
    return {c["name"]: c for c in cls.controls}


def test_slider_loop_metadata_surfaces_in_schema():
    class LoopDemo(BaseTechnique):
        name = "Loop Demo"
        phase = Slider(0, 1, default=0, step=0.01, loop=True)

        def run(self, canvas):
            pass

    assert _controls(LoopDemo)["phase"]["loop"] is True


def test_chunky_sliders_remain_video_selectable_alongside_smooth_companions():
    schema = _controls(MengerSponge3DTechnique)
    assert "depth" in schema
    assert schema["cutout_phase"]["loop"] is True


def test_video_native_time_and_phase_sliders_are_exposed():
    assert _controls(ConwayLifeTechnique)["time"]["loop"] is True
    assert _controls(GrayScottTechnique)["time"]["loop"] is True
    assert _controls(MoireInterferenceTechnique)["phase"]["loop"] is True
    assert _controls(WaveSeaTechnique)["phase"]["loop"] is True


def test_existing_cyclic_sliders_are_finer_loopable_controls():
    assert _controls(HueShiftTechnique)["degrees"]["step"] == 1.0
    assert _controls(HueShiftTechnique)["degrees"]["loop"] is True
    assert _controls(ChladniPlateTechnique)["phase"]["loop"] is True
