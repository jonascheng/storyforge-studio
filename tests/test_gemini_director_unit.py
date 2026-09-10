import json
import pytest
from unittest.mock import MagicMock, patch
from infrastructure.gemini_director import GeminiDirector


FAKE_SCREENPLAY_JSON = json.dumps([
    {
        "scene_id": 1,
        "title": "開場",
        "lines": [
            {"role": "旁白", "emotion": "平靜", "text": "從前從前...", "voice_direction_note": "[calm, slow]"},
            {"role": "小明", "emotion": "開心", "text": "你好！", "voice_direction_note": "[cheerful]"}
        ]
    },
    {
        "scene_id": 2,
        "title": "衝突",
        "lines": [
            {"role": "旁白", "emotion": "緊張", "text": "突然...", "voice_direction_note": "[tense]"}
        ]
    }
])


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


def test_break_down_screenplay_raises_on_bad_json():
    director = GeminiDirector(api_key="fake-key")
    with patch.object(director, "_call_director_model", return_value="not json at all"):
        with pytest.raises(ValueError, match="AI 導演回傳的格式有誤"):
            director.break_down_screenplay("故事")


def test_requires_api_key():
    director = GeminiDirector(api_key="")
    with pytest.raises(ValueError, match="API 通行證"):
        director.break_down_screenplay("故事")
