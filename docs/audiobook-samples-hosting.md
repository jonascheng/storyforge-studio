# 有聲書範本音訊託管指南 (Audiobook Samples Hosting)

本指南說明如何使用 **GitHub Releases** 作為 StoryForge 有聲書範本的免費高音質音訊託管空間。

---

## 💡 五歲小孩比喻：為什麼用 GitHub Releases？

GitHub Releases 就像是在 GitHub 城堡的大門口設立一個**公開展示糖果盒**：
- **完全免費**：不用花任何零用錢，也不用跟外部廠商簽約。
- **大容量**：每個音訊檔案最大可以塞到 2GB（一部完整有聲書通常才 10MB~50MB）。
- **隨拿隨吃（隨點隨播）**：全世界任何人走過來都能立刻拿起耳機聽，而且支援「邊走邊聽、隨意跳段」（HTTP Range 串流），不需要等整首下載完。

---

## 🏷️ 規範定義

### 1. 專屬釋出標籤 (Release Tag)
- **Tag 名稱**：`audiobook-samples`
- **Release 標題**：`🎙️ StoryForge Audiobook Samples`
- **說明**：專門存放示範音訊，與軟體版本（如 `v0.1.0`）分開，確保連結永久固定。

### 2. 檔案命名慣例 (Naming Convention)
檔名統一採小寫英文與連字號，格式如下：
```text
sample-<編號>-<故事英文主題>.mp3
```

範例：
- `sample-01-cyberpunk-detective.mp3`（賽博龐克偵探廣播劇）
- `sample-02-forest-whisper.mp3`（奇幻童話森林冒險）
- `sample-03-space-odyssey.mp3`（太空科幻冒險）

### 3. 音訊規格建議
- **格式**：MP3
- **取樣率**：44.1 kHz
- **位元率**：128 kbps ~ 192 kbps（立體聲 Stereo）
- **建議長度**：精華示範片段 60 秒 ~ 180 秒（檔案約 1MB ~ 3MB，秒開不延遲）

### 4. 永久公開直連網址公式 (Permanent Direct URL)
任何人或網頁播放器皆可透過以下公式直接讀取音訊：

```text
https://github.com/jonascheng/storyforge-studio/releases/download/audiobook-samples/<檔案名稱>
```

例如：
`https://github.com/jonascheng/storyforge-studio/releases/download/audiobook-samples/sample-01-cyberpunk-detective.mp3`

---

## 🚀 上傳與發布流程

### 方式一：網頁後台操作（推薦，最直覺）
1. 打開瀏覽器進入 GitHub 專案的 [Releases 頁面](https://github.com/jonascheng/storyforge-studio/releases)。
2. 若尚未建立，點擊 **「Draft a new release」**：
   - **Choose a tag**：輸入 `audiobook-samples` 並點擊「Create new tag」。
   - **Release title**：填寫 `🎙️ StoryForge Audiobook Samples`。
3. 將製作好的範本 MP3 檔案（如 `sample-01-cyberpunk-detective.mp3`）直接拖拉到下方的 **「Attach binaries by dropping them here」** 虛線框中。
4. 點擊綠色的 **「Publish release」**。
5. （未來若要追加新範本）：直接在該 Release 點擊右上角 **「✏️ 編輯 (Edit)」**，拖入新檔案後點擊 **「Update release」** 即可。

### 方式二：使用 GitHub CLI 指令（自動化）
首次建立 Release 並上傳檔案：
```bash
gh release create audiobook-samples sample-01-cyberpunk-detective.mp3 \
  --title "🎙️ StoryForge Audiobook Samples" \
  --notes "StoryForge 有聲書官方範本高音質試聽音檔"
```

後續追加新的範本音檔：
```bash
gh release upload audiobook-samples sample-02-forest-whisper.mp3
```
