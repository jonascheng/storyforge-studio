from typing import Protocol
from core.entities import Script, Screenplay, Scene


class IDirector(Protocol):
    def break_down_script(self, story_text: str) -> Script:
        ...

    def break_down_screenplay(self, story_text: str) -> Screenplay:
        ...

    def generate_audio(self, script: Script, output_path: str) -> None:
        ...

    def generate_scene_audio(self, scene: Scene, voice_map: dict, output_path: str) -> str:
        ...

    def suggest_safe_lines(self, original_text: str) -> list[str]:
        ...

class IStorage(Protocol):
    def save_api_key(self, key: str) -> None:
        ...

    def get_api_key(self) -> str:
        ...

    def save_thinking_level(self, level: str) -> None:
        ...

    def get_thinking_level(self) -> str:
        ...


class StoryProcessor:
    def __init__(self, director: IDirector, storage: IStorage):
        self.director = director
        self.storage = storage

    def break_down(self, story_text: str) -> Script:
        return self.director.break_down_script(story_text)

    def break_down_screenplay(self, story_text: str) -> Screenplay:
        return self.director.break_down_screenplay(story_text)

    def generate_audio(self, script: Script, output_path: str) -> None:
        self.director.generate_audio(script, output_path)

    def generate_scene_audio(self, scene: Scene, voice_map: dict, output_path: str) -> str:
        return self.director.generate_scene_audio(scene, voice_map, output_path)

    def suggest_safe_lines(self, original_text: str) -> list[str]:
        return self.director.suggest_safe_lines(original_text)

    def save_key(self, key: str) -> None:
        self.storage.save_api_key(key)

    def get_key(self) -> str:
        return self.storage.get_api_key()

    def save_thinking_level(self, level: str) -> None:
        self.storage.save_thinking_level(level)

    def get_thinking_level(self) -> str:
        return self.storage.get_thinking_level()
