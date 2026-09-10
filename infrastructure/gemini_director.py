import json
import io
from google import genai
from google.genai import types
from core.entities import Script, ScriptLine, Scene, Screenplay
from core.use_cases import IDirector


class GeminiDirector(IDirector):
    DIRECTOR_MODEL = "gemini-3.8-flash"
    TTS_MODEL = "gemini-3.1-flash-tts-preview"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = genai.Client(api_key=api_key) if api_key else None

    def _require_key(self):
        if not self.api_key:
            raise ValueError("需要設定 API 通行證才能使用 AI 導演。")

    def _call_director_model(self, prompt: str) -> str:
        self._require_key()
        response = self._client.models.generate_content(
            model=self.DIRECTOR_MODEL,
            contents=prompt,
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

    def generate_scene_audio(self, scene: Scene, voice_map: dict, output_path: str) -> str:
        """逐行呼叫 TTS，拼接成場景音檔，寫入 output_path，回傳路徑。"""
        self._require_key()
        from pydub import AudioSegment

        combined = AudioSegment.empty()

        for line in scene.lines:
            voice_name = voice_map.get(line.role, "Kore")
            tts_prompt = f"{line.voice_direction_note} {line.text}".strip()

            response = self._client.models.generate_content(
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

            audio_data = response.candidates[0].content.parts[0].inline_data.data
            segment = AudioSegment.from_file(io.BytesIO(audio_data), format="wav")
            combined += segment

        combined.export(output_path, format="mp3")
        return output_path
