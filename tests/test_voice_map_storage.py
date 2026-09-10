import os
import tempfile
import pytest
from infrastructure.voice_map_storage import VoiceMapStorage


def test_load_returns_empty_when_no_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = VoiceMapStorage(story_folder=tmpdir)
        assert storage.load() == {}


def test_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = VoiceMapStorage(story_folder=tmpdir)
        vm = {"旁白": "Kore", "小明": "Charon"}
        storage.save(vm)
        loaded = storage.load()
        assert loaded == vm


def test_save_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = VoiceMapStorage(story_folder=tmpdir)
        storage.save({"旁白": "Kore"})
        assert os.path.exists(os.path.join(tmpdir, "voice_map.json"))
