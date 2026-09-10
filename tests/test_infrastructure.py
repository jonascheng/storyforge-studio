import os
import json
import pytest
from infrastructure.file_storage import LocalFileStorage

@pytest.fixture
def temp_storage(tmp_path):
    return LocalFileStorage(base_path=str(tmp_path))

def test_save_and_get_api_key(temp_storage):
    assert temp_storage.get_api_key() == ""
    
    temp_storage.save_api_key("test_secret_key_123")
    
    assert temp_storage.get_api_key() == "test_secret_key_123"

def test_save_audio(temp_storage):
    dummy_audio_data = b"dummy_audio_content"
    output_path = temp_storage.save_audio_file("test_audio.mp3", dummy_audio_data)
    
    assert os.path.exists(output_path)
    with open(output_path, "rb") as f:
        assert f.read() == dummy_audio_data
