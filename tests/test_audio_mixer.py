from unittest.mock import MagicMock, patch

import pytest

from infrastructure.audio_mixer import AudioMixer


def test_mix_concatenates_files(tmp_path):
    scene_paths = [str(tmp_path / "scene_01.mp3"), str(tmp_path / "scene_02.mp3")]
    output_path = str(tmp_path / "final_output.mp3")

    mock_segment = MagicMock()
    # __add__ must return itself so `combined += segment` stays on the same object
    mock_segment.__iadd__ = MagicMock(return_value=mock_segment)
    mock_segment.__add__ = MagicMock(return_value=mock_segment)

    with patch("infrastructure.audio_mixer.AudioSegment") as MockAudio:
        MockAudio.empty.return_value = mock_segment
        MockAudio.from_mp3.return_value = mock_segment

        result = AudioMixer.mix(scene_paths, output_path)

    assert result == output_path
    assert MockAudio.from_mp3.call_count == 2


def test_mix_raises_if_no_scenes(tmp_path):
    with pytest.raises(ValueError, match="至少需要一個場景"):
        AudioMixer.mix([], str(tmp_path / "out.mp3"))


def test_mix_scene_layers_dialogue_only():
    from pydub import AudioSegment

    dialogue = AudioSegment.silent(duration=3000)
    result = AudioMixer.mix_scene_layers(dialogue=dialogue, bgm=None, ambience=None)
    assert len(result) == 3000


def test_mix_scene_layers_with_bgm_only():
    from pydub import AudioSegment

    dialogue = AudioSegment.silent(duration=5000)
    bgm = AudioSegment.silent(duration=2000)  # 需要循環延長
    result = AudioMixer.mix_scene_layers(dialogue=dialogue, bgm=bgm, ambience=None)
    assert len(result) == 5000


def test_mix_scene_layers_with_ambience_only():
    from pydub import AudioSegment

    dialogue = AudioSegment.silent(duration=6000)
    ambience = AudioSegment.silent(duration=2000)
    result = AudioMixer.mix_scene_layers(dialogue=dialogue, bgm=None, ambience=ambience)
    assert len(result) == 6000


def test_mix_scene_layers_with_both_bgm_and_ambience():
    from pydub import AudioSegment

    dialogue = AudioSegment.silent(duration=7000)
    bgm = AudioSegment.silent(duration=3000)
    ambience = AudioSegment.silent(duration=3000)
    result = AudioMixer.mix_scene_layers(dialogue=dialogue, bgm=bgm, ambience=ambience)
    assert len(result) == 7000
