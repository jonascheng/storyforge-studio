import os
import json
from core.use_cases import IStorage

DEFAULT_CONFIG_DIR = os.path.join(os.path.expanduser("~"), "Documents", "StoryForge")


class LocalFileStorage(IStorage):
    def __init__(self, base_path: str = None):
        self.base_path = base_path if base_path is not None else DEFAULT_CONFIG_DIR
        self.config_path = os.path.join(self.base_path, "storyforge_config.json")

    def _ensure_dir(self) -> None:
        os.makedirs(self.base_path, exist_ok=True)

    def save_api_key(self, key: str) -> None:
        self._ensure_dir()
        config = {}
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                try:
                    config = json.load(f)
                except json.JSONDecodeError:
                    pass
        config["api_key"] = key
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f)
            
    def get_api_key(self) -> str:
        if not os.path.exists(self.config_path):
            return ""
        with open(self.config_path, "r", encoding="utf-8") as f:

            try:
                config = json.load(f)
                return config.get("api_key", "")
            except json.JSONDecodeError:
                return ""

    def save_thinking_level(self, level: str) -> None:
        self._ensure_dir()
        config = {}
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                try:
                    config = json.load(f)
                except json.JSONDecodeError:
                    pass
        config["thinking_level"] = level
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f)

    def get_thinking_level(self) -> str:
        if not os.path.exists(self.config_path):
            return "MEDIUM"
        with open(self.config_path, "r", encoding="utf-8") as f:
            try:
                config = json.load(f)
                return config.get("thinking_level", "MEDIUM")
            except json.JSONDecodeError:
                return "MEDIUM"
                
    def save_audio_file(self, filename: str, audio_data: bytes) -> str:
        self._ensure_dir()
        output_path = os.path.join(self.base_path, filename)
        with open(output_path, "wb") as f:
            f.write(audio_data)
        return output_path

