# ADR 0006 — 全面遷移至 Gemini Interactions API

**日期**：2026-09-16  
**狀態**：已確認

---

## 背景

Google 於 2026 年 6 月宣布 Interactions API 全面正式發布（GA），並列為 Gemini 所有模型與功能（文字、語音、音樂、結構化資料）的推薦唯一標準介面；原先的 `generateContent` 則列為舊版維護模式。

StoryForge 先前處於混合狀態：場景背景音樂（Lyria 3 Clip）已採用 Interactions API，但 AI 導演劇本拆解（Gemini 3.8 Flash）與聲音演員配音（Gemini 3.1 Flash TTS Preview）仍使用舊版 `generate_content`，且重試機制各自實作、重複分散。

## 決定

全面遷移至 **Gemini Interactions API**，架構規範如下：

1. **單一接口統一**：
   - 劇本拆解大腦（`gemini-3.8-flash`）、聲音演員配音（`gemini-3.1-flash-tts-preview`）、場景背景音樂（`lyria-3-clip-preview`）全部改由 `client.interactions.create` 呼叫。
2. **劇本拆解採用嚴格結構化表格（Structured Output）**：
   - 定義 Pydantic 規格書（DTO），透過 `response_format={"type": "text", "mime_type": "application/json", "schema": ...}` 傳給 Google，由伺服器保證 JSON 格式，免去人肉字串清洗。
   - 規格書嚴格置於 `infrastructure/` 層，驗證完成後轉為 `core.entities` 純淨領域積木，符合 Clean Architecture 原則。
   - 安全替代句建議（`suggest_safe_lines`）同步採用結構化表格。
3. **無痕創作隱私（`store=False`）**：
   - 由於有聲書劇本拆解與每段錄音皆為獨立事件，統一傳入 `store=False`，故事文字與音訊不留存於雲端伺服器歷史中。
4. **統一防卡關門衛（`_create_interaction_with_retry`）**：
   - 消除重複重試程式碼，劇本拆解、語音配音、背景音樂共用同一套 429 / RESOURCE_EXHAUSTED 額度限制辨識與退避重試邏輯。
5. **語音安全審查雙層攔截**：
   - TTS 呼叫若遭安全機制阻擋，從 API 異常或步驟詳情中提取阻擋理由，確保無縫觸發前端安全替代句救援流程。

## 被放棄的替代方案

| 方案 | 為何放棄 |
|------|---------|
| 僅升級劇本拆解，TTS 保留舊版 | 系統維護雙重 API 介面，未來升級與除錯複雜度倍增 |
| 劇本拆解維持純文字提示詞 + 字串清洗 | 偶發 Markdown 標籤或格式變形需額外修復，不如伺服器級 Schema 嚴格可靠 |
| 保持預設雲端黑板留存（`store=True`） | 有聲書原稿具隱私敏感性，單次任務無需跨輪對話快取 |
| 將 Pydantic 模型直接定義在 `core/entities.py` | 違反 Clean Architecture，使核心領域綁定外部傳輸套件 |

## 代價

- 需改寫既有針對 `_generate_content_with_retry` 的單元測試 Mock 物件，全面轉向 `_create_interaction_with_retry` 與 `interactions.create`。
- 結構化輸出需在 infrastructure 層維護 Pydantic DTO 定義。
