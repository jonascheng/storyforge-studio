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
