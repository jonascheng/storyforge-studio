import pytest
from core.entities import Script, ScriptLine
from core.use_cases import StoryProcessor

class MockDirector:
    def break_down_script(self, story_text: str) -> Script:
        return Script(lines=[
            ScriptLine(role="旁白", emotion="平靜", text="這是一個測試故事。")
        ])
        
    def generate_audio(self, script: Script, output_path: str) -> None:
        pass

class MockStorage:
    def save_api_key(self, key: str) -> None:
        self.key = key
        
    def get_api_key(self) -> str:
        return getattr(self, "key", "")

def test_process_story():
    processor = StoryProcessor(director=MockDirector(), storage=MockStorage())
    
    script = processor.break_down("這是一個測試故事。")
    assert len(script.lines) == 1
    assert script.lines[0].text == "這是一個測試故事。"

def test_api_key_management():
    processor = StoryProcessor(director=MockDirector(), storage=MockStorage())
    
    processor.save_key("test_key_123")
    assert processor.get_key() == "test_key_123"
