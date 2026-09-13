document.addEventListener("DOMContentLoaded", () => {
    // ── Elements ──────────────────────────────────────────────
    const btnSettings      = document.getElementById("btnSettings");
    const settingsModal    = document.getElementById("settingsModal");
    const btnCloseSettings = document.getElementById("btnCloseSettings");
    const btnSaveSettings  = document.getElementById("btnSaveSettings");
    const apiKeyInput      = document.getElementById("apiKeyInput");
    const thinkingLevelSelect = document.getElementById("thinkingLevelSelect");

    const storyInput       = document.getElementById("storyInput");
    const storyNameInput   = document.getElementById("storyNameInput");
    const btnBreakdown     = document.getElementById("btnBreakdown");
    const btnLoadScreenplay = document.getElementById("btnLoadScreenplay");

    const scenesSection    = document.getElementById("scenesSection");
    const scenesList       = document.getElementById("scenesList");
    const storyNameBadge   = document.getElementById("storyNameBadge");
    const btnMixFinal      = document.getElementById("btnMixFinal");

    const loadingModal     = document.getElementById("loadingModal");
    const loadingText      = document.getElementById("loadingText");
    const loadingSubtext   = document.getElementById("loadingSubtext");
    const toast            = document.getElementById("toast");

    // ── State ─────────────────────────────────────────────────
    let currentScenes  = [];   // [{ scene_id, title, lines, audio_path }]
    let currentStory   = "";   // 故事名稱
    let audioReady     = {};   // { scene_id: true/false }

    // ── Utilities ─────────────────────────────────────────────
    function showLoading(text, sub = "請稍候") {
        loadingText.textContent = text;
        loadingSubtext.textContent = sub;
        loadingModal.classList.remove("hidden");
    }
    function hideLoading() { loadingModal.classList.add("hidden"); }

    function showToast(msg, type = "success") {
        toast.textContent = msg;
        toast.className = `toast ${type}`;
        setTimeout(() => toast.classList.add("hidden"), 3000);
    }

    function api(method, ...args) {
        if (window.pywebview) return pywebview.api[method](...args);
        return Promise.resolve({ error: "pywebview not available" });
    }

    // ── Settings ──────────────────────────────────────────────
    btnSettings.addEventListener("click", async () => {
        const settings = await api("get_settings");
        if (settings && !settings.error) {
            apiKeyInput.value = settings.key || "";
            thinkingLevelSelect.value = settings.thinking_level || "MEDIUM";
        }
        settingsModal.classList.remove("hidden");
    });
    btnCloseSettings.addEventListener("click", () => settingsModal.classList.add("hidden"));
    btnSaveSettings.addEventListener("click", async () => {
        const key = apiKeyInput.value.trim();
        const level = thinkingLevelSelect.value;
        await api("save_settings", key, level);
        settingsModal.classList.add("hidden");
        showToast("設定已儲存 ✓");
    });

    // ── Step 1: Breakdown ─────────────────────────────────────
    btnBreakdown.addEventListener("click", async () => {
        const text = storyInput.value.trim();
        const name = storyNameInput.value.trim();

        if (!text) { showToast("請先貼上故事！", "error"); return; }
        if (!name) { showToast("請輸入故事名稱！", "error"); return; }

        setBtnLoading(btnBreakdown, true, "分析中...");
        showLoading("AI 導演正在閱讀故事…", "正在拆解場景與角色，請稍候");

        try {
            const resp = await api("break_down_story", text, name);
            if (resp.error) { showToast("錯誤：" + resp.error, "error"); return; }

            currentStory  = name;
            currentScenes = resp.scenes;
            audioReady    = {};

            storyNameBadge.textContent = "📖 " + name;
            renderScenes();
            scenesSection.classList.remove("hidden");
            scenesSection.scrollIntoView({ behavior: "smooth" });
            showToast(`拆解完成！共 ${currentScenes.length} 個場景 ✓`);
        } catch (e) {
            showToast("發生錯誤：" + e, "error");
        } finally {
            setBtnLoading(btnBreakdown, false, "🎬 AI 分析劇本");
            hideLoading();
        }
    });

    // ── Step 1.5: Load Old Screenplay ─────────────────────────
    btnLoadScreenplay.addEventListener("click", async () => {
        const name = storyNameInput.value.trim();
        if (!name) { showToast("請先輸入故事名稱！", "error"); return; }

        setBtnLoading(btnLoadScreenplay, true, "讀取中...");
        
        try {
            const resp = await api("load_screenplay", name);
            if (resp.error) {
                showToast(resp.error, "error");
                return;
            }

            currentStory  = name;
            currentScenes = resp.scenes;
            audioReady    = {};
            if (resp.audio_ready_ids) {
                resp.audio_ready_ids.forEach(id => { audioReady[id] = true; });
            }

            storyNameBadge.textContent = "📖 " + name;
            renderScenes();
            scenesSection.classList.remove("hidden");
            scenesSection.scrollIntoView({ behavior: "smooth" });
            showToast(`成功載入舊劇本！共 ${currentScenes.length} 個場景 ✓`);
        } catch (e) {
            showToast("發生錯誤：" + e, "error");
        } finally {
            setBtnLoading(btnLoadScreenplay, false, "📂 載入舊劇本");
        }
    });

    // ── Render Scenes ─────────────────────────────────────────
    function renderScenes() {
        scenesList.innerHTML = "";
        currentScenes.forEach((scene, idx) => renderSceneCard(scene, idx));
    }

    function renderSceneCard(scene, idx) {
        const isReady = audioReady[scene.scene_id];
        const statusClass = isReady ? "done" : "pending";
        const statusText = isReady ? "✓ 已完成" : "○ 尚未生成";
        
        const card = document.createElement("div");
        card.className = isReady ? "scene-card has-audio" : "scene-card";
        card.id = `scene-card-${scene.scene_id}`;

        // Header
        const header = document.createElement("div");
        header.className = "scene-header";
        header.style.flexWrap = "wrap";
        header.innerHTML = `
            <div style="display: flex; width: 100%; justify-content: space-between; align-items: center;">
                <div class="scene-title-group">
                    <span class="scene-number">場景 ${scene.scene_id}</span>
                    <span class="scene-title">${scene.title}</span>
                </div>
                <div class="scene-actions">
                    <span class="audio-status ${statusClass}" id="status-${scene.scene_id}">
                        ${statusText}
                    </span>
                    <button class="scene-regen-btn" id="regen-${scene.scene_id}">
                        🎙 生成語音
                    </button>
                </div>
            </div>
            <div id="error-${scene.scene_id}" style="display: none; width: 100%; color: #f87171; font-size: 13px; margin-top: 10px; padding: 8px; background: rgba(248,113,113,0.1); border-radius: 6px; border: 1px solid rgba(248,113,113,0.3);">
            </div>
        `;

        // Toggle collapse on header click (not on button)
        header.addEventListener("click", (e) => {
            if (e.target.closest(".scene-regen-btn")) return;
            body.classList.toggle("collapsed");
        });

        // Body (lines)
        const body = document.createElement("div");
        body.className = "scene-body";

        scene.lines.forEach((line, lineIdx) => {
            const row = document.createElement("div");
            row.className = "script-line";

            const roleInput = document.createElement("input");
            roleInput.className = "role";
            roleInput.value = line.role;
            roleInput.title = "角色";
            roleInput.addEventListener("change", (e) => {
                currentScenes[idx].lines[lineIdx].role = e.target.value;
                api("save_screenplay_progress", currentStory, currentScenes);
            });

            const emotionInput = document.createElement("input");
            emotionInput.className = "emotion";
            emotionInput.value = line.emotion;
            emotionInput.title = "情緒";
            emotionInput.addEventListener("change", (e) => {
                currentScenes[idx].lines[lineIdx].emotion = e.target.value;
                api("save_screenplay_progress", currentStory, currentScenes);
            });

            const textArea = document.createElement("textarea");
            textArea.value = line.text;
            textArea.title = "台詞";
            textArea.addEventListener("change", (e) => {
                currentScenes[idx].lines[lineIdx].text = e.target.value;
                // Mark audio as stale when content changes
                markSceneStale(scene.scene_id);
                api("save_screenplay_progress", currentStory, currentScenes);
            });

            row.appendChild(roleInput);
            row.appendChild(emotionInput);
            row.appendChild(textArea);
            body.appendChild(row);
        });

        card.appendChild(header);
        card.appendChild(body);
        scenesList.appendChild(card);

        // Wire regen button
        document.getElementById(`regen-${scene.scene_id}`)
            .addEventListener("click", () => regenScene(scene.scene_id, idx));
    }

    // ── Regen single scene ────────────────────────────────────
    async function regenScene(sceneId, idx) {
        const btn = document.getElementById(`regen-${sceneId}`);
        const card = document.getElementById(`scene-card-${sceneId}`);
        const status = document.getElementById(`status-${sceneId}`);
        const errorDiv = document.getElementById(`error-${sceneId}`);

        btn.disabled = true;
        btn.textContent = "處理中...";
        card.classList.add("generating");
        card.classList.remove("has-audio");
        status.className = "audio-status working";
        status.textContent = "⟳ 生成中...";
        if (errorDiv) errorDiv.style.display = "none";

        try {
            const sceneData = currentScenes[idx];
            const resp = await api("generate_scene_audio", sceneData, currentStory);

            if (resp.error) {
                showToast(`場景 ${sceneId} 錯誤：${resp.error}`, "error");
                status.className = "audio-status pending";
                status.textContent = "✕ 失敗";
                if (errorDiv) {
                    errorDiv.innerHTML = `<div>${resp.error}</div>`;
                    if (resp.error.includes("安全審查阻擋")) {
                        const btn = document.createElement("button");
                        btn.className = "safe-line-btn";
                        btn.textContent = "✨ 讓 AI 幫我想安全的台詞";
                        
                        const suggContainer = document.createElement("div");
                        suggContainer.className = "suggestions-container hidden";
                        
                        btn.onclick = async () => {
                            btn.textContent = "思考中...";
                            btn.disabled = true;
                            const match = resp.error.match(/台詞「(.*?)」/);
                            if (match) {
                                const originalText = match[1];
                                const res = await api("suggest_safe_lines", originalText);
                                if (res.suggestions && res.suggestions.length > 0) {
                                    btn.style.display = "none"; // Hide button after success
                                    suggContainer.innerHTML = res.suggestions.map(s => 
                                        `<div class="suggestion-item" data-text="${s.replace(/"/g, '&quot;')}">${s}</div>`
                                    ).join("");
                                    suggContainer.classList.remove("hidden");
                                    
                                    suggContainer.querySelectorAll(".suggestion-item").forEach(el => {
                                        el.onclick = () => {
                                            const newText = el.getAttribute("data-text");
                                            const lineIdx = currentScenes[idx].lines.findIndex(l => l.text === originalText);
                                            if (lineIdx !== -1) {
                                                currentScenes[idx].lines[lineIdx].text = newText;
                                                api("save_screenplay_progress", currentStory, currentScenes);
                                                const body = document.getElementById(`scene-card-${sceneId}`).querySelector(".scene-body");
                                                const textAreas = body.querySelectorAll("textarea");
                                                if (textAreas[lineIdx]) textAreas[lineIdx].value = newText;
                                                
                                                suggContainer.classList.add("hidden");
                                                errorDiv.style.display = "none";
                                            }
                                        };
                                    });
                                } else {
                                    btn.textContent = "無法產生建議";
                                }
                            }
                        };
                        
                        errorDiv.appendChild(btn);
                        errorDiv.appendChild(suggContainer);
                    }
                    errorDiv.style.display = "block";
                }
            } else {
                audioReady[sceneId] = true;
                card.classList.remove("generating");
                card.classList.add("has-audio");
                status.className = "audio-status done";
                status.textContent = "✓ 已完成";
                showToast(`場景 ${sceneId}《${currentScenes[idx].title}》語音生成完畢 ✓`);
            }
        } catch (e) {
            showToast("發生錯誤：" + e, "error");
            status.className = "audio-status pending";
            status.textContent = "✕ 失敗";
            if (errorDiv) {
                errorDiv.textContent = e.toString();
                errorDiv.style.display = "block";
            }
        } finally {
            btn.disabled = false;
            btn.textContent = "🎙 重新生成";
        }
    }

    function markSceneStale(sceneId) {
        if (audioReady[sceneId]) {
            audioReady[sceneId] = false;
            const card = document.getElementById(`scene-card-${sceneId}`);
            card.classList.remove("has-audio");
            const status = document.getElementById(`status-${sceneId}`);
            status.className = "audio-status pending";
            status.textContent = "● 內容已修改";
        }
    }

    // ── Mix Final ─────────────────────────────────────────────
    btnMixFinal.addEventListener("click", async () => {
        const readyIds = currentScenes
            .map(s => s.scene_id)
            .filter(id => audioReady[id]);

        if (readyIds.length === 0) {
            showToast("請先為至少一個場景生成語音！", "error");
            return;
        }

        const missingCount = currentScenes.length - readyIds.length;
        if (missingCount > 0) {
            const go = confirm(
                `還有 ${missingCount} 個場景尚未生成語音，\n` +
                `是否只使用已完成的 ${readyIds.length} 個場景合成有聲書？`
            );
            if (!go) return;
        }

        setBtnLoading(btnMixFinal, true, "合併中...");
        showLoading("正在合併所有場景…", "pydub 拼接音檔中，請稍候");

        try {
            const resp = await api("mix_final_audio", currentStory, readyIds);
            if (resp.error) {
                showToast("合併失敗：" + resp.error, "error");
            } else {
                showToast("🎉 有聲書已產出！檔案已存檔。");
                loadingText.textContent = "🎉 完成！";
                loadingSubtext.textContent = "有聲書已儲存至故事資料夾";
                setTimeout(hideLoading, 2500);
                return;
            }
        } catch (e) {
            showToast("發生錯誤：" + e, "error");
        } finally {
            setBtnLoading(btnMixFinal, false, "🔊 產出完整有聲書");
            if (!loadingModal.classList.contains("hidden")) hideLoading();
        }
    });

    // ── Helper ────────────────────────────────────────────────
    function setBtnLoading(btn, loading, loadingLabel) {
        const text   = btn.querySelector(".btn-text");
        const loader = btn.querySelector(".btn-loader");
        btn.disabled = loading;
        if (loading) {
            text.classList.add("hidden");
            loader.classList.remove("hidden");
            loader.textContent = loadingLabel;
        } else {
            text.classList.remove("hidden");
            loader.classList.add("hidden");
            text.textContent = loadingLabel;
        }
    }
});
