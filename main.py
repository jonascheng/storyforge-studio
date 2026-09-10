import os
import webview
from core.use_cases import StoryProcessor
from core.entities import Script, ScriptLine
from infrastructure.gemini_director import GeminiDirector
from infrastructure.file_storage import LocalFileStorage

class StoryForgeApi:
    def __init__(self):
        self.storage = LocalFileStorage()
        # Ensure we always use the latest key when instantiating the director
        self.processor = None
        self._init_processor()

    def _init_processor(self):
        api_key = self.storage.get_api_key()
        director = GeminiDirector(api_key)
        self.processor = StoryProcessor(director=director, storage=self.storage)

    def save_api_key(self, key: str):
        try:
            self.processor.save_key(key)
            self._init_processor() # Reload director with new key
            return {"status": "ok"}
        except Exception as e:
            return {"error": str(e)}

    def get_api_key(self):
        return self.processor.get_key()

    def break_down_story(self, text: str):
        try:
            script = self.processor.break_down(text)
            return {"lines": script.to_dict()["lines"]}
        except Exception as e:
            return {"error": str(e)}

    def generate_audio(self, payload: dict):
        try:
            # Reconstruct Script entity from payload
            lines = [ScriptLine(**item) for item in payload.get("lines", [])]
            script = Script(lines=lines)
            
            output_filename = "storyforge_output.mp3"
            output_path = os.path.join(self.storage.base_path, output_filename)
            
            self.processor.generate_audio(script, output_path)
            return {"status": "ok", "path": output_path}
        except Exception as e:
            return {"error": str(e)}

if __name__ == '__main__':
    api = StoryForgeApi()
    
    # Path to the UI folder
    html_path = os.path.join(os.path.dirname(__file__), 'ui', 'index.html')
    
    window = webview.create_window(
        'StoryForge', 
        url=html_path, 
        js_api=api,
        width=1000, 
        height=700
    )
    webview.start()
