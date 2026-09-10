from typing import Protocol
from core.entities import Script

class IDirector(Protocol):
    def break_down_script(self, story_text: str) -> Script:
        ...
        
    def generate_audio(self, script: Script, output_path: str) -> None:
        ...

class IStorage(Protocol):
    def save_api_key(self, key: str) -> None:
        ...
        
    def get_api_key(self) -> str:
        ...

class StoryProcessor:
    def __init__(self, director: IDirector, storage: IStorage):
        self.director = director
        self.storage = storage
        
    def break_down(self, story_text: str) -> Script:
        return self.director.break_down_script(story_text)
        
    def generate_audio(self, script: Script, output_path: str) -> None:
        self.director.generate_audio(script, output_path)
        
    def save_key(self, key: str) -> None:
        self.storage.save_api_key(key)
        
    def get_key(self) -> str:
        return self.storage.get_api_key()
