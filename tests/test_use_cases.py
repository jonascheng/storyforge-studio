from core.entities import BgmMap, Scene, Screenplay, Script, ScriptLine
from core.use_cases import StoryProcessor


class MockDirector:
    def define_bgm_themes(self, story_text: str) -> BgmMap:
        return BgmMap()

    def break_down_script(self, story_text: str) -> Script:
        return Script(lines=[ScriptLine(role="旁白", emotion="平靜", text="這是一個測試故事。")])

    def break_down_screenplay(self, story_text: str, bgm_map: BgmMap | None = None) -> Screenplay:
        return Screenplay(scenes=[])

    def generate_audio(self, script: Script, output_path: str) -> None:
        pass

    def generate_scene_audio(
        self, scene: Scene, voice_map: dict, output_path: str, bgm_map: BgmMap | None = None
    ) -> str:
        return output_path

    def suggest_safe_lines(self, original_text: str) -> list[str]:
        return []


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


# ── Task 2: Scene-aware interface ────────────────────────────────────────────


class MockDirectorV2:
    def define_bgm_themes(self, story_text: str) -> BgmMap:
        return BgmMap()

    def break_down_script(self, story_text: str):
        return Script(
            lines=[
                ScriptLine(
                    role="旁白", emotion="平靜", text="這是一個測試故事。", voice_direction_note=""
                )
            ]
        )

    def break_down_screenplay(self, story_text: str, bgm_map: BgmMap | None = None) -> Screenplay:
        line = ScriptLine(role="旁白", emotion="平靜", text="測試。", voice_direction_note="[calm]")
        scene = Scene(scene_id=1, title="開場", lines=[line])
        return Screenplay(scenes=[scene])

    def generate_audio(self, script, output_path: str) -> None:
        pass

    def generate_scene_audio(
        self, scene: Scene, voice_map: dict, output_path: str, bgm_map: BgmMap | None = None
    ) -> str:
        return output_path

    def suggest_safe_lines(self, original_text: str) -> list[str]:
        return []


class MockStorageV2:
    def save_api_key(self, key: str) -> None:
        self.key = key

    def get_api_key(self) -> str:
        return getattr(self, "key", "")


def test_break_down_screenplay():
    processor = StoryProcessor(director=MockDirectorV2(), storage=MockStorageV2())
    screenplay = processor.break_down_screenplay("測試故事")
    assert len(screenplay.scenes) == 1
    assert screenplay.scenes[0].title == "開場"


def test_generate_scene_audio():
    processor = StoryProcessor(director=MockDirectorV2(), storage=MockStorageV2())
    line = ScriptLine(role="旁白", emotion="平靜", text="測試。", voice_direction_note="[calm]")
    scene = Scene(scene_id=1, title="開場", lines=[line])
    voice_map = {"旁白": "Kore"}
    path = processor.generate_scene_audio(scene, voice_map, "/tmp/scene_01.mp3")
    assert path == "/tmp/scene_01.mp3"
