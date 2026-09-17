import datetime
import json
import os

BASE_DIR = os.path.join(os.path.expanduser("~"), "Documents", "StoryForge")


class StoryFolderStorage:
    def __init__(self, story_name: str, folder_path: str = None):
        self.story_name = story_name
        self.folder_path = folder_path if folder_path else os.path.join(BASE_DIR, story_name)

    def ensure_folder(self) -> None:
        os.makedirs(self.folder_path, exist_ok=True)

    def scene_audio_path(self, scene_id: int) -> str:
        return os.path.join(self.folder_path, f"scene_{scene_id:02d}.mp3")

    def final_audio_path(self) -> str:
        return os.path.join(self.folder_path, "final_output.mp3")

    def screenplay_path(self) -> str:
        return os.path.join(self.folder_path, "screenplay.json")

    def story_script_path(self) -> str:
        return os.path.join(self.folder_path, "story_script.json")

    def save_screenplay(self, scenes_data: list) -> None:
        with open(self.screenplay_path(), "w", encoding="utf-8") as f:
            json.dump(scenes_data, f, ensure_ascii=False, indent=2)

    def load_screenplay(self) -> list:
        path = self.screenplay_path()
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def save_story_script(self, data: dict) -> None:
        """Saves a new version of the story script to history."""
        history = self.load_story_history()
        history.append(data)
        with open(self.story_script_path(), "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def load_story_script(self) -> dict | None:
        """Loads the latest version of the story script."""
        history = self.load_story_history()
        if history:
            return history[-1]
        return None

    def load_story_history(self) -> list[dict]:
        path = self.story_script_path()
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                # Handle case where it might have been saved as a single object previously
                return [data]
            except json.JSONDecodeError:
                return []

    def restore_story_script_version(self, version_index: int) -> dict | None:
        """Restores history to a specific version (0-indexed)."""
        history = self.load_story_history()
        if 0 <= version_index < len(history):
            new_history = history[: version_index + 1]
            with open(self.story_script_path(), "w", encoding="utf-8") as f:
                json.dump(new_history, f, ensure_ascii=False, indent=2)
            return new_history[-1]
        return None

    @classmethod
    def list_stories(cls, base_dir: str = BASE_DIR) -> list:
        if not os.path.exists(base_dir):
            return []
        results = []
        try:
            for entry in os.scandir(base_dir):
                if entry.is_dir():
                    sc_path = os.path.join(entry.path, "screenplay.json")
                    if os.path.exists(sc_path):
                        mtime = os.path.getmtime(sc_path)
                        updated_at = datetime.datetime.fromtimestamp(mtime).strftime(
                            "%Y-%m-%d %H:%M"
                        )
                        count = 0
                        try:
                            with open(sc_path, encoding="utf-8") as f:
                                data = json.load(f)
                                if isinstance(data, list):
                                    count = len(data)
                        except Exception:
                            pass
                        results.append(
                            {
                                "name": entry.name,
                                "scene_count": count,
                                "updated_at": updated_at,
                                "folder_path": entry.path,
                                "mtime": mtime,
                            }
                        )
        except Exception:
            return []
        results.sort(key=lambda x: x["mtime"], reverse=True)
        return results
