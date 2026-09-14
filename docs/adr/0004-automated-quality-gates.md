# ADR 0004 — 雙層品質檢查機制（Ruff、本地 Git Hook 與 GitHub Actions CI）

**日期**：2026-09-14  
**狀態**：已確認

---

## 背景

StoryForge 遵循整潔架構 (Clean Architecture) 與測試驅動開發 (Strict TDD)。隨著程式碼庫擴展，若缺乏自動化檢驗手段，容易在提交時混入未整理的排版風格、無效的引用（unused imports）或未通過的單元測試，進而增加程式碼審查成本與潛在錯誤風險。

---

## 決定

採用**雙層品質守門機制（本機門口哨兵 + 雲端守門員）**並選用 **Ruff** 作為全專案的品質檢查與排版標準：

```
本機端 (開發者電腦)
  git commit 
    ↓
  [本地哨兵] (.githooks/pre-commit)
    • 快檢本次暫存 (staged) 之 Python 檔案
    • 執行 ruff check 與 ruff format --check (< 1 秒)
    • 違規即阻擋並提供修復指引
    ↓
  通過後完成本機提交

雲端 (GitHub)
  git push / PR
    ↓
  [雲端守門員] (GitHub Actions CI)
    • 智慧過濾：動到程式碼或畫面才啟動
    • 執行全專案 ruff check
    • 執行全專案 ruff format --check
    • 執行完整單元測試 (pytest，含 Node.js 介面測試)
    ↓
  全數通過方可合併
```

具體規則：
1. **工具選型**：採用現代化極速工具 `ruff`，整合於 `pyproject.toml` 的 dev 依賴群組中，替代舊有分散的多套工具。
2. **本機哨兵**：使用原生 Git Hook 架構存放於 `.githooks/pre-commit`，透過 `git config core.hooksPath .githooks` 啟用，不強制安裝額外第三方框架。
3. **本機檢查範圍**：本地哨兵只檢查本次暫存檔案（staged files）的排版與壞味道，耗時小於 1 秒，不阻礙開發流暢性。
4. **雲端完整檢驗**：完整單元測試（現有 49 項測試）與全專案靜態檢查交由 GitHub Actions CI 執行。
5. **CI 智慧路徑過濾**：僅在 Python 檔案、UI 前端、依賴設定與 CI 腳本變更時觸發，改動純 Markdown 文件不消耗 CI 運算資源。

---

## 被放棄的替代方案

| 方案 | 為何放棄 |
|------|---------|
| Flake8 + Black + isort 傳統組合 | 需配置多個工具且速度慢；Ruff 單一工具即可涵蓋並快 10~100 倍 |
| 第三方 `pre-commit` 套件框架 | 需額外安裝 Python 外掛環境，對非工程師或輕量協作者增加上手門檻 |
| 本地端每次 commit 執行完整 pytest | 目前 49 項測試包含 Node.js 與音訊模擬，耗時約 15 秒，每次存檔等待過久破壞開發體驗 |
| 本地哨兵自動修正並 commit | 可能在開發者不知情下自動變更程式碼內容，失去確認把關之嚴謹性 |

---

## 代價

- 本機開發者需在首次複製專案後執行一次 `git config core.hooksPath .githooks` 啟用哨兵（已記錄於 CONTRIBUTING.md）。
- 既有程式碼已由自動化工具全數整理統一風格。
