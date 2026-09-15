import json
from unittest.mock import MagicMock, patch

import pytest

from core.entities import Scene, ScriptLine
from infrastructure.gemini_director import GeminiDirector

FAKE_SCREENPLAY_JSON = json.dumps(
    [
        {
            "scene_id": 1,
            "title": "開場",
            "lines": [
                {
                    "role": "旁白",
                    "emotion": "平靜",
                    "text": "從前從前...",
                    "voice_direction_note": "[calm, slow]",
                },
                {
                    "role": "小明",
                    "emotion": "開心",
                    "text": "你好！",
                    "voice_direction_note": "[cheerful]",
                },
            ],
        },
        {
            "scene_id": 2,
            "title": "衝突",
            "lines": [
                {
                    "role": "旁白",
                    "emotion": "緊張",
                    "text": "突然...",
                    "voice_direction_note": "[tense]",
                }
            ],
        },
    ]
)


def test_break_down_screenplay_parses_json():
    director = GeminiDirector(api_key="fake-key")
    with patch.object(director, "_call_director_model", return_value=FAKE_SCREENPLAY_JSON):
        screenplay = director.break_down_screenplay("隨便一個故事")
    assert len(screenplay.scenes) == 2
    assert screenplay.scenes[0].title == "開場"
    assert screenplay.scenes[1].title == "衝突"
    assert screenplay.scenes[0].lines[1].voice_direction_note == "[cheerful]"


def test_break_down_screenplay_strips_markdown_fences():
    director = GeminiDirector(api_key="fake-key")
    fenced = f"```json\n{FAKE_SCREENPLAY_JSON}\n```"
    with patch.object(director, "_call_director_model", return_value=fenced):
        screenplay = director.break_down_screenplay("故事")
    assert len(screenplay.scenes) == 2
    # 向後相容舊陣列回傳：自動依角色補齊 voice_map
    assert "旁白" in screenplay.voice_map
    assert "小明" in screenplay.voice_map
    assert screenplay.voice_map["旁白"] == "Kore"


def test_break_down_screenplay_parses_dict_with_voice_map():
    director = GeminiDirector(api_key="fake-key")
    response_payload = json.dumps(
        {
            "voice_map": {"小明": "Puck", "怪獸": "Algenib", "旁白": "Kore"},
            "scenes": [
                {
                    "scene_id": 1,
                    "title": "遭遇怪獸",
                    "lines": [
                        {
                            "role": "旁白",
                            "emotion": "緊張",
                            "text": "大霧散去...",
                            "voice_direction_note": "[tense]",
                        },
                        {
                            "role": "小明",
                            "emotion": "害怕",
                            "text": "快跑！",
                            "voice_direction_note": "[fearful]",
                        },
                        {
                            "role": "怪獸",
                            "emotion": "怒吼",
                            "text": "吼！",
                            "voice_direction_note": "[roaring]",
                        },
                    ],
                }
            ],
        }
    )
    with patch.object(director, "_call_director_model", return_value=response_payload):
        screenplay = director.break_down_screenplay("故事")
    assert len(screenplay.scenes) == 1
    assert screenplay.voice_map["旁白"] == "Kore"
    assert screenplay.voice_map["小明"] == "Puck"
    assert screenplay.voice_map["怪獸"] == "Algenib"


def test_break_down_screenplay_raises_on_bad_json():
    director = GeminiDirector(api_key="fake-key")
    with patch.object(director, "_call_director_model", return_value="not json at all"):
        with pytest.raises(ValueError, match="AI 導演回傳的格式有誤"):
            director.break_down_screenplay("故事")


def test_requires_api_key():
    director = GeminiDirector(api_key="")
    with pytest.raises(ValueError, match="API 通行證"):
        director.break_down_screenplay("故事")


def test_generate_content_retries_on_429_and_succeeds():
    from google.genai.errors import ClientError

    director = GeminiDirector(api_key="fake-key")
    mock_response = MagicMock()
    mock_response.text = "成功"

    err_429 = ClientError(
        429,
        {
            "error": {
                "code": 429,
                "message": "Quota exceeded. Please retry in 5s.",
                "status": "RESOURCE_EXHAUSTED",
                "details": [
                    {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "5s"}
                ],
            }
        },
    )
    mock_gen = MagicMock(side_effect=[err_429, mock_response])
    director._client.models.generate_content = mock_gen

    with patch("time.sleep") as mock_sleep:
        res = director._generate_content_with_retry(model="any", contents="test")
        assert res == mock_response
        assert mock_gen.call_count == 2
        assert mock_sleep.call_count == 1
        assert mock_sleep.call_args[0][0] >= 5.0


def test_generate_content_fails_after_max_retries():
    from google.genai.errors import ClientError

    director = GeminiDirector(api_key="fake-key")
    err_429 = ClientError(
        429,
        {
            "error": {
                "code": 429,
                "message": "Quota exceeded. Please retry in 2s.",
                "status": "RESOURCE_EXHAUSTED",
            }
        },
    )
    mock_gen = MagicMock(side_effect=err_429)
    director._client.models.generate_content = mock_gen

    with patch("time.sleep"):
        with pytest.raises(RuntimeError, match="額度已達每分鐘上限"):
            director._generate_content_with_retry(model="any", contents="test", max_retries=2)


def test_generate_content_does_not_retry_non_429():
    director = GeminiDirector(api_key="fake-key")
    mock_gen = MagicMock(side_effect=ValueError("其他錯誤"))
    director._client.models.generate_content = mock_gen

    with patch("time.sleep") as mock_sleep:
        with pytest.raises(ValueError, match="其他錯誤"):
            director._generate_content_with_retry(model="any", contents="test")
        assert mock_sleep.call_count == 0
        assert mock_gen.call_count == 1


def test_generate_content_aborts_immediately_when_delay_exceeds_threshold():
    from google.genai.errors import ClientError

    director = GeminiDirector(api_key="fake-key")
    err_429 = ClientError(
        429,
        {
            "error": {
                "code": 429,
                "message": "Quota exceeded. Please retry in 78667s.",
                "status": "RESOURCE_EXHAUSTED",
                "details": [
                    {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "78667s"}
                ],
            }
        },
    )
    mock_gen = MagicMock(side_effect=err_429)
    director._client.models.generate_content = mock_gen

    with patch("time.sleep") as mock_sleep:
        with pytest.raises(RuntimeError, match="今日額度已達上限"):
            director._generate_content_with_retry(model="any", contents="test", max_delay=60.0)
        assert mock_sleep.call_count == 0
        assert mock_gen.call_count == 1


def test_group_lines_into_dialogue_groups_alternating_two_speakers():
    director = GeminiDirector(api_key="fake-key")
    lines = [
        ScriptLine(role="小明", emotion="開心", text="嗨！", voice_direction_note="[cheerful]"),
        ScriptLine(role="小美", emotion="溫柔", text="你好呀！", voice_direction_note="[gentle]"),
        ScriptLine(
            role="小明", emotion="好奇", text="今天要去哪？", voice_direction_note="[curious]"
        ),
        ScriptLine(
            role="小美", emotion="興奮", text="去森林冒險！", voice_direction_note="[excited]"
        ),
    ]
    groups = director._group_lines_into_dialogue_groups(lines)
    assert len(groups) == 1
    assert len(groups[0]) == 4


def test_group_lines_into_dialogue_groups_max_lines_limit():
    director = GeminiDirector(api_key="fake-key")
    lines = [
        ScriptLine(role="A", emotion="", text=f"台詞 {i}", voice_direction_note="")
        for i in range(8)
    ]
    # alternating A and B
    for i, line in enumerate(lines):
        line.role = "A" if i % 2 == 0 else "B"

    groups = director._group_lines_into_dialogue_groups(lines)
    assert len(groups) == 2
    assert len(groups[0]) == 6
    assert len(groups[1]) == 2


def test_group_lines_into_dialogue_groups_three_speakers():
    director = GeminiDirector(api_key="fake-key")
    lines = [
        ScriptLine(role="小明", emotion="", text="你看那邊！", voice_direction_note=""),
        ScriptLine(role="小美", emotion="", text="那是貓咪耶！", voice_direction_note=""),
        ScriptLine(role="小明", emotion="", text="好想摸牠。", voice_direction_note=""),
        ScriptLine(role="媽媽", emotion="", text="不行，要先洗手。", voice_direction_note=""),
        ScriptLine(role="小明", emotion="", text="好啦...", voice_direction_note=""),
    ]
    groups = director._group_lines_into_dialogue_groups(lines)
    assert len(groups) == 2
    # Group 1: 小明, 小美
    assert [line.role for line in groups[0]] == ["小明", "小美", "小明"]
    # Group 2: 媽媽, 小明
    assert [line.role for line in groups[1]] == ["媽媽", "小明"]


def test_group_lines_into_dialogue_groups_character_length_limit():
    director = GeminiDirector(api_key="fake-key")
    long_text = "這是一段很長很長的話，說了好多好多細節。" * 6  # ~144 chars
    lines = [
        ScriptLine(role="A", emotion="", text=long_text, voice_direction_note=""),
        ScriptLine(role="B", emotion="", text=long_text, voice_direction_note=""),
        ScriptLine(role="A", emotion="", text=long_text, voice_direction_note=""),
    ]
    groups = director._group_lines_into_dialogue_groups(lines)
    # 144 + 144 = 288 (<300). 3rd line would make 432 (>300), so cut into new group.
    assert len(groups) == 2
    assert len(groups[0]) == 2
    assert len(groups[1]) == 1


def test_group_lines_into_dialogue_groups_isolates_narration():
    director = GeminiDirector(api_key="fake-key")
    lines = [
        ScriptLine(role="旁白", emotion="", text="森林裡很安靜。", voice_direction_note=""),
        ScriptLine(role="小明", emotion="", text="快看！", voice_direction_note=""),
        ScriptLine(role="爸爸", emotion="", text="慢慢走。", voice_direction_note=""),
        ScriptLine(role="小明", emotion="", text="好！", voice_direction_note=""),
        ScriptLine(role="旁白", emotion="", text="天色漸漸暗了。", voice_direction_note=""),
    ]
    groups = director._group_lines_into_dialogue_groups(lines)
    assert len(groups) == 3
    # Group 1: 旁白
    assert len(groups[0]) == 1
    assert groups[0][0].role == "旁白"
    # Group 2: 小明 and 爸爸
    assert len(groups[1]) == 3
    assert [line.role for line in groups[1]] == ["小明", "爸爸", "小明"]
    # Group 3: 旁白
    assert len(groups[2]) == 1
    assert groups[2][0].role == "旁白"


def test_build_multi_speaker_prompt():
    director = GeminiDirector(api_key="fake-key")
    scene = Scene(scene_id=1, title="神秘森林", lines=[])
    group = [
        ScriptLine(role="爸爸", emotion="沉穩", text="快看！", voice_direction_note="[excited]"),
        ScriptLine(
            role="小美", emotion="害怕", text="那是怪獸嗎？", voice_direction_note="[trembling]"
        ),
    ]
    roles = ["爸爸", "小美"]
    prompt = director._build_multi_speaker_prompt(scene, group, roles)

    assert "神秘森林" in prompt
    assert "Characters:" in prompt
    assert "爸爸" in prompt
    assert "小美" in prompt
    assert "Adult male father" in prompt
    assert "快看！" in prompt
    assert "那是怪獸嗎？" in prompt


def test_generate_scene_audio_calls_multi_speaker_and_exports():
    from pydub import AudioSegment

    director = GeminiDirector(api_key="fake-key")
    scene = Scene(
        scene_id=1,
        title="對話場景",
        lines=[
            ScriptLine(role="小明", emotion="開心", text="嗨！", voice_direction_note=""),
            ScriptLine(role="小美", emotion="溫柔", text="你好！", voice_direction_note=""),
        ],
    )
    voice_map = {"小明": "Kore", "小美": "Puck"}

    # Mock audio response
    mock_resp = MagicMock()
    mock_part = MagicMock()
    # 1000 samples of 16-bit PCM = 2000 bytes
    mock_part.inline_data.data = b"\x00\x00" * 1000
    mock_part.inline_data.mime_type = "audio/pcm;rate=24000"
    mock_resp.candidates = [MagicMock(content=MagicMock(parts=[mock_part]))]

    with (
        patch.object(director, "_generate_content_with_retry", return_value=mock_resp) as mock_gen,
        patch.object(AudioSegment, "export") as mock_export,
    ):
        out = director.generate_scene_audio(scene, voice_map, "/tmp/test_scene.mp3")

        assert out == "/tmp/test_scene.mp3"
        assert mock_gen.call_count == 1  # 2 lines in 1 multi-speaker call!
        # Verify speech config in call
        config_used = mock_gen.call_args[1]["config"]
        assert config_used.speech_config.multi_speaker_voice_config is not None
        mock_export.assert_called_once_with("/tmp/test_scene.mp3", format="mp3")


def test_generate_scene_audio_falls_back_to_single_speaker_on_failure():
    from pydub import AudioSegment

    director = GeminiDirector(api_key="fake-key")
    scene = Scene(
        scene_id=1,
        title="對話場景",
        lines=[
            ScriptLine(role="小明", emotion="開心", text="嗨！", voice_direction_note=""),
            ScriptLine(role="小美", emotion="溫柔", text="你好！", voice_direction_note=""),
        ],
    )
    voice_map = {"小明": "Kore", "小美": "Puck"}

    mock_resp_success = MagicMock()
    mock_part = MagicMock()
    mock_part.inline_data.data = b"\x00\x00" * 1000
    mock_part.inline_data.mime_type = "audio/pcm;rate=24000"
    mock_resp_success.candidates = [MagicMock(content=MagicMock(parts=[mock_part]))]

    # First call (multi-speaker) fails with ValueError, next 2 calls (single-speaker) succeed
    call_count = 0

    def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        config = kwargs.get("config")
        if config and config.speech_config and config.speech_config.multi_speaker_voice_config:
            raise ValueError("AI 安全審查阻擋合奏")
        return mock_resp_success

    with (
        patch.object(director, "_generate_content_with_retry", side_effect=mock_generate),
        patch.object(AudioSegment, "export") as mock_export,
    ):
        out = director.generate_scene_audio(scene, voice_map, "/tmp/test_scene.mp3")

        assert out == "/tmp/test_scene.mp3"
        # 1 multi-speaker attempt + 2 single-speaker fallback calls = 3 calls total
        assert call_count == 3
        mock_export.assert_called_once_with("/tmp/test_scene.mp3", format="mp3")


def test_build_tts_prompt_includes_emotion():
    director = GeminiDirector(api_key="fake-key")
    scene = Scene(scene_id=1, title="房間裡的對話", lines=[])
    line = ScriptLine(
        role="小明",
        emotion="憤怒",
        text="你為什麼騙我！",
        voice_direction_note="[angry, raised voice]",
    )
    prompt = director._build_tts_prompt(scene, line)

    assert "Emotion: 憤怒" in prompt
    assert "angry, raised voice" in prompt
    assert "你為什麼騙我！" in prompt


def test_build_multi_speaker_prompt_includes_emotion():
    director = GeminiDirector(api_key="fake-key")
    scene = Scene(scene_id=1, title="神秘森林", lines=[])
    group = [
        ScriptLine(role="爸爸", emotion="沉穩", text="快看！", voice_direction_note="[excited]"),
        ScriptLine(
            role="小美", emotion="害怕", text="那是怪獸嗎？", voice_direction_note="[trembling]"
        ),
    ]
    roles = ["爸爸", "小美"]
    prompt = director._build_multi_speaker_prompt(scene, group, roles)
    assert "爸爸: (沉穩, excited) 快看！" in prompt
    assert "小美: (害怕, trembling) 那是怪獸嗎？" in prompt


def test_decode_audio_data_handles_lowercase_l16_without_ffmpeg_from_file():
    from pydub import AudioSegment

    director = GeminiDirector(api_key="fake-key")
    pcm_data = b"\x00\x00" * 480  # 480 samples = 20ms at 24000Hz
    mime_type = "audio/l16; rate=24000; channels=1"

    with patch.object(AudioSegment, "from_file") as mock_from_file:
        seg = director._decode_audio_data(pcm_data, mime_type)

        # 確保不觸發 from_file (ffmpeg)
        mock_from_file.assert_not_called()
        assert seg.frame_rate == 24000
        assert seg.channels == 1
        assert seg.sample_width == 2
        assert len(seg) == 20  # 20ms
