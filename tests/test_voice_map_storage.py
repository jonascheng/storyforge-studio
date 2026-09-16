import os
import tempfile

from infrastructure.voice_map_storage import VoiceMapStorage


def test_load_returns_empty_when_no_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = VoiceMapStorage(story_folder=tmpdir)
        assert storage.load() == {}


def test_save_old_format_auto_upgrades_on_load():
    """存入舊格式（字串值），load() 回傳新格式（dict）。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = VoiceMapStorage(story_folder=tmpdir)
        vm = {"旁白": "Kore", "小明": "Charon"}
        storage.save(vm)
        loaded = storage.load()
        assert loaded["旁白"] == {"voice": "Kore", "audio_profile": ""}
        assert loaded["小明"] == {"voice": "Charon", "audio_profile": ""}


def test_save_new_format_round_trip():
    """存入新格式（dict 值），load() 完整保留。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = VoiceMapStorage(story_folder=tmpdir)
        vm = {
            "旁白": {"voice": "Kore", "audio_profile": "Calm, steady audiobook narrator."},
            "小明": {"voice": "Puck", "audio_profile": "Young boy, cheerful and curious."},
        }
        storage.save(vm)
        loaded = storage.load()
        assert loaded == vm


def test_load_voice_names_returns_str_dict():
    """load_voice_names() 回傳 role → voice 字串字典。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = VoiceMapStorage(story_folder=tmpdir)
        vm = {
            "旁白": {"voice": "Kore", "audio_profile": "Narrator."},
            "小明": {"voice": "Puck", "audio_profile": "Young boy."},
        }
        storage.save(vm)
        names = storage.load_voice_names()
        assert names == {"旁白": "Kore", "小明": "Puck"}


def test_save_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = VoiceMapStorage(story_folder=tmpdir)
        storage.save({"旁白": "Kore"})
        assert os.path.exists(os.path.join(tmpdir, "voice_map.json"))
