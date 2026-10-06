from unittest.mock import MagicMock, patch

from main import StoryForgeApi


def test_api_generate_scene_audio_passes_ambience_id(tmp_path):
    api = StoryForgeApi()
    api.processor = MagicMock()
    scene_data = {
        "scene_id": 1,
        "title": "雨夜場景",
        "bgm_theme_id": "tension",
        "ambience_id": "rain",
        "scene_description": "Rain outside",
        "lines": [{"role": "旁白", "emotion": "平靜", "text": "下雨了"}],
    }
    with patch.object(api, "_get_storage") as mock_storage_factory:
        mock_storage = MagicMock()
        mock_storage.folder_path = str(tmp_path)
        mock_storage.scene_audio_path.return_value = str(tmp_path / "scene_01.mp3")
        mock_storage_factory.return_value = mock_storage

        res = api.generate_scene_audio(scene_data, "TestStory")
        assert res.get("status") == "ok"
        passed_scene = api.processor.generate_scene_audio.call_args[0][0]
        assert passed_scene.ambience_id == "rain"
