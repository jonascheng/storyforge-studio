import os
import webview
from core.use_cases import StoryProcessor
from core.entities import ScriptLine, Scene, Screenplay
from infrastructure.gemini_director import GeminiDirector
from infrastructure.file_storage import LocalFileStorage
from infrastructure.story_folder_storage import StoryFolderStorage, BASE_DIR
from infrastructure.voice_map_storage import VoiceMapStorage
from infrastructure.audio_mixer import AudioMixer


_DEFAULT_VOICES = ["Kore", "Charon", "Fenrir", "Aoede", "Puck"]


class StoryForgeApi:
    def __init__(self):
        self.storage = LocalFileStorage()
        self.processor = None
        self.story_paths = {}
        self._init_processor()

    def _init_processor(self):
        api_key = self.storage.get_api_key()
        thinking_level = self.storage.get_thinking_level()
        director = GeminiDirector(api_key, thinking_level)
        self.processor = StoryProcessor(director=director, storage=self.storage)

    def _get_storage(self, story_name: str, folder_path: str = None) -> StoryFolderStorage:
        if folder_path:
            self.story_paths[story_name] = folder_path
        stored_path = self.story_paths.get(story_name)
        return StoryFolderStorage(story_name, folder_path=stored_path)

    # ── 設定 ────────────────────────────────────────────────
    def save_settings(self, key: str, thinking_level: str):
        try:
            self.processor.save_key(key)
            self.processor.save_thinking_level(thinking_level)
            self._init_processor()
            return {"status": "ok"}
        except Exception as e:
            return {"error": str(e)}

    def get_settings(self):
        return {
            "key": self.processor.get_key(),
            "thinking_level": self.processor.get_thinking_level()
        }

    # ── 劇本拆解 ─────────────────────────────────────────────────
    def break_down_story(self, text: str, story_name: str):
        try:
            screenplay = self.processor.break_down_screenplay(text)

            folder = self._get_storage(story_name)
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

            # 將剛拆解完的劇本存檔
            scenes_data = screenplay.to_dict()["scenes"]
            folder.save_screenplay(scenes_data)

            return {
                "scenes": scenes_data,
                "voice_map": voice_map,
            }
        except Exception as e:
            return {"error": str(e)}

    def check_screenplay(self, story_name: str):
        folder = self._get_storage(story_name)
        return os.path.exists(folder.screenplay_path())

    def list_stories(self):
        try:
            return {"stories": StoryFolderStorage.list_stories()}
        except Exception as e:
            return {"error": str(e)}

    def select_story_folder(self):
        try:
            window = webview.active_window()
            if not window:
                return {"error": "無法開啟檔案選取視窗"}
            initial_dir = BASE_DIR if os.path.exists(BASE_DIR) else os.path.expanduser("~")
            res = window.create_file_dialog(webview.FOLDER_DIALOG, directory=initial_dir)
            if not res:
                return {"cancelled": True}
            folder_path = res[0]
            screenplay_file = os.path.join(folder_path, "screenplay.json")
            if not os.path.exists(screenplay_file):
                return {"error": "選取的資料夾內找不到劇本進度檔 (screenplay.json)"}
            story_name = os.path.basename(folder_path)
            return self.load_screenplay(story_name, folder_path=folder_path)
        except Exception as e:
            return {"error": str(e)}

    def load_screenplay(self, story_name: str, folder_path: str = None):
        try:
            folder = self._get_storage(story_name, folder_path=folder_path)
            if not os.path.exists(folder.screenplay_path()):
                return {"error": "找不到舊劇本"}
            scenes_data = folder.load_screenplay()
            
            vm_storage = VoiceMapStorage(folder.folder_path)
            voice_map = vm_storage.load()
            
            audio_ready_ids = []
            for scene in scenes_data:
                sid = scene.get("scene_id")
                if sid is not None and os.path.exists(folder.scene_audio_path(sid)):
                    audio_ready_ids.append(sid)

            return {
                "story_name": story_name,
                "scenes": scenes_data,
                "voice_map": voice_map,
                "audio_ready_ids": audio_ready_ids,
                "folder_path": folder.folder_path,
            }
        except Exception as e:
            return {"error": str(e)}

    def save_screenplay_progress(self, story_name: str, scenes_data: list):
        try:
            folder = self._get_storage(story_name)
            folder.ensure_folder()
            folder.save_screenplay(scenes_data)
            return {"status": "ok"}
        except Exception as e:
            return {"error": str(e)}

    # ── 場景語音生成 ──────────────────────────────────────────────
    def generate_scene_audio(self, scene_data: dict, story_name: str):
        try:
            folder = self._get_storage(story_name)
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

    def suggest_safe_lines(self, original_text: str):
        try:
            suggestions = self.processor.suggest_safe_lines(original_text)
            return {"status": "ok", "suggestions": suggestions}
        except Exception as e:
            return {"error": str(e)}

    # ── 最終拼接 ──────────────────────────────────────────────────
    def mix_final_audio(self, story_name: str, scene_ids: list):
        try:
            folder = self._get_storage(story_name)
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
            folder = self._get_storage(story_name)
            vm_storage = VoiceMapStorage(folder.folder_path)
            vm_storage.save(voice_map)
            return {"status": "ok"}
        except Exception as e:
            return {"error": str(e)}

    # ── 場景音檔刪除 ──────────────────────────────────────────────
    def delete_scene_audio(self, scene_id: int, story_name: str):
        try:
            folder = self._get_storage(story_name)
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
