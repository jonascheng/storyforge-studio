# StoryForge Scene Pipeline 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將 StoryForge 從「整篇一次 TTS」升級為「場景為單位、可局部重生成」的語音產出流程。

**Architecture:** AI 導演在劇本拆解時同時切分場景並為每行台詞寫聲音導演備註。每行台詞單獨呼叫 TTS，每個場景的音檔立刻存磁碟。使用者可只重跑修改過的場景，最後用 pydub 拼接成成品。

**Tech Stack:** Python 3.14, `google.genai`（新版 SDK）, `gemini-3.8-flash`（劇本拆解）, `gemini-3.1-flash-tts-preview`（語音生成）, `pydub`（音檔拼接）, `pywebview`（桌面視窗）

## Global Constraints

- 所有程式碼使用 Python 3.14
- SDK 只用 `google.genai`，禁止 `google.generativeai`（已棄用）
- 測試用 `pytest`，執行指令 `uv run pytest`
- 新增套件用 `uv add <package>`
- 場景音檔存路徑：`~/Documents/StoryForge/<故事名稱>/scene_NN.mp3`
- 角色聲音對應表存路徑：`~/Documents/StoryForge/<故事名稱>/voice_map.json`
- 每行台詞單獨呼叫 TTS（不批次合併）
- 重生成直接覆蓋舊音檔，不保留備份
- 音檔拼接用 `pydub`（不用 ffmpeg）

---

### Task 1: 新增 Scene 相關 Entity，並更新現有 Entity

**Files:**
- Modify: `core/entities.py`
- Modify: `tests/test_core.py`

**Interfaces:**
- Produces:
  - `ScriptLine(role: str, emotion: str, text: str, voice_direction_note: str)`
  - `Scene(scene_id: int, title: str, lines: List[ScriptLine])`
  - `Screenplay(scenes: List[Scene])` — 取代舊的 `Script`
  - `Scene.audio_path: Optional[str]` — 該場景音檔的磁碟路徑，尚未生成時為 `None`

- [ ] **Step 1: 寫失敗的測試**

```python
# tests/test_core.py 新增（保留既有測試不刪）

from core.entities import ScriptLine, Scene, Screenplay


def test_script_line_has_voice_direction_note():
    line = ScriptLine(
        role="旁白", emotion="平靜", text="從前從前...", voice_direction_note="[calm, slow]"
    )
    assert line.voice_direction_note == "[calm, slow]"


def test_scene_creation():
    line = ScriptLine(
        role="旁白", emotion="平靜", text="從前從前...", voice_direction_note="[calm]"
    )
    scene = Scene(scene_id=1, title="開場白", lines=[line])
    assert scene.scene_id == 1
    assert scene.title == "開場白"
    assert len(scene.lines) == 1
    assert scene.audio_path is None


def test_scene_to_dict():
    line = ScriptLine(role="小明", emotion="開心", text="你好！", voice_direction_note="[cheerful]")
    scene = Scene(scene_id=2, title="相遇", lines=[line])
    data = scene.to_dict()
    assert data["scene_id"] == 2
    assert data["title"] == "相遇"
    assert data["lines"][0]["voice_direction_note"] == "[cheerful]"
    assert data["audio_path"] is None


def test_screenplay_creation():
    line = ScriptLine(role="旁白", emotion="平靜", text="結束。", voice_direction_note="[calm]")
    scene = Scene(scene_id=1, title="結局", lines=[line])
    screenplay = Screenplay(scenes=[scene])
    assert len(screenplay.scenes) == 1


def test_screenplay_to_dict():
    line = ScriptLine(role="旁白", emotion="平靜", text="結束。", voice_direction_note="[calm]")
    scene = Scene(scene_id=1, title="結局", lines=[line])
    screenplay = Screenplay(scenes=[scene])
    data = screenplay.to_dict()
    assert len(data["scenes"]) == 1
    assert data["scenes"][0]["title"] == "結局"
```

- [ ] **Step 2: 跑測試，確認失敗**

```bash
uv run pytest tests/test_core.py -v -k "voice_direction or scene or screenplay"
```

預期：`ImportError: cannot import name 'Scene' from 'core.entities'`

- [ ] **Step 3: 實作新 Entity**

將 `core/entities.py` 全部替換為：

```python
from dataclasses import dataclass, asdict, field
from typing import List, Optional


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
    lines: List[ScriptLine]
    audio_path: Optional[str] = None

    def to_dict(self):
        return {
            "scene_id": self.scene_id,
            "title": self.title,
            "lines": [line.to_dict() for line in self.lines],
            "audio_path": self.audio_path,
        }


@dataclass
class Screenplay:
    scenes: List[Scene]

    def to_dict(self):
        return {"scenes": [scene.to_dict() for scene in self.scenes]}


# 向後相容 — 舊 Script 仍可用，指向 Screenplay
@dataclass
class Script:
    lines: List[ScriptLine]

    def to_dict(self):
        return {"lines": [asdict(line) for line in self.lines]}
```

- [ ] **Step 4: 跑全部測試，確認全過**

```bash
uv run pytest tests/ -v
```

預期：全部 PASS（含既有的 `test_script_*` 測試）

- [ ] **Step 5: Commit**

```bash
git add core/entities.py tests/test_core.py
git commit -m "feat: add Scene and Screenplay entities with voice_direction_note"
```

---

### Task 2: 更新 IDirector 協議，新增場景拆解與逐行語音生成介面

**Files:**
- Modify: `core/use_cases.py`
- Modify: `tests/test_use_cases.py`

**Interfaces:**
- Consumes: `Screenplay`, `Scene`, `ScriptLine` from Task 1
- Produces:
  - `IDirector.break_down_screenplay(story_text: str) -> Screenplay`
  - `IDirector.generate_scene_audio(scene: Scene, voice_map: dict, output_path: str) -> str` — 回傳實際寫入的路徑
  - `StoryProcessor.break_down_screenplay(story_text: str) -> Screenplay`
  - `StoryProcessor.generate_scene_audio(scene: Scene, voice_map: dict, output_path: str) -> str`

- [ ] **Step 1: 寫失敗的測試**

```python
# tests/test_use_cases.py 新增（保留既有測試）

from core.entities import Screenplay, Scene, ScriptLine
from core.use_cases import StoryProcessor


class MockDirectorV2:
    def break_down_script(self, story_text: str):
        from core.entities import Script

        return Script(
            lines=[
                ScriptLine(
                    role="旁白", emotion="平靜", text="這是一個測試故事。", voice_direction_note=""
                )
            ]
        )

    def break_down_screenplay(self, story_text: str) -> Screenplay:
        line = ScriptLine(role="旁白", emotion="平靜", text="測試。", voice_direction_note="[calm]")
        scene = Scene(scene_id=1, title="開場", lines=[line])
        return Screenplay(scenes=[scene])

    def generate_audio(self, script, output_path: str) -> None:
        pass

    def generate_scene_audio(self, scene: Scene, voice_map: dict, output_path: str) -> str:
        return output_path


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
```

- [ ] **Step 2: 跑測試，確認失敗**

```bash
uv run pytest tests/test_use_cases.py -v -k "screenplay or scene_audio"
```

預期：`AttributeError: 'StoryProcessor' object has no attribute 'break_down_screenplay'`

- [ ] **Step 3: 更新 use_cases.py**

```python
from typing import Protocol
from core.entities import Script, Screenplay, Scene


class IDirector(Protocol):
    def break_down_script(self, story_text: str) -> Script: ...

    def break_down_screenplay(self, story_text: str) -> Screenplay: ...

    def generate_audio(self, script: Script, output_path: str) -> None: ...

    def generate_scene_audio(self, scene: Scene, voice_map: dict, output_path: str) -> str: ...


class IStorage(Protocol):
    def save_api_key(self, key: str) -> None: ...

    def get_api_key(self) -> str: ...


class StoryProcessor:
    def __init__(self, director: IDirector, storage: IStorage):
        self.director = director
        self.storage = storage

    def break_down(self, story_text: str) -> Script:
        return self.director.break_down_script(story_text)

    def break_down_screenplay(self, story_text: str) -> Screenplay:
        return self.director.break_down_screenplay(story_text)

    def generate_audio(self, script: Script, output_path: str) -> None:
        self.director.generate_audio(script, output_path)

    def generate_scene_audio(self, scene: Scene, voice_map: dict, output_path: str) -> str:
        return self.director.generate_scene_audio(scene, voice_map, output_path)

    def save_key(self, key: str) -> None:
        self.storage.save_api_key(key)

    def get_key(self) -> str:
        return self.storage.get_api_key()
```

- [ ] **Step 4: 跑全部測試**

```bash
uv run pytest tests/ -v
```

預期：全部 PASS

- [ ] **Step 5: Commit**

```bash
git add core/use_cases.py tests/test_use_cases.py
git commit -m "feat: extend IDirector and StoryProcessor with scene-based methods"
```

---

### Task 3: 實作 VoiceMapStorage（角色聲音對應表讀寫）

**Files:**
- Create: `infrastructure/voice_map_storage.py`
- Create: `tests/test_voice_map_storage.py`

**Interfaces:**
- Produces:
  - `VoiceMapStorage(story_folder: str)`
  - `VoiceMapStorage.load() -> dict`  — 例：`{"旁白": "Kore", "小明": "Charon"}`
  - `VoiceMapStorage.save(voice_map: dict) -> None`

- [ ] **Step 1: 寫失敗的測試**

```python
# tests/test_voice_map_storage.py

import os
import tempfile
import pytest
from infrastructure.voice_map_storage import VoiceMapStorage


def test_load_returns_empty_when_no_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = VoiceMapStorage(story_folder=tmpdir)
        assert storage.load() == {}


def test_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = VoiceMapStorage(story_folder=tmpdir)
        vm = {"旁白": "Kore", "小明": "Charon"}
        storage.save(vm)
        loaded = storage.load()
        assert loaded == vm


def test_save_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = VoiceMapStorage(story_folder=tmpdir)
        storage.save({"旁白": "Kore"})
        assert os.path.exists(os.path.join(tmpdir, "voice_map.json"))
```

- [ ] **Step 2: 跑測試，確認失敗**

```bash
uv run pytest tests/test_voice_map_storage.py -v
```

預期：`ModuleNotFoundError: No module named 'infrastructure.voice_map_storage'`

- [ ] **Step 3: 實作**

```python
# infrastructure/voice_map_storage.py

import os
import json


class VoiceMapStorage:
    def __init__(self, story_folder: str):
        self.path = os.path.join(story_folder, "voice_map.json")

    def load(self) -> dict:
        if not os.path.exists(self.path):
            return {}
        with open(self.path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

    def save(self, voice_map: dict) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(voice_map, f, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: 跑測試**

```bash
uv run pytest tests/test_voice_map_storage.py -v
```

預期：全部 PASS

- [ ] **Step 5: Commit**

```bash
git add infrastructure/voice_map_storage.py tests/test_voice_map_storage.py
git commit -m "feat: add VoiceMapStorage for per-story voice assignments"
```

---

### Task 4: 升級 GeminiDirector — SDK 換新版 + 實作 break_down_screenplay

**Files:**
- Modify: `infrastructure/gemini_director.py`
- Create: `tests/test_gemini_director_unit.py`

**Interfaces:**
- Consumes: `Screenplay`, `Scene`, `ScriptLine` from Task 1
- Produces:
  - `GeminiDirector.break_down_screenplay(story_text: str) -> Screenplay` — 呼叫 `gemini-3.8-flash`，回傳場景清單（含標題、台詞行、聲音導演備註）

> **注意**：這個 Task 的測試 mock 掉 Gemini API（不真的打 API），驗證 JSON 解析與 Entity 組裝邏輯。

- [ ] **Step 1: 安裝新版 SDK**

```bash
uv add google-genai
```

- [ ] **Step 2: 寫失敗的測試（mock API 回應）**

```python
# tests/test_gemini_director_unit.py

import json
import pytest
from unittest.mock import MagicMock, patch
from infrastructure.gemini_director import GeminiDirector

FAKE_SCREENPLAY_JSON = json.dumps(
    [
        {
            "scene_id": 1,
            "title": "開場",
            "lines": [
                {
                    "role": "旁白",
                    "emotion": "平靜",
                    "text": "從前從前...",
                    "voice_direction_note": "[calm, slow]",
                },
                {
                    "role": "小明",
                    "emotion": "開心",
                    "text": "你好！",
                    "voice_direction_note": "[cheerful]",
                },
            ],
        },
        {
            "scene_id": 2,
            "title": "衝突",
            "lines": [
                {
                    "role": "旁白",
                    "emotion": "緊張",
                    "text": "突然...",
                    "voice_direction_note": "[tense]",
                }
            ],
        },
    ]
)


def test_break_down_screenplay_parses_json():
    director = GeminiDirector(api_key="fake-key")
    mock_response = MagicMock()
    mock_response.text = FAKE_SCREENPLAY_JSON

    with patch.object(director, "_call_director_model", return_value=mock_response.text):
        screenplay = director.break_down_screenplay("隨便一個故事")

    assert len(screenplay.scenes) == 2
    assert screenplay.scenes[0].title == "開場"
    assert screenplay.scenes[1].title == "衝突"
    assert screenplay.scenes[0].lines[1].voice_direction_note == "[cheerful]"


def test_break_down_screenplay_strips_markdown_fences():
    director = GeminiDirector(api_key="fake-key")
    fenced = f"```json\n{FAKE_SCREENPLAY_JSON}\n```"

    with patch.object(director, "_call_director_model", return_value=fenced):
        screenplay = director.break_down_screenplay("故事")

    assert len(screenplay.scenes) == 2


def test_break_down_screenplay_raises_on_bad_json():
    director = GeminiDirector(api_key="fake-key")

    with patch.object(director, "_call_director_model", return_value="not json at all"):
        with pytest.raises(ValueError, match="AI 導演回傳的格式有誤"):
            director.break_down_screenplay("故事")


def test_requires_api_key():
    director = GeminiDirector(api_key="")
    with pytest.raises(ValueError, match="API 通行證"):
        director.break_down_screenplay("故事")
```

- [ ] **Step 3: 跑測試，確認失敗**

```bash
uv run pytest tests/test_gemini_director_unit.py -v
```

預期：`ImportError` 或 `AttributeError`（`_call_director_model` 不存在）

- [ ] **Step 4: 重寫 gemini_director.py**

```python
# infrastructure/gemini_director.py

import json
from google import genai
from google.genai import types
from core.entities import Script, ScriptLine, Scene, Screenplay
from core.use_cases import IDirector


class GeminiDirector(IDirector):
    DIRECTOR_MODEL = "gemini-3.8-flash"
    TTS_MODEL = "gemini-3.1-flash-tts-preview"

    def __init__(self, api_key: str):
        self.api_key = api_key
        if self.api_key:
            self._client = genai.Client(api_key=self.api_key)
        else:
            self._client = None

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

    # ── 舊介面（向後相容）────────────────────────────────────────
    def break_down_script(self, story_text: str) -> Script:
        screenplay = self.break_down_screenplay(story_text)
        all_lines = [line for scene in screenplay.scenes for line in scene.lines]
        return Script(lines=all_lines)

    def generate_audio(self, script: Script, output_path: str) -> None:
        # 舊介面保留，簡單串接新介面
        raise NotImplementedError("請改用 generate_scene_audio")

    # ── 新介面 ───────────────────────────────────────────────────
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
                scenes.append(
                    Scene(
                        scene_id=item["scene_id"],
                        title=item["title"],
                        lines=lines,
                    )
                )
            return Screenplay(scenes=scenes)
        except Exception as e:
            raise ValueError(f"AI 導演回傳的格式有誤: {e}")

    def generate_scene_audio(self, scene: Scene, voice_map: dict, output_path: str) -> str:
        """逐行呼叫 TTS，拼接成場景音檔，寫入 output_path，回傳路徑。"""
        self._require_key()
        from pydub import AudioSegment
        import io

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
```

- [ ] **Step 5: 跑測試**

```bash
uv run pytest tests/test_gemini_director_unit.py tests/ -v
```

預期：全部 PASS

- [ ] **Step 6: Commit**

```bash
git add infrastructure/gemini_director.py tests/test_gemini_director_unit.py
git commit -m "feat: migrate to google.genai SDK and implement scene-based breakdown + TTS"
```

---

### Task 5: 實作 StoryFolderStorage（故事資料夾管理）

**Files:**
- Create: `infrastructure/story_folder_storage.py`
- Create: `tests/test_story_folder_storage.py`

**Interfaces:**
- Produces:
  - `StoryFolderStorage(story_name: str)`
  - `StoryFolderStorage.folder_path: str` — `~/Documents/StoryForge/<story_name>/`
  - `StoryFolderStorage.scene_audio_path(scene_id: int) -> str` — e.g. `…/scene_01.mp3`
  - `StoryFolderStorage.final_audio_path() -> str` — `…/final_output.mp3`
  - `StoryFolderStorage.ensure_folder() -> None`

- [ ] **Step 1: 寫失敗的測試**

```python
# tests/test_story_folder_storage.py

import os
import tempfile
import pytest
from unittest.mock import patch
from infrastructure.story_folder_storage import StoryFolderStorage


def test_folder_path_is_in_documents():
    storage = StoryFolderStorage("小王子")
    assert storage.folder_path.endswith(os.path.join("StoryForge", "小王子"))


def test_scene_audio_path_format():
    storage = StoryFolderStorage("小王子")
    path = storage.scene_audio_path(3)
    assert path.endswith("scene_03.mp3")


def test_final_audio_path():
    storage = StoryFolderStorage("小王子")
    assert storage.final_audio_path().endswith("final_output.mp3")


def test_ensure_folder_creates_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_base = os.path.join(tmpdir, "StoryForge")
        with patch("infrastructure.story_folder_storage.BASE_DIR", fake_base):
            storage = StoryFolderStorage("測試故事")
            storage.ensure_folder()
            assert os.path.isdir(storage.folder_path)
```

- [ ] **Step 2: 跑測試，確認失敗**

```bash
uv run pytest tests/test_story_folder_storage.py -v
```

預期：`ModuleNotFoundError`

- [ ] **Step 3: 實作**

```python
# infrastructure/story_folder_storage.py

import os

BASE_DIR = os.path.join(os.path.expanduser("~"), "Documents", "StoryForge")


class StoryFolderStorage:
    def __init__(self, story_name: str):
        self.story_name = story_name
        self.folder_path = os.path.join(BASE_DIR, story_name)

    def ensure_folder(self) -> None:
        os.makedirs(self.folder_path, exist_ok=True)

    def scene_audio_path(self, scene_id: int) -> str:
        return os.path.join(self.folder_path, f"scene_{scene_id:02d}.mp3")

    def final_audio_path(self) -> str:
        return os.path.join(self.folder_path, "final_output.mp3")
```

- [ ] **Step 4: 跑測試**

```bash
uv run pytest tests/test_story_folder_storage.py -v
```

預期：全部 PASS

- [ ] **Step 5: Commit**

```bash
git add infrastructure/story_folder_storage.py tests/test_story_folder_storage.py
git commit -m "feat: add StoryFolderStorage for scene/final audio path management"
```

---

### Task 6: 實作 AudioMixer（pydub 拼接場景音檔）

**Files:**
- Create: `infrastructure/audio_mixer.py`
- Create: `tests/test_audio_mixer.py`

**Interfaces:**
- Consumes: `pydub.AudioSegment`
- Produces:
  - `AudioMixer.mix(scene_audio_paths: List[str], output_path: str) -> str`

- [ ] **Step 1: 安裝 pydub**

```bash
uv add pydub
```

- [ ] **Step 2: 寫失敗的測試**

```python
# tests/test_audio_mixer.py

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from infrastructure.audio_mixer import AudioMixer


def test_mix_concatenates_files(tmp_path):
    """測試 mix() 呼叫 pydub 進行拼接並輸出到正確路徑"""
    scene_paths = [str(tmp_path / "scene_01.mp3"), str(tmp_path / "scene_02.mp3")]
    output_path = str(tmp_path / "final_output.mp3")

    mock_segment = MagicMock()
    mock_segment.__add__ = MagicMock(return_value=mock_segment)
    mock_segment.export = MagicMock()

    with patch("infrastructure.audio_mixer.AudioSegment") as MockAudio:
        MockAudio.empty.return_value = mock_segment
        MockAudio.from_mp3.return_value = mock_segment

        result = AudioMixer.mix(scene_paths, output_path)

    assert result == output_path
    mock_segment.export.assert_called_once_with(output_path, format="mp3")


def test_mix_raises_if_no_scenes(tmp_path):
    with pytest.raises(ValueError, match="至少需要一個場景"):
        AudioMixer.mix([], str(tmp_path / "out.mp3"))
```

- [ ] **Step 3: 跑測試，確認失敗**

```bash
uv run pytest tests/test_audio_mixer.py -v
```

預期：`ModuleNotFoundError`

- [ ] **Step 4: 實作**

```python
# infrastructure/audio_mixer.py

from typing import List
from pydub import AudioSegment


class AudioMixer:
    @staticmethod
    def mix(scene_audio_paths: List[str], output_path: str) -> str:
        if not scene_audio_paths:
            raise ValueError("至少需要一個場景才能拼接。")

        combined = AudioSegment.empty()
        for path in scene_audio_paths:
            segment = AudioSegment.from_mp3(path)
            combined += segment

        combined.export(output_path, format="mp3")
        return output_path
```

- [ ] **Step 5: 跑測試**

```bash
uv run pytest tests/test_audio_mixer.py -v
```

預期：全部 PASS

- [ ] **Step 6: Commit**

```bash
git add infrastructure/audio_mixer.py tests/test_audio_mixer.py
git commit -m "feat: add AudioMixer for scene-to-final concatenation via pydub"
```

---

### Task 7: 更新 StoryForgeApi（主程式串接新流程）

**Files:**
- Modify: `main.py`

**Interfaces:**
- Consumes: `GeminiDirector`, `StoryFolderStorage`, `VoiceMapStorage`, `AudioMixer` from Tasks 3-6
- Produces（UI 可呼叫的方法）：
  - `StoryForgeApi.break_down_story(text: str, story_name: str) -> dict` — 回傳 `{"scenes": [...]}`
  - `StoryForgeApi.generate_scene_audio(scene_id: int, story_name: str) -> dict` — 回傳 `{"status": "ok", "path": "..."}`
  - `StoryForgeApi.mix_final_audio(story_name: str) -> dict` — 回傳 `{"status": "ok", "path": "..."}`
  - `StoryForgeApi.delete_scene(scene_id: int, story_name: str) -> dict`
  - `StoryForgeApi.update_voice_map(story_name: str, voice_map: dict) -> dict`

> 此 Task 無需新增測試（UI 整合層，邏輯已在各 Task 測過）。手動驗證見 Verification 節。

- [ ] **Step 1: 重寫 main.py**

```python
# main.py

import os
import webview
from core.use_cases import StoryProcessor
from core.entities import Script, ScriptLine, Scene, Screenplay
from infrastructure.gemini_director import GeminiDirector
from infrastructure.file_storage import LocalFileStorage
from infrastructure.story_folder_storage import StoryFolderStorage
from infrastructure.voice_map_storage import VoiceMapStorage
from infrastructure.audio_mixer import AudioMixer


class StoryForgeApi:
    def __init__(self):
        self.storage = LocalFileStorage()
        self.processor = None
        # 暫存本次工作的 Screenplay（按故事名稱）
        self._screenplays: dict[str, Screenplay] = {}
        self._init_processor()

    def _init_processor(self):
        api_key = self.storage.get_api_key()
        director = GeminiDirector(api_key)
        self.processor = StoryProcessor(director=director, storage=self.storage)

    # ── API 通行證 ────────────────────────────────────────────────
    def save_api_key(self, key: str):
        try:
            self.processor.save_key(key)
            self._init_processor()
            return {"status": "ok"}
        except Exception as e:
            return {"error": str(e)}

    def get_api_key(self):
        return self.processor.get_key()

    # ── 劇本拆解 ─────────────────────────────────────────────────
    def break_down_story(self, text: str, story_name: str):
        try:
            screenplay = self.processor.break_down_screenplay(text)
            self._screenplays[story_name] = screenplay

            # 確保故事資料夾存在
            folder = StoryFolderStorage(story_name)
            folder.ensure_folder()

            # AI 建議初始聲音對應（取所有角色，指定預設聲音）
            all_roles = list({line.role for scene in screenplay.scenes for line in scene.lines})
            default_voices = ["Kore", "Charon", "Fenrir", "Aoede", "Puck"]
            voice_map = {
                role: default_voices[i % len(default_voices)] for i, role in enumerate(all_roles)
            }
            if "旁白" in voice_map:
                voice_map["旁白"] = "Kore"  # 旁白固定用 Kore

            vm_storage = VoiceMapStorage(folder.folder_path)
            vm_storage.save(voice_map)

            return {
                "scenes": screenplay.to_dict()["scenes"],
                "voice_map": voice_map,
            }
        except Exception as e:
            return {"error": str(e)}

    # ── 場景語音生成 ──────────────────────────────────────────────
    def generate_scene_audio(self, scene_data: dict, story_name: str):
        try:
            folder = StoryFolderStorage(story_name)
            folder.ensure_folder()

            vm_storage = VoiceMapStorage(folder.folder_path)
            voice_map = vm_storage.load()

            lines = [ScriptLine(**ln) for ln in scene_data["lines"]]
            scene = Scene(
                scene_id=scene_data["scene_id"],
                title=scene_data["title"],
                lines=lines,
            )

            output_path = folder.scene_audio_path(scene.scene_id)
            path = self.processor.generate_scene_audio(scene, voice_map, output_path)
            return {"status": "ok", "path": path}
        except Exception as e:
            return {"error": str(e)}

    # ── 最終拼接 ──────────────────────────────────────────────────
    def mix_final_audio(self, story_name: str, scene_ids: list):
        try:
            folder = StoryFolderStorage(story_name)
            scene_paths = [folder.scene_audio_path(sid) for sid in scene_ids]
            missing = [p for p in scene_paths if not os.path.exists(p)]
            if missing:
                return {"error": f"以下場景音檔尚未生成：{missing}"}

            output_path = folder.final_audio_path()
            AudioMixer.mix(scene_paths, output_path)
            return {"status": "ok", "path": output_path}
        except Exception as e:
            return {"error": str(e)}

    # ── 聲音對應表更新 ────────────────────────────────────────────
    def update_voice_map(self, story_name: str, voice_map: dict):
        try:
            folder = StoryFolderStorage(story_name)
            vm_storage = VoiceMapStorage(folder.folder_path)
            vm_storage.save(voice_map)
            return {"status": "ok"}
        except Exception as e:
            return {"error": str(e)}

    # ── 場景刪除 ──────────────────────────────────────────────────
    def delete_scene_audio(self, scene_id: int, story_name: str):
        try:
            folder = StoryFolderStorage(story_name)
            path = folder.scene_audio_path(scene_id)
            if os.path.exists(path):
                os.remove(path)
            return {"status": "ok"}
        except Exception as e:
            return {"error": str(e)}


if __name__ == "__main__":
    api = StoryForgeApi()
    html_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")
    window = webview.create_window(
        "StoryForge",
        url=html_path,
        js_api=api,
        width=1000,
        height=700,
    )
    webview.start()
```

- [ ] **Step 2: 跑全部測試確認舊的沒壞**

```bash
uv run pytest tests/ -v
```

預期：全部 PASS

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: wire scene pipeline into StoryForgeApi (breakdown/generate/mix/delete)"
```

---

## Verification Plan

### Automated Tests

```bash
uv run pytest tests/ -v --tb=short
```

全部 Task 完成後預期：所有測試 PASS，無 `FutureWarning`（已換 SDK）。

### Manual Verification（手動確認）

1. 執行 `uv run main.py`，確認 UI 正常開啟，無警告訊息
2. 設定 API 通行證後，輸入一段 300 字以上的中文故事，按「分析」
3. 確認 UI 顯示多個場景，每個場景有標題
4. 確認 `~/Documents/StoryForge/<故事名>/voice_map.json` 已建立
5. 點擊其中一個場景的「生成語音」按鈕
6. 確認 `scene_01.mp3`（或對應編號）出現在故事資料夾
7. 修改該場景的一行台詞，再點「重新生成」，確認音檔被覆蓋
8. 按「產出完整有聲書」，確認 `final_output.mp3` 出現
