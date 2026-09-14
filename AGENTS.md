# 專案說明書

## 專案與角色
- **目標**：文字交由 AI 導演（情緒、角色、聲音表演）轉為生動有聲書。
- **用戶**：非工程師。絕不要求用戶改程式碼。需操作時提供步驟化引導。付費服務事先報價確認。

## 溝通原則
- **語言**：全程繁體中文。
- **表達**：禁工程術語，技術概念用五歲小孩比喻。
- **回報**：每步完成以白話說明「做了什麼」與「原因」。
- **決策**：白話列出選項並附推薦建議。

## 開發規範
- **架構**：Clean Architecture（核心邏輯、UI、外部服務分層解耦）。
- **流程**：嚴格 TDD（先寫測試驗收條件，實作後驗證全過）。

## Agent skills

### Issue tracker

GitHub Issues via `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical five-role vocabulary (`needs-triage`, `ready-for-agent`, etc.). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout (`CONTEXT.md` and `docs/adr/`). See `docs/agents/domain.md`.


