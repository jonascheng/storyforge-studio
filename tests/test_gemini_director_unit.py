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
                "details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "5s"}]
            }
        }
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
        }
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
                "details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "78667s"}]
            }
        }
    )
    mock_gen = MagicMock(side_effect=err_429)
    director._client.models.generate_content = mock_gen

    with patch("time.sleep") as mock_sleep:
        with pytest.raises(RuntimeError, match="今日額度已達上限"):
            director._generate_content_with_retry(model="any", contents="test", max_delay=60.0)
        assert mock_sleep.call_count == 0
        assert mock_gen.call_count == 1

