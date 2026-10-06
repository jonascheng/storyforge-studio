import numpy as np
import pytest
from pydub import AudioSegment

from core.entities import FoleyCue
from infrastructure.foley_synthesizer import FoleyDefinition, FoleySynthesizer


def test_foley_cue_entity():
    cue = FoleyCue(sfx_id="step", timestamp_ms=1500, volume=0.8)
    assert cue.sfx_id == "step"
    assert cue.timestamp_ms == 1500
    assert cue.volume == 0.8
    assert cue.to_dict() == {"sfx_id": "step", "timestamp_ms": 1500, "volume": 0.8}


def test_list_and_get_sfx():
    sfx_list = FoleySynthesizer.list_sfx()
    assert len(sfx_list) >= 8

    expected_ids = {
        "creak",
        "step",
        "whoosh",
        "thump",
        "crash",
        "heartbeat",
        "rumble",
        "click",
        "ding",
        "ignite",
    }
    actual_ids = {item.sfx_id for item in sfx_list}
    assert expected_ids.issubset(actual_ids)

    for item in sfx_list:
        assert isinstance(item, FoleyDefinition)
        assert item.name
        assert item.description
        assert item.duration_sec > 0
        assert len(item.keywords) > 0

    step_info = FoleySynthesizer.get_sfx_info("step")
    assert step_info is not None
    assert step_info.sfx_id == "step"
    assert "腳步" in step_info.name

    assert FoleySynthesizer.get_sfx_info("non_existent") is None


def test_synthesize_signal_returns_valid_numpy_array():
    signal, sr = FoleySynthesizer.synthesize_signal("click")
    assert isinstance(signal, np.ndarray)
    assert signal.dtype == np.float32
    assert sr == 48000
    assert len(signal) > 0
    assert -1.0 <= signal.min() <= 1.0
    assert -1.0 <= signal.max() <= 1.0
    assert np.any(signal != 0)


def test_synthesize_returns_valid_audiosegment():
    seg = FoleySynthesizer.synthesize("whoosh")
    assert isinstance(seg, AudioSegment)
    assert len(seg) > 100  # at least 100 ms
    assert seg.sample_width == 2
    assert seg.channels == 1
    assert seg.frame_rate == 48000
    # ensure it's not silent
    assert seg.max > 0


def test_synthesize_all_registered_sfx():
    for item in FoleySynthesizer.list_sfx():
        seg = FoleySynthesizer.synthesize(item.sfx_id)
        assert isinstance(seg, AudioSegment)
        assert len(seg) > 0
        assert seg.max > 0


def test_synthesize_invalid_id_raises():
    with pytest.raises(ValueError, match="找不到動作音效"):
        FoleySynthesizer.synthesize("unknown_sfx_xyz")


def test_synthesize_volume_control():
    seg_full = FoleySynthesizer.synthesize("thump", volume=1.0)
    seg_half = FoleySynthesizer.synthesize("thump", volume=0.5)

    assert seg_full.dBFS > seg_half.dBFS
    # Half volume in linear amplitude is approximately 6 dB lower
    assert pytest.approx(seg_full.dBFS - seg_half.dBFS, abs=1.5) == 6.0


def test_find_by_keyword():
    match = FoleySynthesizer.find_by_keyword("關門")
    assert match is not None
    assert match.sfx_id == "creak"

    match_thunder = FoleySynthesizer.find_by_keyword("打雷")
    assert match_thunder is not None
    assert match_thunder.sfx_id == "rumble"

    match_none = FoleySynthesizer.find_by_keyword("太空梭起飛")
    assert match_none is None
