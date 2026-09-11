import os
import json
from core.use_cases import IStorage

class LocalFileStorage(IStorage):
    def __init__(self, base_path: str = "."):
        self.base_path = base_path
        self.config_path = os.path.join(self.base_path, "storyforge_config.json")
        
    def save_api_key(self, key: str) -> None:
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
        output_path = os.path.join(self.base_path, filename)
        with open(output_path, "wb") as f:
            f.write(audio_data)
        return output_path
