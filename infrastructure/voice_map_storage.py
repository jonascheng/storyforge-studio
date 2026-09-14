import json
import os


class VoiceMapStorage:
    def __init__(self, story_folder: str):
        self.path = os.path.join(story_folder, "voice_map.json")

    def load(self) -> dict:
        if not os.path.exists(self.path):
            return {}
        with open(self.path, encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

    def save(self, voice_map: dict) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(voice_map, f, ensure_ascii=False, indent=2)
