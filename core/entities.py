from dataclasses import asdict, dataclass


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

    def to_dict(self):
        return {
            "scene_id": self.scene_id,
            "title": self.title,
            "lines": [line.to_dict() for line in self.lines],
            "audio_path": self.audio_path,
        }


@dataclass
class Screenplay:
    scenes: list[Scene]

    def to_dict(self):
        return {"scenes": [scene.to_dict() for scene in self.scenes]}


# 向後相容 — 舊 Script 仍可用
@dataclass
class Script:
    lines: list[ScriptLine]

    def to_dict(self):
        return {"lines": [asdict(line) for line in self.lines]}
