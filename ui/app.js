document.addEventListener("DOMContentLoaded", () => {
    const btnSettings = document.getElementById("btnSettings");
    const settingsModal = document.getElementById("settingsModal");
    const btnCloseSettings = document.getElementById("btnCloseSettings");
    const btnSaveSettings = document.getElementById("btnSaveSettings");
    const apiKeyInput = document.getElementById("apiKeyInput");

    const btnBreakdown = document.getElementById("btnBreakdown");
    const storyInput = document.getElementById("storyInput");
    const scriptSection = document.getElementById("scriptSection");
    const scriptList = document.getElementById("scriptList");
    
    const btnGenerate = document.getElementById("btnGenerate");
    const generatingModal = document.getElementById("generatingModal");
    const loadingText = document.getElementById("loadingText");

    let currentScript = [];

    // --- Settings Modal ---
    btnSettings.addEventListener("click", async () => {
        // Request existing key from python backend
        if (window.pywebview) {
            const key = await pywebview.api.get_api_key();
            apiKeyInput.value = key || "";
        }
        settingsModal.classList.remove("hidden");
    });

    btnCloseSettings.addEventListener("click", () => {
        settingsModal.classList.add("hidden");
    });

    btnSaveSettings.addEventListener("click", async () => {
        const key = apiKeyInput.value.trim();
        if (window.pywebview) {
            await pywebview.api.save_api_key(key);
        }
        settingsModal.classList.add("hidden");
    });

    // --- Breakdown Script ---
    btnBreakdown.addEventListener("click", async () => {
        const text = storyInput.value.trim();
        if (!text) {
            alert("請先貼上故事！");
            return;
        }

        const btnText = btnBreakdown.querySelector(".btn-text");
        const btnLoader = btnBreakdown.querySelector(".btn-loader");
        
        btnText.classList.add("hidden");
        btnLoader.classList.remove("hidden");
        btnBreakdown.disabled = true;

        try {
            if (window.pywebview) {
                const response = await pywebview.api.break_down_story(text);
                if (response.error) {
                    alert("錯誤: " + response.error);
                } else {
                    currentScript = response.lines;
                    renderScriptEditor();
                    scriptSection.classList.remove("hidden");
                    scriptSection.scrollIntoView({ behavior: 'smooth' });
                }
            } else {
                // Mock behavior for UI testing
                currentScript = [
                    {role: "旁白", emotion: "平靜", text: "這是一個測試故事。"},
                    {role: "小明", emotion: "開心", text: "哇！畫面好漂亮。"}
                ];
                renderScriptEditor();
                scriptSection.classList.remove("hidden");
                scriptSection.scrollIntoView({ behavior: 'smooth' });
            }
        } catch (e) {
            alert("發生錯誤：" + e);
        } finally {
            btnText.classList.remove("hidden");
            btnLoader.classList.add("hidden");
            btnBreakdown.disabled = false;
        }
    });

    function renderScriptEditor() {
        scriptList.innerHTML = "";
        currentScript.forEach((line, index) => {
            const item = document.createElement("div");
            item.className = "script-item";
            
            const roleInput = document.createElement("input");
            roleInput.className = "role";
            roleInput.value = line.role;
            roleInput.onchange = (e) => currentScript[index].role = e.target.value;

            const emotionInput = document.createElement("input");
            emotionInput.className = "emotion";
            emotionInput.value = line.emotion;
            emotionInput.onchange = (e) => currentScript[index].emotion = e.target.value;

            const textInput = document.createElement("textarea");
            textInput.className = "line-text";
            textInput.value = line.text;
            textInput.onchange = (e) => currentScript[index].text = e.target.value;

            item.appendChild(roleInput);
            item.appendChild(emotionInput);
            item.appendChild(textInput);
            
            scriptList.appendChild(item);
        });
    }

    // --- Generate Audio ---
    btnGenerate.addEventListener("click", async () => {
        generatingModal.classList.remove("hidden");
        loadingText.innerText = "AI 導演正在處理聲音...";
        
        try {
            if (window.pywebview) {
                const response = await pywebview.api.generate_audio({lines: currentScript});
                if (response.error) {
                    alert("錯誤: " + response.error);
                } else {
                    loadingText.innerText = "完成！檔案已存檔。";
                    setTimeout(() => generatingModal.classList.add("hidden"), 2000);
                }
            } else {
                // Mock
                setTimeout(() => {
                    loadingText.innerText = "完成！檔案已存檔。";
                    setTimeout(() => generatingModal.classList.add("hidden"), 2000);
                }, 2000);
            }
        } catch (e) {
            alert("發生錯誤：" + e);
            generatingModal.classList.add("hidden");
        }
    });
});
