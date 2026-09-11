import os

BASE_DIR = os.path.join(os.path.expanduser("~"), "Documents", "StoryForge")


class StoryFolderStorage:
    def __init__(self, story_name: str):
        self.story_name = story_name
        self.folder_path = os.path.join(BASE_DIR, story_name)

    def ensure_folder(self) -> None:
        os.makedirs(self.folder_path, exist_ok=True)

    def scene_audio_path(self, scene_id: int) -> str:
        return os.path.join(self.folder_path, f"scene_{scene_id:02d}.mp3")

    def final_audio_path(self) -> str:
        return os.path.join(self.folder_path, "final_output.mp3")

    def screenplay_path(self) -> str:
        return os.path.join(self.folder_path, "screenplay.json")

    def save_screenplay(self, scenes_data: list) -> None:
        import json
        with open(self.screenplay_path(), "w", encoding="utf-8") as f:
            json.dump(scenes_data, f, ensure_ascii=False, indent=2)

    def load_screenplay(self) -> list:
        import json
        path = self.screenplay_path()
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
