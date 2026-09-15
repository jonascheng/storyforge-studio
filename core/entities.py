from dataclasses import asdict, dataclass, field


@dataclass
class ScriptLine:
    role: str
    emotion: str
    text: str
    voice_direction_note: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class Scene:
    scene_id: int
    title: str
    lines: list[ScriptLine]
    audio_path: str | None = None
    bgm_prompt: str | None = None  # AI 導演建議的場景背景音樂 prompt（給 Lyria 用）

    def to_dict(self):
        return {
            "scene_id": self.scene_id,
            "title": self.title,
            "lines": [line.to_dict() for line in self.lines],
            "audio_path": self.audio_path,
            "bgm_prompt": self.bgm_prompt,
        }


@dataclass
class Screenplay:
    scenes: list[Scene]
    voice_map: dict[str, str] = field(default_factory=dict)

    def to_dict(self):
        return {
            "scenes": [scene.to_dict() for scene in self.scenes],
            "voice_map": self.voice_map,
        }


# 向後相容 — 舊 Script 仍可用
@dataclass
class Script:
    lines: list[ScriptLine]

    def to_dict(self):
        return {"lines": [asdict(line) for line in self.lines]}
