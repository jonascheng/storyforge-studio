import pytest
from pydub import AudioSegment

from infrastructure.ambience_catalog import AmbienceCatalog


def test_list_themes():
    themes = AmbienceCatalog.list_themes()
    assert len(themes) >= 6
    theme_ids = [t.theme_id for t in themes]
    assert "rain" in theme_ids
    assert "wind" in theme_ids
    assert "forest" in theme_ids
    assert "night" in theme_ids
    assert "fireplace" in theme_ids
    assert "room" in theme_ids

    for t in themes:
        assert t.theme_id
        assert t.name
        assert t.description
        assert isinstance(t.keywords, list)


def test_get_theme():
    theme = AmbienceCatalog.get_theme("rain")
    assert theme is not None
    assert theme.theme_id == "rain"
    assert "雨" in theme.name

    assert AmbienceCatalog.get_theme("nonexistent_theme") is None


def test_has_theme():
    assert AmbienceCatalog.has_theme("rain") is True
    assert AmbienceCatalog.has_theme("forest") is True
    assert AmbienceCatalog.has_theme("ghost_sound") is False


def test_get_looped_ambience_invalid_theme():
    with pytest.raises(ValueError, match="找不到環境音主題"):
        AmbienceCatalog.get_looped_ambience("unknown_theme", 5000)


def test_get_looped_ambience_zero_or_negative_duration():
    audio = AmbienceCatalog.get_looped_ambience("rain", 0)
    assert len(audio) == 0
    audio_neg = AmbienceCatalog.get_looped_ambience("rain", -500)
    assert len(audio_neg) == 0


def test_get_looped_ambience_shorter_than_source():
    audio = AmbienceCatalog.get_looped_ambience("rain", 2000)
    assert isinstance(audio, AudioSegment)
    assert len(audio) == 2000


def test_get_looped_ambience_longer_than_source():
    # 測試長時間無縫循環拼接（目標 15 秒）
    audio = AmbienceCatalog.get_looped_ambience("rain", 15000, crossfade_ms=500)
    assert isinstance(audio, AudioSegment)
    assert len(audio) == 15000
