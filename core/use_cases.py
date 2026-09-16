from typing import Protocol

from core.entities import BgmMap, Scene, Screenplay, Script


class IDirector(Protocol):
    def define_bgm_themes(self, story_text: str) -> BgmMap: ...

    def break_down_script(self, story_text: str) -> Script: ...

    def break_down_screenplay(
        self, story_text: str, bgm_map: BgmMap | None = None
    ) -> Screenplay: ...

    def generate_audio(self, script: Script, output_path: str) -> None: ...

    def generate_scene_audio(
        self, scene: Scene, voice_map: dict, output_path: str, bgm_map: BgmMap | None = None
    ) -> str: ...

    def suggest_safe_lines(self, original_text: str) -> list[str]: ...


class IStorage(Protocol):
    def save_api_key(self, key: str) -> None: ...

    def get_api_key(self) -> str: ...

    def save_thinking_level(self, level: str) -> None: ...

    def get_thinking_level(self) -> str: ...


class StoryProcessor:
    def __init__(self, director: IDirector, storage: IStorage):
        self.director = director
        self.storage = storage

    def define_bgm_themes(self, story_text: str) -> BgmMap:
        return self.director.define_bgm_themes(story_text)

    def break_down(self, story_text: str) -> Script:
        return self.director.break_down_script(story_text)

    def break_down_screenplay(self, story_text: str, bgm_map: BgmMap | None = None) -> Screenplay:
        return self.director.break_down_screenplay(story_text, bgm_map)

    def generate_audio(self, script: Script, output_path: str) -> None:
        self.director.generate_audio(script, output_path)

    def generate_scene_audio(
        self, scene: Scene, voice_map: dict, output_path: str, bgm_map: BgmMap | None = None
    ) -> str:
        return self.director.generate_scene_audio(scene, voice_map, output_path, bgm_map)

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
