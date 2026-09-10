import os
import tempfile
import pytest
from unittest.mock import patch
from infrastructure.story_folder_storage import StoryFolderStorage


def test_folder_path_is_in_storyforge():
    storage = StoryFolderStorage("小王子")
    assert os.path.join("StoryForge", "小王子") in storage.folder_path


def test_scene_audio_path_format():
    storage = StoryFolderStorage("小王子")
    path = storage.scene_audio_path(3)
    assert path.endswith("scene_03.mp3")


def test_final_audio_path():
    storage = StoryFolderStorage("小王子")
    assert storage.final_audio_path().endswith("final_output.mp3")


def test_ensure_folder_creates_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_base = os.path.join(tmpdir, "StoryForge")
        with patch("infrastructure.story_folder_storage.BASE_DIR", fake_base):
            storage = StoryFolderStorage("測試故事")
            storage.ensure_folder()
            assert os.path.isdir(storage.folder_path)
