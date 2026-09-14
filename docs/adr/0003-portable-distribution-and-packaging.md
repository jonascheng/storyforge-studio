# ADR 0003 — 跨平台免洗執行與套件發布架構

**日期**：2026-09-14  
**狀態**：已確認

---

## 背景

StoryForge 旨在讓非工程師使用者（不論使用 Windows 或 macOS）都能透過單一行指令免安裝（`uvx`）直接啟動。在進行套件化時面臨以下關鍵挑戰：
1. **PyPI 命名衝突**：官方套件庫已有名為 `storyforge` 的既有專案（為他人之文字冒險 TUI）。
2. **音訊底層依賴**：聲音拼接（`AudioMixer` / `pydub`）處理 MP3 時需依賴底層 `ffmpeg`，非工程師電腦通常未安裝此工具，手動安裝設定門檻極高。
3. **設定檔記憶位置**：原先設定檔（`storyforge_config.json`）存於終端機當前目錄，跨資料夾執行會遺失通行證（API Key）。
4. **受眾分流**：非工程師需要極簡步驟教學，而開源協作者需要嚴格的架構與測試規範。

## 決定

1. **官方套件名稱訂為 `storyforge-studio`**：
   - 解決 PyPI 命名衝突，並保留未來發布至官方套件庫的能力。
2. **雙指令捷徑（Entrypoint Aliases）**：
   - 同時註冊 `storyforge` 與 `storyforge-studio` 兩個執行指令。
   - 使用者可直接執行：
     `uvx --from git+https://github.com/jonascheng/storyforge storyforge`
     或（發布後）：
     `uvx storyforge-studio`
3. **內建 `static-ffmpeg` 自動補充音訊小剪刀工具**：
   - 軟體啟動時透過 `static-ffmpeg` 自動補齊環境路徑，使用者不需在 Windows 或 macOS 手動安裝設定 `ffmpeg`。
4. **設定檔固定存放於 `~/Documents/StoryForge/storyforge_config.json`**：
   - 與故事資料夾（`~/Documents/StoryForge/`）集中管理，不管從任何目錄執行 `uvx` 都能自動載入已儲存的 API Key。
5. **說明文件雙軌分離**：
   - `README.md`：全繁體中文，專為非工程師設計（Windows/Mac 步驟化引導、取得免費通行證、界面操作說明）。
   - `CONTRIBUTING.md`：專為工程師與開源協作者設計（Clean Architecture、嚴格 TDD 規範、`uv run pytest` 全測試合格標準、PR 流程）。

## 被放棄的替代方案

| 方案 | 為何放棄 |
|------|---------|
| 強制手動安裝 ffmpeg | 非工程師在 Windows/Mac 設定 PATH 環境變數失敗率高，違反「零工程門檻」原則 |
| 僅支援單一命令列別名 | 限制了使用者記憶習慣，同時提供 `storyforge` 與 `storyforge-studio` 體驗更佳 |
| 將說明與貢獻指南混在同一份 README.md | 技術名詞與測試指令會使非工程師產生抗拒心理 |
| 依賴執行當前路徑儲存設定檔 | 每次切換目錄就要重新輸入 API Key，使用者體驗不佳 |

## 代價

- 引入 `static-ffmpeg` 在首次啟動時需花費數秒下載相應平台的執行檔，但換取完全免手動設定的順暢體驗。
- `pyproject.toml` 需明確打包 `ui/` 前端靜態資源，確保快取環境中 UI 能正常載入。
