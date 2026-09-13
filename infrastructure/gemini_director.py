import json
import io
from google import genai
from google.genai import types
from core.entities import Script, ScriptLine, Scene, Screenplay
from core.use_cases import IDirector


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
        m = re.search(r'retry in ([0-9.]+)s', err_str)
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

    def _generate_content_with_retry(self, *args, max_retries: int = 3, **kwargs):
        import time
        self._require_key()
        last_err = None
        for attempt in range(max_retries + 1):
            try:
                return self._client.models.generate_content(*args, **kwargs)
            except Exception as e:
                if not self._is_rate_limit_error(e):
                    raise
                last_err = e
                if attempt < max_retries:
                    delay = self._extract_retry_delay(e, default=10.0 * (attempt + 1))
                    sleep_sec = delay + 1.0
                    print(f"DEBUG: 遇到 429 額度限制，等待 {sleep_sec:.1f} 秒後自動重試（第 {attempt + 1}/{max_retries} 次）...")
                    time.sleep(sleep_sec)
                else:
                    break

        raise RuntimeError(f"AI 額度已達每分鐘上限（已自動重試多次）：{last_err}")

    def _call_director_model(self, prompt: str) -> str:
        self._require_key()
        response = self._generate_content_with_retry(
            model=self.DIRECTOR_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_level=self.thinking_level
                )
            )
        )
        return response.text

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
    def break_down_screenplay(self, story_text: str) -> Screenplay:
        self._require_key()
        prompt = f"""你是一位專業的有聲書導演。請將以下故事拆解為多個「場景」。

每個場景代表一個情節單元（時間地點或情緒基調相對一致），每個場景最多 300 字。
每個場景需要：
1. 一個 scene_id（從 1 開始）
2. 一個簡短的中文場景標題（4-10 個字）
3. 所有台詞行，每行需有：role（角色名或「旁白」）、emotion（情緒）、text（台詞）、voice_direction_note（給 TTS 的英文聲音導演備註，例如 "[calm, slow]" 或 "speak with a trembling voice"）

請嚴格以 JSON 陣列格式回傳，例如：
[
  {{
    "scene_id": 1,
    "title": "書房中的爭吵",
    "lines": [
      {{"role": "旁白", "emotion": "緊張", "text": "門突然被推開", "voice_direction_note": "[tense, urgent]"}},
      {{"role": "小明", "emotion": "憤怒", "text": "你為什麼騙我！", "voice_direction_note": "[angry, raised voice]"}}
    ]
  }}
]

故事原文：
{story_text}
"""
        raw = self._call_director_model(prompt)
        text = self._clean_json(raw)
        try:
            data = json.loads(text)
            scenes = []
            for item in data:
                lines = [ScriptLine(**ln) for ln in item["lines"]]
                scenes.append(Scene(
                    scene_id=item["scene_id"],
                    title=item["title"],
                    lines=lines,
                ))
            return Screenplay(scenes=scenes)
        except Exception as e:
            raise ValueError(f"AI 導演回傳的格式有誤: {e}")

    def suggest_safe_lines(self, original_text: str) -> list[str]:
        """當台詞被安全審查阻擋時，請 AI 提供 3 個安全的替代台詞。"""
        self._require_key()
        prompt = f"""這句台詞被 TTS 語音模型的安全審查阻擋了：
「{original_text}」

請提供 3 個意思相近，但用語更溫和、絕對安全的替代方案，讓它可以順利通過語音生成。
請直接以 JSON 陣列的格式回傳這 3 個字串，例如：
["安全替代句一", "安全替代句二", "安全替代句三"]
"""
        raw = self._call_director_model(prompt)
        text = self._clean_json(raw)
        try:
            suggestions = json.loads(text)
            if isinstance(suggestions, list) and all(isinstance(s, str) for s in suggestions):
                return suggestions[:3]
            return []
        except Exception:
            return []

    def _build_tts_prompt(self, scene: Scene, line) -> str:
        """根據 Google 官方 TTS 提示指南，組裝結構化 prompt。
        
        結構：聲音設定檔 → 場景 → 導演附註 → 轉錄稿
        這樣做可以讓 AI 清楚分辨「這是要唸的台詞」而非「有害的對話」，
        大幅降低被安全分類器誤殺的機率。
        """
        director_notes = line.voice_direction_note.strip() if line.voice_direction_note else ""
        style_line = f"Style: {director_notes}" if director_notes else "Style: Natural, expressive reading for an audiobook."

        return f"""# AUDIO PROFILE: {line.role}
## "{scene.title}"

## THE SCENE: {scene.title}
這是一個有聲書的場景朗讀。請以角色「{line.role}」的身份，自然地朗讀以下轉錄稿。

### DIRECTOR'S NOTES
{style_line}

#### TRANSCRIPT
{line.text}
"""

    def generate_scene_audio(self, scene: Scene, voice_map: dict, output_path: str) -> str:
        """逐行呼叫 TTS，拼接成場景音檔，寫入 output_path，回傳路徑。"""
        self._require_key()
        from pydub import AudioSegment

        combined = AudioSegment.empty()

        for line in scene.lines:
            voice_name = voice_map.get(line.role, "Kore")

            # 根據 Google 官方 TTS 提示指南，使用結構化 prompt
            # 避免短句被安全分類器誤判為有害內容
            tts_prompt = self._build_tts_prompt(scene, line)

            response = self._generate_content_with_retry(
                model=self.TTS_MODEL,
                contents=tts_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name,
                            )
                        )
                    ),
                ),
            )

            if not response.candidates:
                reason = "未知原因"
                if response.prompt_feedback and hasattr(response.prompt_feedback, "block_reason"):
                    reason = str(getattr(response.prompt_feedback.block_reason, "name", response.prompt_feedback.block_reason))
                raise ValueError(f"台詞「{line.text}」遭到 AI 安全審查阻擋 (原因: {reason})")

            part = response.candidates[0].content.parts[0].inline_data
            audio_data = part.data
            mime_type = part.mime_type or ""

            print(f"DEBUG: TTS line: '{line.text}'")
            print(f"DEBUG: TTS returned mime_type: '{mime_type}', data length: {len(audio_data)} bytes")

            # 預設為 raw PCM，如果沒有給 mime_type 或者是 pcm/L16
            if not mime_type or "L16" in mime_type or "pcm" in mime_type.lower() or "raw" in mime_type.lower():
                print("DEBUG: Processing as raw 16-bit PCM (24000Hz)")
                rate = 24000
                for part_str in mime_type.split(";"):
                    part_str = part_str.strip()
                    if part_str.lower().startswith("rate="):
                        try:
                            rate = int(part_str.split("=")[1])
                        except ValueError:
                            pass
                segment = AudioSegment(
                    data=audio_data,
                    sample_width=2,   # 16-bit
                    frame_rate=rate,
                    channels=1,
                )
            else:
                print(f"DEBUG: Processing as {mime_type} via from_file")
                try:
                    segment = AudioSegment.from_file(io.BytesIO(audio_data))
                except Exception as e:
                    print(f"DEBUG: from_file failed: {e}. Trying raw PCM fallback.")
                    segment = AudioSegment(
                        data=audio_data,
                        sample_width=2,
                        frame_rate=24000,
                        channels=1,
                    )

            combined += segment

        combined.export(output_path, format="mp3")
        return output_path
