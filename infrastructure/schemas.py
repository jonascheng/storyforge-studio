from pydantic import BaseModel, Field


class ScriptLineDTO(BaseModel):
    role: str = Field(description="角色名稱，如「旁白」、「小明」等")
    emotion: str = Field(description="台詞情緒，如「緊張」、「平靜」等")
    text: str = Field(description="台詞文字內容")
    voice_direction_note: str = Field(
        default="",
        description="給 TTS 的聲音導演指示，例如 '[calm, slow]' 或 '[tense, urgent]'",
    )


class BgmThemeDTO(BaseModel):
    name: str = Field(description="中文主題名稱，如「緊張」、「溫馨」等")
    prompt: str = Field(description="給 Lyria 的背景音樂英文描述，純器樂、無人聲")


class BgmMapDTO(BaseModel):
    themes: dict[str, BgmThemeDTO] = Field(
        default_factory=dict,
        description="BGM 主題 ID (如 'tension', 'daily') 對應主題設定的字典",
    )


class VoiceEntryDTO(BaseModel):
    """角色聲音對應表的單一條目，含聲線名稱與固定 Audio Profile 描述。"""

    voice: str = Field(description="聲音演員名稱，如 'Puck'、'Kore'")
    audio_profile: str = Field(
        default="",
        description=(
            "固定的英文角色人格描述，用於 TTS prompt 的 AUDIO PROFILE 區塊。"
            "描述角色身份、原型、年齡、個性等，確保跨場景聲音一致。"
        ),
    )


class SceneDTO(BaseModel):
    scene_id: int = Field(description="場景序號，從 1 開始遞增")
    title: str = Field(description="簡短中文場景標題，約 4-10 個字")
    bgm_theme_id: str | None = Field(
        default=None,
        description="從 BGM 主題表中挑選的 bgm_theme_id；若無需 BGM 則為 null",
    )
    scene_description: str = Field(
        default="",
        description=(
            "場景環境氛圍的英文描述（2-4 句），包含地點、時間、氣氛等細節，"
            "用於引導 TTS 模型的演技表現。"
        ),
    )
    lines: list[ScriptLineDTO] = Field(description="該場景的所有台詞行清單")


class ScreenplayDTO(BaseModel):
    voice_map: dict[str, VoiceEntryDTO] = Field(
        default_factory=dict,
        description=(
            "角色與聲音演員對應表，每個條目包含聲線名稱與固定 Audio Profile 描述。"
            "例如：{'旁白': {'voice': 'Kore', 'audio_profile': 'Calm narrator.'}, "
            "'小明': {'voice': 'Puck', 'audio_profile': 'Young boy, age 8.'}}"
        ),
    )
    scenes: list[SceneDTO] = Field(description="故事拆解後的所有場景清單")


class SafeLinesDTO(BaseModel):
    suggestions: list[str] = Field(description="3 個意思相近但語氣溫和、安全的替代台詞字串清單")
