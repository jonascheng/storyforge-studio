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
class BgmTheme:
    name: str
    prompt: str

    def to_dict(self):
        return asdict(self)


@dataclass
class BgmMap:
    themes: dict[str, BgmTheme] = field(default_factory=dict)

    def to_dict(self):
        return {"themes": {k: v.to_dict() for k, v in self.themes.items()}}


@dataclass
class Scene:
    scene_id: int
    title: str
    lines: list[ScriptLine]
    bgm_theme_id: str | None = None  # AI 導演挑選的場景背景音樂主題 ID

    def to_dict(self):
        return {
            "scene_id": self.scene_id,
            "title": self.title,
            "lines": [line.to_dict() for line in self.lines],
            "bgm_theme_id": self.bgm_theme_id,
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
