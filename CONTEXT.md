# StoryForge

將文字故事轉換為具備情緒、角色演繹與生動聲音的有聲書電腦軟體。

## Language

**StoryForge**:
本專案的名稱，一個在電腦上執行的有聲書產生工具。
_Avoid_: 小工具、App

**AI 導演 (AI Director)**:
負責理解文字故事中的情緒與角色，並決定如何發聲的核心大腦。目前使用的是 Gemini 3.1 Flash TTS。
_Avoid_: 語音合成器、文字轉語音、TTS 模型

**故事原稿 (Source Text)**:
使用者直接貼上的原始文字，這是 AI 導演的輸入。
_Avoid_: 腳本、輸入檔

**劇本拆解 (Script Breakdown)**:
AI 導演將原稿自動分析並拆解成一段段「旁白」與「不同角色的對話」，並加上情緒標記的過程。
_Avoid_: 文字分析、前處理

**有聲書成品 (Audio Output)**:
最後產生出來並存檔的 MP3 聲音檔，可以直接播放或分享。
_Avoid_: 輸出檔、結果

**劇本編輯區 (Script Editor)**:
讓你在 AI 拆解完劇本後，可以手動修改角色、情緒或台詞的畫面。
_Avoid_: 修改介面

**API 通行證 (API Key)**:
用來證明你有權限使用 Gemini 大腦的專屬密碼，只要設定一次就會自動記住。
_Avoid_: 金鑰、憑證
