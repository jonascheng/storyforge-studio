import base64
import io
import json

from google import genai

from core.entities import BgmMap, BgmTheme, Scene, Screenplay, Script, ScriptLine
from core.use_cases import IDirector
from core.voice_catalog import resolve_voice_map
from infrastructure.schemas import BgmMapDTO, SafeLinesDTO, ScreenplayDTO


class GeminiDirector(IDirector):
    DIRECTOR_MODEL = "gemini-3.8-flash"
    TTS_MODEL = "gemini-3.1-flash-tts-preview"

    def __init__(self, api_key: str, thinking_level: str = "MEDIUM"):
        self.api_key = api_key
        self.thinking_level = thinking_level
        self._client = genai.Client(api_key=api_key) if api_key else None

    def _require_key(self):
        if not self.api_key:
            raise ValueError("需要設定 API 通行證才能使用 AI 導演。")

    def _extract_retry_delay(self, err: Exception, default: float = 10.0) -> float:
        import re

        details = getattr(err, "details", None)
        if isinstance(details, dict):
            err_details = details.get("error", {}).get("details", []) or details.get("details", [])
            if isinstance(err_details, list):
                for item in err_details:
                    if isinstance(item, dict) and "retryDelay" in item:
                        delay_str = str(item["retryDelay"]).rstrip("s")
                        try:
                            return float(delay_str)
                        except ValueError:
                            pass

        err_str = str(err)
        m = re.search(r"retry in ([0-9.]+)s", err_str)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass

        m2 = re.search(r'[\'"]retryDelay[\'"]:\s*[\'"]([0-9.]+)s?[\'"]', err_str)
        if m2:
            try:
                return float(m2.group(1))
            except ValueError:
                pass

        return default

    def _is_rate_limit_error(self, err: Exception) -> bool:
        code = getattr(err, "code", None)
        if code == 429:
            return True
        status = getattr(err, "status", None)
        if status == "RESOURCE_EXHAUSTED":
            return True
        err_str = str(err)
        return "429" in err_str or "RESOURCE_EXHAUSTED" in err_str

    def _create_interaction_with_retry(
        self, *args, max_retries: int = 3, max_delay: float = 60.0, **kwargs
    ):
        import time

        self._require_key()
        if "store" not in kwargs:
            kwargs["store"] = False

        last_err = None
        for attempt in range(max_retries + 1):
            try:
                return self._client.interactions.create(*args, **kwargs)
            except Exception as e:
                if not self._is_rate_limit_error(e):
                    raise
                last_err = e
                if attempt < max_retries:
                    delay = self._extract_retry_delay(e, default=10.0 * (attempt + 1))
                    if delay > max_delay:
                        raise RuntimeError(
                            f"AI 今日額度已達上限（需等待一段時間或明天重設，或更換通行證）：{e}"
                        ) from e
                    sleep_sec = delay + 1.0
                    print(
                        f"DEBUG: 遇到 429 額度限制，等待 {sleep_sec:.1f} 秒後自動重試（第 {attempt + 1}/{max_retries} 次）..."
                    )
                    time.sleep(sleep_sec)
                else:
                    break

        raise RuntimeError(f"AI 額度已達每分鐘上限（已自動重試多次）：{last_err}")

    def _call_director_model(self, prompt: str, schema: dict | None = None) -> str:
        self._require_key()
        response_format = None
        if schema:
            response_format = {
                "type": "text",
                "mime_type": "application/json",
                "schema": schema,
            }
        interaction = self._create_interaction_with_retry(
            model=self.DIRECTOR_MODEL,
            input=prompt,
            response_format=response_format,
            generation_config={
                "thinking_level": self.thinking_level.lower(),
            },
            store=False,
        )
        return getattr(interaction, "output_text", "") or ""

    def _clean_json(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    # ── 向後相容舊介面 ────────────────────────────────────────────
    def break_down_script(self, story_text: str) -> Script:
        screenplay = self.break_down_screenplay(story_text)
        all_lines = [line for scene in screenplay.scenes for line in scene.lines]
        return Script(lines=all_lines)

    def generate_audio(self, script: Script, output_path: str) -> None:
        raise NotImplementedError("請改用 generate_scene_audio")

    # ── 新場景介面 ────────────────────────────────────────────────
    def define_bgm_themes(self, story_text: str) -> BgmMap:
        self._require_key()
        prompt = f"""你是一位專業的有聲書配樂指導。請先掃描以下故事原文，定義出 2 到 4 個貫穿全劇的「BGM 主題（BGM Themes）」（例如：日常、緊張、戰鬥、感傷等）。
每個主題需要有一個簡短的英文 ID (theme_id)、一個中文名稱 (name)，以及給 Lyria 音樂生成 AI 的英文描述 (prompt)。
音樂描述要求：純器樂、無人聲、音量漸退，適合做為有聲書墊底配樂。例如："[tension/mood] instrumental, no vocals, subtle and understated as background music for audiobook"。

請嚴格以 JSON 格式回傳，格式範例如下：
{{
  "themes": {{
    "tension": {{
      "name": "緊張",
      "prompt": "Tense, slow orchestral strings, no vocals, subtle and understated as background music for audiobook"
    }},
    "daily": {{
      "name": "日常",
      "prompt": "Light and warm acoustic guitar, no vocals, subtle and understated as background music for audiobook"
    }}
  }}
}}

故事原文：
{story_text}
"""
        raw = self._call_director_model(prompt, schema=BgmMapDTO.model_json_schema())
        text = self._clean_json(raw)
        try:
            dto = BgmMapDTO.model_validate_json(text)
            themes = {k: BgmTheme(name=v.name, prompt=v.prompt) for k, v in dto.themes.items()}
            return BgmMap(themes=themes)
        except Exception as e:
            raise ValueError(f"AI 回傳的 BGM 主題格式有誤: {e}")

    def break_down_screenplay(self, story_text: str, bgm_map: BgmMap | None = None) -> Screenplay:
        self._require_key()

        bgm_themes_str = "無"
        if bgm_map and bgm_map.themes:
            bgm_themes_str = "\n".join(
                f"- ID: {k}, 名稱: {v.name}, 描述: {v.prompt}" for k, v in bgm_map.themes.items()
            )

        prompt = f"""你是一位專業的有聲書導演。請將以下故事拆解為多個「場景」，並為所有出場角色挑選最合適的聲音演員。

聲音演員庫（供角色配音挑選，請依照角色性別挑選相符前綴的演員，每位角色盡量使用不同演員）：
- 童趣活潑：[男] Puck (歡快活潑), [女] Leda (年輕稚嫩), [男] Fenrir (激昂興奮), [男] Zephyr (明亮清爽), [女] Autonoe (明亮靈巧), [女] Laomedeia (節奏輕快), [女] Sadachbia (活力充沛)
- 溫柔親切：[女] Aoede (輕鬆愜意), [女] Callirrhoe (隨和悠閒), [男] Umbriel (柔和放鬆), [男] Achernar (柔和細膩), [女] Achird (親切友善), [女] Vindemiatrix (溫柔慈愛), [女] Sulafat (溫暖醇厚)
- 成熟沉穩：[女] Schedar (平穩勻稱), [男] Charon (資訊知性), [男] Gacrux (成熟穩健), [男] Iapetus (清晰咬字), [女] Erinome (清澈透亮), [男] Algieba (絲滑沉著), [女] Despina (優雅平和), [男] Rasalgethi (知性詳實), [男] Sadaltager (博學多聞), [男] Zubenelgenubi (自然隨意)
- 威嚴粗獷：[中性] Algenib (低沉沙啞怪獸), [男] Orus (威嚴果決), [男] Alnilam (剛正堅毅), [女] Pulcherrima (直接果敢), [男] Enceladus (神秘深邃)
- 說書人（旁白）：固定使用 [中性] Kore

BGM 主題清單（供場景配樂挑選）：
{bgm_themes_str}

每個場景代表一個情節單元（時間地點或情緒基調相對一致），每個場景最多 300 字。
每個場景需要：
1. 一個 scene_id（從 1 開始）
2. 一個簡短的中文場景標題（4-10 個字）
3. 一個 bgm_theme_id（從上方定義好的 BGM 主題清單中挑選最適合此場景的 theme_id）。若場景簡短或無需 BGM，請設為 null。
4. 所有台詞行，每行需有：role（角色名或「旁白」）、emotion（情緒）、text（台詞）、voice_direction_note（給 TTS 的英文聲音導演備註，例如 "[calm, slow]" 或 "speak with a trembling voice"）

請嚴格以 JSON 格式回傳，格式範例如下：
{{
  "voice_map": {{
    "旁白": "Kore",
    "小明": "Puck",
    "怪獸": "Algenib"
  }},
  "scenes": [
    {{
      "scene_id": 1,
      "title": "書房中的爭吵",
      "bgm_theme_id": "tension",
      "lines": [
        {{"role": "旁白", "emotion": "緊張", "text": "門突然被推開", "voice_direction_note": "[tense, urgent]"}},
        {{"role": "小明", "emotion": "憤怒", "text": "你為什麼騙我！", "voice_direction_note": "[angry, raised voice]"}}
      ]
    }}
  ]
}}

故事原文：
{story_text}
"""
        raw = self._call_director_model(prompt, schema=ScreenplayDTO.model_json_schema())
        text = self._clean_json(raw)
        try:
            try:
                dto = ScreenplayDTO.model_validate_json(text)
                raw_scenes = [s.model_dump() for s in dto.scenes]
                raw_voice_map = dto.voice_map
            except Exception:
                data = json.loads(text)
                if isinstance(data, dict):
                    raw_scenes = data.get("scenes", [])
                    raw_voice_map = data.get("voice_map", {})
                elif isinstance(data, list):
                    raw_scenes = data
                    raw_voice_map = {}
                else:
                    raise ValueError("JSON 根元素必須是物件或陣列")

            scenes = []
            role_counts: dict[str, int] = {}
            for item in raw_scenes:
                lines = [ScriptLine(**ln) for ln in item["lines"]]
                for ln in lines:
                    role_counts[ln.role] = role_counts.get(ln.role, 0) + 1
                scenes.append(
                    Scene(
                        scene_id=item["scene_id"],
                        title=item["title"],
                        lines=lines,
                        bgm_theme_id=item.get("bgm_theme_id"),
                    )
                )

            all_roles = list(role_counts.keys())
            voice_map = resolve_voice_map(
                raw_voice_map,
                all_roles,
                narrator_voice="Kore",
                role_line_counts=role_counts,
            )
            return Screenplay(scenes=scenes, voice_map=voice_map)
        except Exception as e:
            raise ValueError(f"AI 導演回傳的格式有誤: {e}")

    def suggest_safe_lines(self, original_text: str) -> list[str]:
        """當台詞被安全審查阻擋時，請 AI 提供 3 個安全的替代台詞。"""
        self._require_key()
        prompt = f"""這句台詞被 TTS 語音模型的安全審查阻擋了：
「{original_text}」

請提供 3 個意思相近，但用語更溫和、絕對安全的替代方案，讓它可以順利通過語音生成。
"""
        raw = self._call_director_model(prompt, schema=SafeLinesDTO.model_json_schema())
        text = self._clean_json(raw)
        try:
            try:
                dto = SafeLinesDTO.model_validate_json(text)
                return dto.suggestions[:3]
            except Exception:
                data = json.loads(text)
                if isinstance(data, dict) and "suggestions" in data:
                    return data["suggestions"][:3]
                if isinstance(data, list) and all(isinstance(s, str) for s in data):
                    return data[:3]
                return []
        except Exception:
            return []

    def generate_scene_bgm(self, bgm_prompt: str, output_path: str) -> str:
        """呼叫 Lyria 3 Clip 生成 30 秒場景背景音樂，存為 MP3，回傳路徑。

        使用 Interactions API。
        bgm_prompt 應為英文器樂描述，包含 no vocals 與情緒風格指示。
        """
        self._require_key()
        LYRIA_MODEL = "lyria-3-clip-preview"

        try:
            interaction = self._create_interaction_with_retry(
                model=LYRIA_MODEL,
                input=bgm_prompt,
                store=False,
            )
            audio = getattr(interaction, "output_audio", None)
            if not audio or not getattr(audio, "data", None):
                raise ValueError("Lyria 未回傳音頻資料")
            audio_bytes = (
                base64.b64decode(audio.data) if isinstance(audio.data, str) else audio.data
            )
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            return output_path
        except Exception as e:
            if "額度" in str(e):
                raise
            raise RuntimeError(f"Lyria BGM 生成失敗（已重試多次）：{e}") from e

    @staticmethod
    def _build_looped_bgm(bgm_segment, target_ms: int, crossfade_ms: int = 1000):
        """BGM 足長工具：若 bgm_segment 不夠 target_ms，用 crossfade 無縭循環拼接直到夠長。"""
        if len(bgm_segment) >= target_ms:
            return bgm_segment[:target_ms]
        result = bgm_segment
        # 保護：crossfade 不能大於單段長度
        cf = min(crossfade_ms, len(bgm_segment) - 1)
        while len(result) < target_ms:
            result = result.append(bgm_segment, crossfade=cf)
        return result[:target_ms]

    def _build_tts_prompt(self, scene: Scene, line: ScriptLine) -> str:
        """根據 Google 官方 TTS 提示指南，組裝結構化 prompt。

        結構：聲音設定檔 → 場景 → 導演附註 → 轉錄稿
        這樣做可以讓 AI 清楚分辨「這是要唸的台詞」而非「有害的對話」，
        大幅降低被安全分類器誤殺的機率。
        """
        notes_parts = []
        if line.emotion:
            notes_parts.append(f"Emotion: {line.emotion}")
        if line.voice_direction_note:
            notes_parts.append(line.voice_direction_note.strip("[]"))

        director_notes = ", ".join(notes_parts)
        style_line = (
            f"Style: {director_notes}"
            if director_notes
            else "Style: Natural, expressive reading for an audiobook."
        )

        return f"""# AUDIO PROFILE: {line.role}
## "{scene.title}"

## THE SCENE: {scene.title}
這是一個有聲書的場景朗讀。請以角色「{line.role}」的身份，自然地朗讀以下轉錄稿。

### DIRECTOR'S NOTES
{style_line}

#### TRANSCRIPT
{line.text}
"""

    def _decode_audio_data(self, audio_data: bytes, mime_type: str):
        from pydub import AudioSegment

        lower_mime = mime_type.lower() if mime_type else ""
        if not lower_mime or "l16" in lower_mime or "pcm" in lower_mime or "raw" in lower_mime:
            rate = 24000
            channels = 1
            for part_str in lower_mime.split(";"):
                part_str = part_str.strip()
                if part_str.startswith("rate="):
                    try:
                        rate = int(part_str.split("=")[1])
                    except ValueError:
                        pass
                elif part_str.startswith("channels="):
                    try:
                        channels = int(part_str.split("=")[1])
                    except ValueError:
                        pass
            return AudioSegment(
                data=audio_data,
                sample_width=2,  # 16-bit
                frame_rate=rate,
                channels=channels,
            )
        else:
            try:
                return AudioSegment.from_file(io.BytesIO(audio_data))
            except Exception as e:
                print(f"DEBUG: from_file failed: {e}. Trying raw PCM fallback.")
                return AudioSegment(
                    data=audio_data,
                    sample_width=2,
                    frame_rate=24000,
                    channels=1,
                )

    def _infer_character_description(self, role: str, group: list[ScriptLine]) -> str:
        """根據角色名稱與台詞提示，推導角色的聲音性格標籤。"""
        notes = []
        for line in group:
            if line.role == role:
                if line.emotion:
                    notes.append(line.emotion)
                if line.voice_direction_note:
                    notes.append(line.voice_direction_note.strip("[]"))
        notes_summary = ", ".join(notes[:3]) if notes else "expressive audiobook voice"

        if role in ["旁白", "說書人"]:
            return f"Calm, steady, and clear third-person audiobook narrator ({notes_summary})"

        if any(k in role for k in ["爸爸", "父親", "叔叔", "伯伯"]):
            return f"Adult male father, warm and deep voice ({notes_summary})"
        if any(k in role for k in ["媽媽", "母親", "阿姨", "姑姑"]):
            return f"Adult female mother, gentle and warm voice ({notes_summary})"
        if any(k in role for k in ["爺爺", "公公", "阿公"]):
            return f"Elderly male grandfather, kind and mature voice ({notes_summary})"
        if any(k in role for k in ["奶奶", "婆婆", "阿嬤", "外婆"]):
            return f"Elderly female grandmother, loving and warm voice ({notes_summary})"
        if any(k in role for k in ["怪獸", "精靈", "幽靈", "魔王"]):
            return f"Playful mythical creature ({notes_summary})"

        combined_notes = " ".join(notes).lower()
        if any(w in combined_notes for w in ["child", "kid", "boy", "girl"]):
            return f"Young child, gentle tone ({notes_summary})"

        return f"Role {role} ({notes_summary})"

    def _group_lines_into_dialogue_groups(
        self,
        lines: list[ScriptLine],
        max_lines: int = 6,
        max_chars: int = 300,
    ) -> list[list[ScriptLine]]:
        """依台詞順序將場景台詞切分為朗讀對話組。

        原則（ADR 0007）：
        1. 消除旁白特例，旁白視為普通角色，與其他角色一同排隊。
        2. 依先後順序貪婪分組，每組最多 2 位不同角色，上限 max_lines 句或 max_chars 字。
        """
        if not lines:
            return []

        groups: list[list[ScriptLine]] = []
        current_group: list[ScriptLine] = []
        current_roles: set[str] = set()
        current_chars: int = 0

        for line in lines:
            if current_group:
                would_be_roles = current_roles | {line.role}
                would_be_chars = current_chars + len(line.text)

                if (
                    len(would_be_roles) > 2
                    or len(current_group) >= max_lines
                    or would_be_chars > max_chars
                ):
                    groups.append(current_group)
                    current_group = [line]
                    current_roles = {line.role}
                    current_chars = len(line.text)
                else:
                    current_group.append(line)
                    current_roles.add(line.role)
                    current_chars += len(line.text)
            else:
                current_group.append(line)
                current_roles.add(line.role)
                current_chars += len(line.text)

        if current_group:
            groups.append(current_group)

        return groups

    def _build_multi_speaker_prompt(
        self,
        scene: Scene,
        group: list[ScriptLine],
        roles: list[str],
    ) -> str:
        """建構多角色合奏朗讀的提示詞，包含場景脈絡與角色特質引導。"""
        char_descriptions = []
        for role in roles:
            desc = self._infer_character_description(role, group)
            char_descriptions.append(f"- {role}: {desc}")

        chars_header = "\n".join(char_descriptions)

        transcript_lines = []
        for line in group:
            notes_parts = []
            if line.emotion:
                notes_parts.append(line.emotion)
            if line.voice_direction_note:
                notes_parts.append(line.voice_direction_note.strip("[]"))
            note_str = f"({', '.join(notes_parts)}) " if notes_parts else ""
            transcript_lines.append(f"{line.role}: {note_str}{line.text}")
        transcript = "\n".join(transcript_lines)

        if "旁白" in roles or "說書人" in roles:
            narrator_role = "旁白" if "旁白" in roles else "說書人"
            other_roles = [r for r in roles if r != narrator_role]
            other_str = other_roles[0] if other_roles else "the characters"
            instructions = (
                f"TTS the following audiobook excerpt. "
                f"{narrator_role} provides calm, clear third-person narration, "
                f"while {other_str} performs dialogue with emotional expression:\n"
            )
        else:
            instructions = f"TTS the following conversation between {roles[0]} and {roles[1]}:\n"

        return (
            f"# AUDIO SCENE: {scene.title}\n"
            f"Characters:\n"
            f"{chars_header}\n\n"
            f"{instructions}"
            f"{transcript}"
        )

    def _generate_single_line_audio(self, scene: Scene, line: ScriptLine, voice_map: dict):
        """單行錄音呼叫。"""
        voice_name = voice_map.get(line.role, "Kore")
        tts_prompt = self._build_tts_prompt(scene, line)
        print("\n" + "=" * 50)
        print("[DEBUG TTS - 單人朗讀 (Interactions API)]")
        print(f"  • 角色: {line.role}")
        print(f"  • speech_config: [{{'voice': '{voice_name}'}}]")
        print(f"  • prompt:\n{tts_prompt.strip()}")
        print("=" * 50 + "\n")

        try:
            interaction = self._create_interaction_with_retry(
                model=self.TTS_MODEL,
                input=tts_prompt,
                response_format={"type": "audio"},
                generation_config={"speech_config": [{"voice": voice_name}]},
                store=False,
            )
        except Exception as e:
            if self._is_rate_limit_error(e) or "額度" in str(e):
                raise
            raise ValueError(f"台詞「{line.text}」遭到 AI 安全審查阻擋 (原因: {e})") from e

        audio = getattr(interaction, "output_audio", None)
        if not audio or not getattr(audio, "data", None):
            reason = "未知原因"
            steps = getattr(interaction, "steps", None) or []
            for step in steps:
                if getattr(step, "error", None):
                    reason = str(step.error)
            raise ValueError(f"台詞「{line.text}」遭到 AI 安全審查阻擋 (原因: {reason})")

        audio_bytes = base64.b64decode(audio.data) if isinstance(audio.data, str) else audio.data
        mime = getattr(audio, "mime_type", None) or "audio/pcm;rate=24000"
        return self._decode_audio_data(audio_bytes, mime)

    def _generate_multi_speaker_group_audio(
        self,
        scene: Scene,
        group: list[ScriptLine],
        voice_map: dict,
    ):
        """雙角色合奏錄音呼叫。"""
        roles = list(dict.fromkeys(line.role for line in group))
        tts_prompt = self._build_multi_speaker_prompt(scene, group, roles)
        v1 = voice_map.get(roles[0], "Kore")
        v2 = voice_map.get(roles[1], "Puck")
        print("\n" + "=" * 50)
        print("[DEBUG TTS - 雙角色合奏 (Interactions API)]")
        print(f"  • 合奏角色: {roles[0]} & {roles[1]}")
        print("  • speech_config:")
        print(f"      - speaker: '{roles[0]}', voice: '{v1}'")
        print(f"      - speaker: '{roles[1]}', voice: '{v2}'")
        print(f"  • prompt:\n{tts_prompt.strip()}")
        print("=" * 50 + "\n")

        try:
            interaction = self._create_interaction_with_retry(
                model=self.TTS_MODEL,
                input=tts_prompt,
                response_format={"type": "audio"},
                generation_config={
                    "speech_config": [
                        {"speaker": roles[0], "voice": v1},
                        {"speaker": roles[1], "voice": v2},
                    ]
                },
                store=False,
            )
        except Exception as e:
            if self._is_rate_limit_error(e) or "額度" in str(e):
                raise
            raise ValueError(f"合奏對話遭到 AI 安全審查阻擋 (原因: {e})") from e

        audio = getattr(interaction, "output_audio", None)
        if not audio or not getattr(audio, "data", None):
            reason = "未知原因"
            steps = getattr(interaction, "steps", None) or []
            for step in steps:
                if getattr(step, "error", None):
                    reason = str(step.error)
            raise ValueError(f"合奏對話遭到 AI 安全審查阻擋 (原因: {reason})")

        audio_bytes = base64.b64decode(audio.data) if isinstance(audio.data, str) else audio.data
        mime = getattr(audio, "mime_type", None) or "audio/pcm;rate=24000"
        return self._decode_audio_data(audio_bytes, mime)

    def _build_single_speaker_group_prompt(
        self,
        scene: Scene,
        group: list[ScriptLine],
        role: str,
    ) -> str:
        """建構單人整組朗讀的提示詞（純旁白或單人獨白批次）。"""
        desc = self._infer_character_description(role, group)
        transcript_lines = []
        for line in group:
            notes_parts = []
            if line.emotion:
                notes_parts.append(line.emotion)
            if line.voice_direction_note:
                notes_parts.append(line.voice_direction_note.strip("[]"))
            note_str = f"({', '.join(notes_parts)}) " if notes_parts else ""
            transcript_lines.append(f"{note_str}{line.text}")
        transcript = "\n".join(transcript_lines)

        return (
            f"# AUDIO SCENE: {scene.title}\n"
            f"Character: {role} ({desc})\n\n"
            f"Please read the following lines aloud with natural intonation and expression:\n"
            f"{transcript}"
        )

    def _generate_single_speaker_group_audio(
        self,
        scene: Scene,
        group: list[ScriptLine],
        voice_map: dict,
    ):
        """單角色整組批次錄音呼叫。"""
        role = group[0].role
        voice_name = voice_map.get(role, "Kore")
        tts_prompt = self._build_single_speaker_group_prompt(scene, group, role)
        print("\n" + "=" * 50)
        print("[DEBUG TTS - 單人整組朗讀 (Interactions API)]")
        print(f"  • 角色: {role} (共 {len(group)} 句)")
        print(f"  • speech_config: [{{'voice': '{voice_name}'}}]")
        print(f"  • prompt:\n{tts_prompt.strip()}")
        print("=" * 50 + "\n")

        try:
            interaction = self._create_interaction_with_retry(
                model=self.TTS_MODEL,
                input=tts_prompt,
                response_format={"type": "audio"},
                generation_config={"speech_config": [{"voice": voice_name}]},
                store=False,
            )
        except Exception as e:
            if self._is_rate_limit_error(e) or "額度" in str(e):
                raise
            raise ValueError(f"整組台詞遭到 AI 安全審查阻擋 (原因: {e})") from e

        audio = getattr(interaction, "output_audio", None)
        if not audio or not getattr(audio, "data", None):
            reason = "未知原因"
            steps = getattr(interaction, "steps", None) or []
            for step in steps:
                if getattr(step, "error", None):
                    reason = str(step.error)
            raise ValueError(f"整組台詞遭到 AI 安全審查阻擋 (原因: {reason})")

        audio_bytes = base64.b64decode(audio.data) if isinstance(audio.data, str) else audio.data
        mime = getattr(audio, "mime_type", None) or "audio/pcm;rate=24000"
        return self._decode_audio_data(audio_bytes, mime)

    def generate_scene_audio(
        self, scene: Scene, voice_map: dict, output_path: str, bgm_map: BgmMap | None = None
    ) -> str:
        """以朗讀對話組為單位生成語音，支援雙角色合奏、單人整組批次與自動降級單人錄音，拼接成場景音檔。

        若 scene.bgm_theme_id 非空且在 bgm_map 中，則載入（或懶加載生成）對應的 BGM 主題音檔，以 -18 dB 恆定墊底混入對白：
        場景開頭 2 秒淡入、結尾 2 秒淡出，對白超過 30 秒則以 1 秒 crossfade 無縭循環。
        """
        self._require_key()
        from pydub import AudioSegment

        combined = AudioSegment.empty()
        groups = self._group_lines_into_dialogue_groups(scene.lines)

        for group in groups:
            group_roles = list(dict.fromkeys(line.role for line in group))
            group_audio = None

            # 若組內恰好為 2 位角色，優先嘗試雙角色合奏朗讀
            if len(group_roles) == 2:
                try:
                    print(
                        f"DEBUG: 嘗試雙角色合奏朗讀 ({group_roles[0]} & {group_roles[1]}, 共 {len(group)} 句)..."
                    )
                    group_audio = self._generate_multi_speaker_group_audio(scene, group, voice_map)
                except Exception as e:
                    print(f"DEBUG: 雙角色合奏失敗 ({e})，自動降級為單人逐行錄音備案...")
                    group_audio = None
            elif len(group_roles) == 1 and len(group) > 1:
                try:
                    print(f"DEBUG: 嘗試單人整組批次朗讀 ({group_roles[0]}, 共 {len(group)} 句)...")
                    group_audio = self._generate_single_speaker_group_audio(scene, group, voice_map)
                except Exception as e:
                    print(f"DEBUG: 單人整組朗讀失敗 ({e})，自動降級為單人逐行錄音備案...")
                    group_audio = None

            # 若不是合奏/整組成功，或只有 1 行，或失敗降級，執行單人逐行錄音
            if group_audio is None:
                group_segment = AudioSegment.empty()
                for line in group:
                    line_audio = self._generate_single_line_audio(scene, line, voice_map)
                    group_segment += line_audio
                group_audio = group_segment

            # 組間加入 300ms 自然呼吸停頓
            if len(combined) > 0:
                combined += AudioSegment.silent(duration=300)

            combined += group_audio

        # ── BGM 混音 ────────────────────────────────────────────────
        if scene.bgm_theme_id and bgm_map and scene.bgm_theme_id in bgm_map.themes:
            import os

            theme = bgm_map.themes[scene.bgm_theme_id]
            bgm_path = os.path.join(
                os.path.dirname(output_path),
                f"theme_{scene.bgm_theme_id}.mp3",
            )
            try:
                if not os.path.exists(bgm_path):
                    print(f"DEBUG: 首次遇到 BGM 主題 '{theme.name}'，呼叫 Lyria 懶加載生成...")
                    self.generate_scene_bgm(theme.prompt, bgm_path)
                else:
                    print(f"DEBUG: 重複使用 BGM 主題 '{theme.name}'...")

                raw_bgm = AudioSegment.from_mp3(bgm_path)

                BGM_DB = -18  # BGM 混入音量（對白永遠主導）
                FADE_IN_MS = 2000  # 淡入
                FADE_OUT_MS = 2000  # 淡出
                CROSSFADE_MS = 1000  # crossfade loop 接縭

                dialogue_ms = len(combined)

                # 1. 建立足夠長的 BGM 軌道
                bgm_track = self._build_looped_bgm(raw_bgm, dialogue_ms, CROSSFADE_MS)

                # 2. 整體壓低 -18 dB + 淡入淡出
                bgm_track = (bgm_track + BGM_DB).fade_in(FADE_IN_MS).fade_out(FADE_OUT_MS)

                # 3. 對齊長度（BGM 軌道與對白同長）
                max_len = max(len(bgm_track), dialogue_ms)
                bgm_track = bgm_track + AudioSegment.silent(duration=max_len - len(bgm_track))
                dialogue_padded = combined + AudioSegment.silent(duration=max_len - dialogue_ms)

                # 4. overlay：BGM 墊底，對白在上
                final_audio = bgm_track.overlay(dialogue_padded)
                print(
                    f"DEBUG: BGM 混音完成（BGM {BGM_DB} dB，總長 {len(final_audio) / 1000:.1f} 秒）"
                )
            except Exception as e:
                print(f"DEBUG: BGM 生成失敗（{e}），跳過 BGM，僅輸出對白")
                final_audio = combined
        else:
            final_audio = combined

        final_audio.export(output_path, format="mp3")
        return output_path
