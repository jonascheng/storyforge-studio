from pydantic import BaseModel, Field


class ScriptLineDTO(BaseModel):
    role: str = Field(description="角色名稱，如「旁白」、「小明」等")
    emotion: str = Field(description="台詞情緒，如「緊張」、「平靜」等")
    text: str = Field(description="台詞文字內容")
    voice_direction_note: str = Field(
        default="",
        description="給 TTS 的聲音導演指示，例如 '[calm, slow]' 或 '[tense, urgent]'",
    )


class SceneDTO(BaseModel):
    scene_id: int = Field(description="場景序號，從 1 開始遞增")
    title: str = Field(description="簡短中文場景標題，約 4-10 個字")
    bgm_prompt: str | None = Field(
        default=None,
        description="給 Lyria 的場景背景音樂英文描述，純器樂、無人聲；若無需 BGM 則為 null",
    )
    lines: list[ScriptLineDTO] = Field(description="該場景的所有台詞行清單")


class ScreenplayDTO(BaseModel):
    voice_map: dict[str, str] = Field(
        default_factory=dict,
        description="角色與聲音演員對應表，例如 {'旁白': 'Kore', '小明': 'Puck'}",
    )
    scenes: list[SceneDTO] = Field(description="故事拆解後的所有場景清單")


class SafeLinesDTO(BaseModel):
    suggestions: list[str] = Field(description="3 個意思相近但語氣溫和、安全的替代台詞字串清單")
