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


def test_apply_ducking_empty_cues_returns_original():
    from pydub import AudioSegment

    audio = AudioSegment.silent(duration=2000)
    result = AudioMixer.apply_ducking(audio, cues=[])
    assert len(result) == len(audio)
    assert result == audio


def test_apply_ducking_attenuates_volume():
    import numpy as np
    from pydub import AudioSegment

    from core.entities import FoleyCue

    # 建立 3 秒、取樣率 48000 Hz、振幅恆定的 440 Hz 單聲道正弦波
    sr = 48000
    t = np.linspace(0, 3.0, sr * 3, endpoint=False)
    sine = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
    audio = AudioSegment(sine.tobytes(), frame_rate=sr, sample_width=2, channels=1)

    # 在 1000 ms ~ 1500 ms 期間讓路 10 dB
    cue = FoleyCue(sfx_id="thump", timestamp_ms=1000)
    ducked = AudioMixer.apply_ducking(audio, cues=[cue], duck_db=10.0, default_duration_ms=500)

    assert len(ducked) == len(audio)

    # 觀察未讓路區間 (300ms ~ 700ms) 與讓路核心區間 (1100ms ~ 1400ms)
    unducked_slice = ducked[300:700]
    ducked_slice = ducked[1100:1400]

    diff_db = unducked_slice.dBFS - ducked_slice.dBFS
    # 衰減應接近 10 dB (容許平滑過渡誤差 ±1.5 dB)
    assert pytest.approx(diff_db, abs=1.5) == 10.0


def test_apply_ducking_stereo():
    import numpy as np
    from pydub import AudioSegment

    sr = 48000
    t = np.linspace(0, 2.0, sr * 2, endpoint=False)
    # 立體聲 (2 聲道)
    s1 = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
    s2 = (np.sin(2 * np.pi * 880 * t) * 16000).astype(np.int16)
    stereo = np.column_stack([s1, s2]).reshape(-1)
    audio = AudioSegment(stereo.tobytes(), frame_rate=sr, sample_width=2, channels=2)

    ducked = AudioMixer.apply_ducking(audio, cues=[(500, 400)], duck_db=8.0)
    assert len(ducked) == 2000
    assert ducked.channels == 2
    assert ducked[600:800].dBFS < ducked[100:300].dBFS


def test_mix_scene_layers_with_foley_and_ducking():
    import numpy as np
    from pydub import AudioSegment

    from core.entities import FoleyCue
    from infrastructure.foley_synthesizer import FoleySynthesizer

    sr = 48000
    t = np.linspace(0, 4.0, sr * 4, endpoint=False)
    sine = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
    bgm = AudioSegment(sine.tobytes(), frame_rate=sr, sample_width=2, channels=1)
    dialogue = AudioSegment.silent(duration=4000)

    cue = FoleyCue(sfx_id="rumble", timestamp_ms=1000)
    foley_seg = FoleySynthesizer.synthesize("rumble")

    mixed = AudioMixer.mix_scene_layers(
        dialogue=dialogue,
        bgm=bgm,
        ambience=None,
        foley_track=foley_seg,
        foley_cues=[cue],
        duck_db=8.0,
    )

    assert len(mixed) == 4000
    assert mixed.max > 0
