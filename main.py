import os
import webview
from core.use_cases import StoryProcessor
from core.entities import ScriptLine, Scene, Screenplay
from infrastructure.gemini_director import GeminiDirector
from infrastructure.file_storage import LocalFileStorage
from infrastructure.story_folder_storage import StoryFolderStorage
from infrastructure.voice_map_storage import VoiceMapStorage
from infrastructure.audio_mixer import AudioMixer


_DEFAULT_VOICES = ["Kore", "Charon", "Fenrir", "Aoede", "Puck"]


class StoryForgeApi:
    def __init__(self):
        self.storage = LocalFileStorage()
        self.processor = None
        self._init_processor()

    def _init_processor(self):
        api_key = self.storage.get_api_key()
        director = GeminiDirector(api_key)
        self.processor = StoryProcessor(director=director, storage=self.storage)

    # ── API 通行證 ────────────────────────────────────────────────
    def save_api_key(self, key: str):
        try:
            self.processor.save_key(key)
            self._init_processor()
            return {"status": "ok"}
        except Exception as e:
            return {"error": str(e)}

    def get_api_key(self):
        return self.processor.get_key()

    # ── 劇本拆解 ─────────────────────────────────────────────────
    def break_down_story(self, text: str, story_name: str):
        try:
            screenplay = self.processor.break_down_screenplay(text)

            folder = StoryFolderStorage(story_name)
            folder.ensure_folder()

            # 建立初始角色聲音對應表（AI 建議）
            all_roles = list({line.role for scene in screenplay.scenes for line in scene.lines})
            voice_map = {
                role: (_DEFAULT_VOICES[i % len(_DEFAULT_VOICES)] if role != "旁白" else "Kore")
                for i, role in enumerate(all_roles)
            }
            # 旁白固定 Kore
            voice_map["旁白"] = "Kore"

            vm_storage = VoiceMapStorage(folder.folder_path)
            vm_storage.save(voice_map)

            return {
                "scenes": screenplay.to_dict()["scenes"],
                "voice_map": voice_map,
            }
        except Exception as e:
            return {"error": str(e)}

    # ── 場景語音生成 ──────────────────────────────────────────────
    def generate_scene_audio(self, scene_data: dict, story_name: str):
        try:
            folder = StoryFolderStorage(story_name)
            folder.ensure_folder()

            vm_storage = VoiceMapStorage(folder.folder_path)
            voice_map = vm_storage.load()

            lines = [ScriptLine(**ln) for ln in scene_data["lines"]]
            scene = Scene(
                scene_id=scene_data["scene_id"],
                title=scene_data["title"],
                lines=lines,
            )

            output_path = folder.scene_audio_path(scene.scene_id)
            path = self.processor.generate_scene_audio(scene, voice_map, output_path)
            return {"status": "ok", "path": path}
        except Exception as e:
            return {"error": str(e)}

    # ── 最終拼接 ──────────────────────────────────────────────────
    def mix_final_audio(self, story_name: str, scene_ids: list):
        try:
            folder = StoryFolderStorage(story_name)
            scene_paths = [folder.scene_audio_path(sid) for sid in scene_ids]
            missing = [p for p in scene_paths if not os.path.exists(p)]
            if missing:
                return {"error": f"以下場景音檔尚未生成：{missing}"}

            output_path = folder.final_audio_path()
            AudioMixer.mix(scene_paths, output_path)
            return {"status": "ok", "path": output_path}
        except Exception as e:
            return {"error": str(e)}

    # ── 聲音對應表更新 ────────────────────────────────────────────
    def update_voice_map(self, story_name: str, voice_map: dict):
        try:
            folder = StoryFolderStorage(story_name)
            vm_storage = VoiceMapStorage(folder.folder_path)
            vm_storage.save(voice_map)
            return {"status": "ok"}
        except Exception as e:
            return {"error": str(e)}

    # ── 場景音檔刪除 ──────────────────────────────────────────────
    def delete_scene_audio(self, scene_id: int, story_name: str):
        try:
            folder = StoryFolderStorage(story_name)
            path = folder.scene_audio_path(scene_id)
            if os.path.exists(path):
                os.remove(path)
            return {"status": "ok"}
        except Exception as e:
            return {"error": str(e)}


if __name__ == '__main__':
    api = StoryForgeApi()
    html_path = os.path.join(os.path.dirname(__file__), 'ui', 'index.html')
    window = webview.create_window(
        'StoryForge',
        url=html_path,
        js_api=api,
        width=1000,
        height=700,
    )
    webview.start()
