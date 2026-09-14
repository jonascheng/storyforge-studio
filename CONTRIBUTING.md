# 開發者與協作者貢獻指南 (Contributing Guide)

感謝你對 StoryForge 的關注！本專案旨在打造將文字故事轉換為生動有聲書的高品質工具。

為了確保軟體核心邏輯清晰、穩定可維護，本專案嚴格遵守 **整潔架構 (Clean Architecture)** 與 **測試驅動開發 (Strict TDD)** 規範。請在參與貢獻前詳閱以下原則。

---

## 🛠️ 開發環境設定

本專案使用現代化 Python 依賴管理工具 [`uv`](https://github.com/astral-sh/uv)。

1. **複製專案**：
   ```bash
   git clone https://github.com/jonascheng/storyforge-studio.git
   cd storyforge-studio
   ```


2. **同步依賴環境**：
   ```bash
   uv sync
   ```

3. **啟用本機門口哨兵 (Git Hooks)**：
   ```bash
   git config core.hooksPath .githooks
   ```

4. **啟動本機開發介面**：
   ```bash
   uv run storyforge
   # 或
   uv run python main.py
   ```

5. **執行程式碼風格檢查與自動排版**：
   ```bash
   # 檢查品質與瑕疵
   uv run ruff check .

   # 檢查排版風格
   uv run ruff format --check .

   # 自動修復可修正之問題
   uv run ruff check --fix .
   uv run ruff format .
   ```

6. **驗證所有自動化測試**：
   ```bash
   uv run pytest
   ```

---

## 🏛️ 架構原則：整潔架構 (Clean Architecture)

專案分層解耦，單向依賴，核心業務邏輯絕不受外部框架或技術細節干擾：

```
[ UI 介面層 ] (ui/ + pywebview)
      ↓
[ 核心業務層 ] (core/entities.py & core/use_cases.py)
      ↑
[ 外部基礎層 ] (infrastructure/ - Gemini API, Storage, AudioMixer)
```

- **`core/`（核心邏輯層）**：
  - `entities.py`：定義場景（Scene）、劇本台詞（ScriptLine）、劇本（Screenplay）等純資料物件。
  - `use_cases.py`：定義劇本拆解、語音生成工作流，以及 `IDirector`、`IStorage` 抽象介面。
  - ⚠️ **禁令**：本層絕不可直接引用任何外部函式庫（如 `google-genai`、`pydub`、`webview`）。
- **`infrastructure/`（外部實作層）**：
  - 實作 `core` 所定義的介面，例如 `GeminiDirector` 串接 Google Gemini API、`StoryFolderStorage` 管理硬碟檔案、`AudioMixer` 處理音訊拼接。
- **`ui/`（使用者介面層）**：
  - HTML5、Vanilla CSS、Vanilla JavaScript 前端，透過 `pywebview` 的 JS API 與後端溝通。

---

## 🧪 開發流程：嚴格測試驅動開發 (Strict TDD)

所有新功能開發或錯誤修復，**必須遵循紅燈-綠燈-重構（Red-Green-Refactor）流程**：

1. **先寫測試（Red）**：在 `tests/` 新增測試案例，描述預期行為與驗收條件，確認測試失敗。
2. **編寫實作（Green）**：編寫最少必要程式碼，使測試通過。
3. **重構優化（Refactor）**：在測試保護傘下重構程式碼，維持高可讀性與架構純潔性。
4. **全測試驗證**：送出前必須確認 `uv run pytest` 全數通過（目前共有 49 項測試）。

---

## 📋 Issue 與 Pull Request 流程

本專案使用 GitHub Issues 與 Pull Requests 管理工作。

### Triage 標籤分類
專案遵循 `docs/agents/triage-labels.md` 定義之五大標準標籤：
- `needs-triage`：新建立的議題，待審查其問題完整性。
- `ready-for-agent`：需求明確、驗收條件清楚，可立即指派開發。
- `agent-working`：目前正在進行開發。
- `needs-human-review`：實作完成，等待人工驗收審查。
- `done`：已驗收並合併完成。

### 送出 Pull Request (PR) 檢核清單
在提交 PR 之前，請確認：
- [ ] 遵循 Clean Architecture 架構分層。
- [ ] 執行 `uv run ruff check .` 與 `uv run ruff format --check .` 確認排版與品質檢查全數通過。
- [ ] 執行 `uv run pytest` 確認所有測試 100% 通過。
- [ ] 新增或修改的功能具備對應的單元或整合測試。
- [ ] 若涉及重要決策，已撰寫或更新對應的 [ADR (Architecture Decision Record)](docs/adr/)。
- [ ] PR 描述清晰說明修改動機與驗證成果。
