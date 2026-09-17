import base64
import os
import traceback

import webview

from core.entities import Scene, ScriptLine, StoryScript
from core.use_cases import StoryProcessor
from infrastructure.audio_mixer import AudioMixer
from infrastructure.bgm_map_storage import BgmMapStorage
from infrastructure.file_storage import LocalFileStorage
from infrastructure.gemini_director import GeminiDirector
from infrastructure.story_folder_storage import BASE_DIR, StoryFolderStorage
from infrastructure.voice_map_storage import VoiceMapStorage


class StoryForgeApi:
    def __init__(self):
        self.storage = LocalFileStorage()
        self.processor = None
        self.story_paths = {}
        self._init_processor()

    @staticmethod
    def _handle_error(action: str, e: Exception) -> dict:
        print(f"\n[API ERROR] {action}: {e}")
        traceback.print_exc()
        return {"error": str(e)}

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
    def save_settings(self, key: str, thinking_level: str, pause_seconds: int = 1):
        try:
            self.processor.save_key(key)
            self.processor.save_thinking_level(thinking_level)
            self.processor.save_pause_seconds(int(pause_seconds))
            self._init_processor()
            return {"status": "ok"}
        except Exception as e:
            return self._handle_error("save_settings", e)

    def get_settings(self):
        return {
            "key": self.processor.get_key(),
            "thinking_level": self.processor.get_thinking_level(),
            "pause_seconds": self.processor.get_pause_seconds(),
        }

    # ── 故事編劇步驟 (Screenwriter Step) ─────────────────────────
    def expand_story(self, short_input: str):
        try:
            story_script = self.processor.expand_story_script(short_input)
            story_name = story_script.title.strip()
            # 確保有資料夾
            folder = self._get_storage(story_name)
            folder.ensure_folder()
            # 儲存
            folder.save_story_script(story_script.to_dict())
            return {
                "status": "ok",
                "story_script": story_script.to_dict(),
                "story_name": story_name,
            }
        except Exception as e:
            return self._handle_error("expand_story", e)

    def tweak_story(self, story_name: str, current_script_dict: dict, instruction: str):
        try:
            current_script = StoryScript(**current_script_dict)
            new_script = self.processor.tweak_story_script(current_script, instruction)
            folder = self._get_storage(story_name)
            folder.ensure_folder()
            folder.save_story_script(new_script.to_dict())
            return {"status": "ok", "story_script": new_script.to_dict()}
        except Exception as e:
            return self._handle_error("tweak_story", e)

    def save_story_script(self, story_name: str, script_dict: dict):
        try:
            folder = self._get_storage(story_name)
            folder.ensure_folder()
            folder.save_story_script(script_dict)
            return {"status": "ok"}
        except Exception as e:
            return self._handle_error("save_story_script", e)

    def get_story_history(self, story_name: str):
        try:
            folder = self._get_storage(story_name)
            history = folder.load_story_history()
            return {"status": "ok", "history": history}
        except Exception as e:
            return self._handle_error("get_story_history", e)

    def restore_story_version(self, story_name: str, version_index: int):
        try:
            folder = self._get_storage(story_name)
            restored = folder.restore_story_script_version(version_index)
            if not restored:
                return {"error": "找不到該版本"}
            return {"status": "ok", "story_script": restored}
        except Exception as e:
            return self._handle_error("restore_story_version", e)

    # ── 劇本拆解 (Analyst Step) ──────────────────────────────────
    def break_down_story(self, story_script_dict: dict, story_name: str):
        try:
            folder = self._get_storage(story_name)
            folder.ensure_folder()

            # 將整個 StoryScript 轉為純文字，供後續拆解
            story_script = StoryScript(**story_script_dict)
            text_for_analysis = (
                f"【標題】{story_script.title}\n\n"
                f"【故事內容】\n{story_script.story_text}\n\n"
                f"【角色設定】\n{story_script.character_cards}\n\n"
                f"【世界觀】\n{story_script.worldview_rules}"
            )

            # 1. 預先掃描定義 BGM 主題
            bgm_map = self.processor.define_bgm_themes(text_for_analysis)
            bgm_storage = BgmMapStorage(folder.folder_path)
            bgm_storage.save(bgm_map)

            # 2. 進行劇本拆解
            screenplay = self.processor.break_down_screenplay(text_for_analysis, bgm_map=bgm_map)

            # 儲存角色聲音對應表（AI 建議 + 防撞處理）
            voice_map = screenplay.voice_map
            vm_storage = VoiceMapStorage(folder.folder_path)
            vm_storage.save(voice_map)

            # 將剛拆解完的劇本存檔
            scenes_data = screenplay.to_dict()["scenes"]
            folder.save_screenplay(scenes_data)

            return {
                "scenes": scenes_data,
                "voice_map": voice_map,
                "bgm_map": bgm_map.to_dict() if bgm_map else None,
            }
        except Exception as e:
            return self._handle_error("break_down_story", e)

    def check_screenplay(self, story_name: str):
        folder = self._get_storage(story_name)
        return os.path.exists(folder.screenplay_path())

    def list_stories(self):
        try:
            return {"stories": StoryFolderStorage.list_stories()}
        except Exception as e:
            return self._handle_error("list_stories", e)

    def select_story_folder(self):
        try:
            window = webview.active_window()
            if not window:
                return {"error": "無法開啟檔案選取視窗"}
            initial_dir = BASE_DIR if os.path.exists(BASE_DIR) else os.path.expanduser("~")
            folder_dialog_type = getattr(
                webview.FileDialog, "FOLDER", getattr(webview, "FOLDER_DIALOG", 20)
            )
            res = window.create_file_dialog(folder_dialog_type, directory=initial_dir)
            if not res:
                return {"cancelled": True}
            folder_path = res[0]
            screenplay_file = os.path.join(folder_path, "screenplay.json")
            if not os.path.exists(screenplay_file):
                return {"error": "選取的資料夾內找不到劇本進度檔 (screenplay.json)"}
            story_name = os.path.basename(folder_path)
            return self.load_screenplay(story_name, folder_path=folder_path)
        except Exception as e:
            return self._handle_error("select_story_folder", e)

    def load_screenplay(self, story_name: str, folder_path: str = None):
        try:
            folder = self._get_storage(story_name, folder_path=folder_path)
            if not os.path.exists(folder.screenplay_path()):
                return {"error": "找不到舊劇本"}
            scenes_data = folder.load_screenplay()

            vm_storage = VoiceMapStorage(folder.folder_path)
            voice_map = vm_storage.load()

            bgm_storage = BgmMapStorage(folder.folder_path)
            bgm_map = bgm_storage.load()

            audio_ready_ids = []
            for scene in scenes_data:
                sid = scene.get("scene_id")
                if sid is not None and os.path.exists(folder.scene_audio_path(sid)):
                    audio_ready_ids.append(sid)

            story_script = folder.load_story_script()

            return {
                "story_name": story_name,
                "story_script": story_script,
                "scenes": scenes_data,
                "voice_map": voice_map,
                "bgm_map": bgm_map.to_dict() if bgm_map else None,
                "audio_ready_ids": audio_ready_ids,
                "folder_path": folder.folder_path,
            }
        except Exception as e:
            return self._handle_error("load_screenplay", e)

    def save_screenplay_progress(self, story_name: str, scenes_data: list):
        try:
            folder = self._get_storage(story_name)
            folder.ensure_folder()
            folder.save_screenplay(scenes_data)
            return {"status": "ok"}
        except Exception as e:
            return self._handle_error("save_screenplay_progress", e)

    # ── 場景語音生成 ──────────────────────────────────────────────
    def generate_scene_audio(self, scene_data: dict, story_name: str):
        try:
            if not scene_data or not isinstance(scene_data, dict):
                raise ValueError("傳入的場景資料無效 (scene_data 為空)")
            if "lines" not in scene_data or scene_data["lines"] is None:
                raise ValueError("場景資料缺少台詞清單 (lines 為空)")

            folder = self._get_storage(story_name)
            folder.ensure_folder()

            vm_storage = VoiceMapStorage(folder.folder_path)
            # 載入完整 voice_map（含 audio_profile），讓 director 能提取 Audio Profile
            voice_map = vm_storage.load()

            lines = [ScriptLine(**ln) for ln in scene_data["lines"]]
            scene = Scene(
                scene_id=scene_data.get("scene_id", 1),
                title=scene_data.get("title", ""),
                lines=lines,
                bgm_theme_id=scene_data.get("bgm_theme_id"),
                scene_description=scene_data.get("scene_description", ""),
            )

            bgm_storage = BgmMapStorage(folder.folder_path)
            bgm_map = bgm_storage.load()

            output_path = folder.scene_audio_path(scene.scene_id)
            path = self.processor.generate_scene_audio(
                scene, voice_map, output_path, bgm_map=bgm_map
            )
            return {"status": "ok", "path": path}
        except Exception as e:
            return self._handle_error("generate_scene_audio", e)

    def get_scene_audio_base64(self, scene_id: int, story_name: str):
        try:
            folder = self._get_storage(story_name)
            path = folder.scene_audio_path(scene_id)
            if not os.path.exists(path):
                return {"error": "Audio file not found"}
            with open(path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            return {"status": "ok", "base64": encoded}
        except Exception as e:
            return self._handle_error("get_scene_audio_base64", e)

    def suggest_safe_lines(self, original_text: str):
        try:
            suggestions = self.processor.suggest_safe_lines(original_text)
            return {"status": "ok", "suggestions": suggestions}
        except Exception as e:
            return self._handle_error("suggest_safe_lines", e)

    # ── 最終拼接 ──────────────────────────────────────────────────
    def mix_final_audio(self, story_name: str, scene_ids: list):
        try:
            folder = self._get_storage(story_name)
            scene_paths = [folder.scene_audio_path(sid) for sid in scene_ids]
            missing = [p for p in scene_paths if not os.path.exists(p)]
            if missing:
                return {"error": f"以下場景音檔尚未生成：{missing}"}

            output_path = folder.final_audio_path()
            pause_seconds = self.processor.get_pause_seconds()
            AudioMixer.mix(scene_paths, output_path, pause_seconds=pause_seconds)
            return {"status": "ok", "path": output_path}
        except Exception as e:
            return self._handle_error("mix_final_audio", e)

    # ── 聲音對應表更新 ────────────────────────────────────────────
    def update_voice_map(self, story_name: str, voice_map: dict):
        try:
            folder = self._get_storage(story_name)
            vm_storage = VoiceMapStorage(folder.folder_path)
            vm_storage.save(voice_map)
            return {"status": "ok"}
        except Exception as e:
            return self._handle_error("update_voice_map", e)

    # ── 場景音檔刪除 ──────────────────────────────────────────────
    def delete_scene_audio(self, scene_id: int, story_name: str):
        try:
            folder = self._get_storage(story_name)
            path = folder.scene_audio_path(scene_id)
            if os.path.exists(path):
                os.remove(path)
            return {"status": "ok"}
        except Exception as e:
            return self._handle_error("delete_scene_audio", e)


def main():
    try:
        import static_ffmpeg

        static_ffmpeg.add_paths(weak=True)
    except Exception:
        pass

    api = StoryForgeApi()
    html_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")
    webview.create_window(
        "StoryForge",
        url=html_path,
        js_api=api,
        width=1000,
        height=700,
    )
    webview.start()


if __name__ == "__main__":
    main()
