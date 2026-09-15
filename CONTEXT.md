# StoryForge

將文字故事轉換為具備情緒、角色演繹與生動聲音的有聲書電腦軟體。

## Language

**StoryForge**:
本專案的名稱，一個在電腦上執行的有聲書產生工具。
_Avoid_: 小工具、App

**AI 導演 (AI Director)**:
負責理解文字故事中的情緒與角色，並決定如何發聲的核心大腦。目前使用的是 Gemini 3.8 Flash。
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

**場景 (Scene)**:
AI 導演將劇本自動分割成的段落，每個場景代表一個情節單元（時間地點或情緒基調相對一致）。每個場景有 AI 自動取的標題，包含若干台詞行，並對應一個獨立的音檔。場景是重新生成語音的最小單位。
_Avoid_: 段落、片段、chunk

**聲音導演備註 (Voice Direction Note)**:
AI 導演在劇本拆解時為每一行台詞附加的聲音指示文字（例如 `[excited, fast-paced]` 或「用顫抖的聲音輕聲說」），直接作為語音生成時的情緒提示。
_Avoid_: 情緒標記、TTS prompt

**角色聲音對應表 (Voice Map)**:
記錄每個角色對應哪個語音聲線的設定，由 AI 導演初步建議，使用者可修改。每個故事有自己的對應表，存放於故事資料夾中。
_Avoid_: 聲音設定、語音配置

**故事資料夾 (Story Folder)**:
每個故事專屬的存放位置（預設為 `~/Documents/StoryForge/<故事名稱>/`，亦可為使用者自選的電腦資料夾），內含各場景的音檔、角色聲音對應表，以及最終的有聲書成品。
_Avoid_: 輸出目錄、資料夾

**故事選單視窗 (Story Selector)**:
點擊載入舊劇本時彈出的視窗，列出所有既有故事名稱、場景數量與修改時間，並提供直接挑選電腦資料夾的按鈕。
_Avoid_: 檔案總管、dialog、選單彈窗


**聲音拼接 (Audio Mixing)**:
將各場景的獨立音檔依序合併成最終有聲書成品的過程。在所有場景都生成完畢後執行。
_Avoid_: 合併、concatenate

**場景背景音樂 (Scene BGM)**:
AI 導演為每個場景在劇本拆解時自動建議的背景音樂英文描述（存於 `bgm_prompt` 欄位），用來呼叫 Lyria 3 Clip 生成 30 秒純器樂（根據場景情緒選風格，例如緊張場景用緩慢弦樂、溫馨場景用輕柔吉他），以 -18 dB 恆定墊底方式混入對白，場景首尾各 2 秒淡入/淡出，對白超過 30 秒時 1 秒 crossfade 無縫循環。使用者可在劇本編輯區修改或清空（留空不生成）。
_Avoid_: 環境音效、SFX、bgm_prompt

**思考深度 (Thinking Level)**:
AI 導演在拆解劇本與生成聲音導演備註時的思考深淺程度（分為 MEDIUM 與 LOW）。
_Avoid_: model parameter, reasoning level

**劇本進度檔 (Screenplay Progress)**:
記錄了 AI 拆解完並經過使用者修改的場景與台詞資料，自動存檔於故事資料夾中的檔案，可隨時載入恢復進度。
_Avoid_: cache file, save state

**合奏朗讀 (Multi-speaker Recording)**:
AI 導演在一個場景中，將最多兩位角色的來回對白打包在一起同時演繹出聲音的方式，能大幅縮短錄音時間並提升對手戲的自然度。
_Avoid_: 多人語音合成、批次 TTS

**朗讀對話組 (Dialogue Group)**:
在合奏朗讀時，由相鄰台詞且角色不超過兩位所組合而成的小段落，為單次交由 AI 導演演繹的單位（若只有一人自白則為單人朗讀組）。
_Avoid_: batch, chunk, 對話批次

**故事設定檔 (StoryForge Config)**:
記錄 API 通行證與思考深度設定的秘密筆記本，自動儲存於個人的 `~/Documents/StoryForge/storyforge_config.json`，不管在電腦哪個角落開啟都能記住。
_Avoid_: 設定檔、環境變數、.env

**本地哨兵 (Pre-commit Hook)**:
在電腦本機每次要把改好的故事程式積木存檔打包前，在門口快檢檔案有沒有排整齊的小幫手。
_Avoid_: pre-commit script, hook

**雲端守門員 (GitHub CI)**:
當把寫好的故事程式送到 GitHub 雲端時，自動在雲端乾淨電腦裡替我們把所有積木全部重新檢查與跑測試的自動化機器人。
_Avoid_: CI/CD, pipeline, Actions runner
