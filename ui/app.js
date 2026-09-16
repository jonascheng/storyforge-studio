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

    const storySelectorModal   = document.getElementById("storySelectorModal");
    const storyListContainer   = document.getElementById("storyListContainer");
    const btnBrowseFolder     = document.getElementById("btnBrowseFolder");
    const btnCloseStorySelector = document.getElementById("btnCloseStorySelector");

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
    let currentBgmMap  = null; // { themes: { [theme_id]: { name, prompt } } }

    // ── Utilities ─────────────────────────────────────────────
    function showLoading(text, sub = "請稍候") {
        loadingText.textContent = text;
        loadingSubtext.textContent = sub;
        loadingModal.classList.remove("hidden");
    }
    function hideLoading() { loadingModal.classList.add("hidden"); }

    let toastTimeout = null;

    function copyToClipboard(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            return navigator.clipboard.writeText(text).catch(() => fallbackCopy(text));
        }
        return fallbackCopy(text);
    }
    function fallbackCopy(text) {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        try {
            document.execCommand("copy");
        } catch (e) {}
        document.body.removeChild(ta);
        return Promise.resolve();
    }

    function showToast(msg, type = "success") {
        if (toastTimeout) clearTimeout(toastTimeout);
        toast.textContent = "";

        const textSpan = document.createElement("span");
        textSpan.textContent = msg;
        toast.appendChild(textSpan);

        if (type === "error") {
            const copyBtn = document.createElement("button");
            copyBtn.className = "toast-copy-btn";
            copyBtn.title = "點擊複製錯誤訊息";
            copyBtn.textContent = "📋 複製";
            copyBtn.onclick = (e) => {
                e.stopPropagation();
                copyToClipboard(msg).then(() => {
                    copyBtn.textContent = "✓ 已複製";
                    setTimeout(() => { copyBtn.textContent = "📋 複製"; }, 2000);
                });
            };
            toast.appendChild(copyBtn);
            toast.className = `toast ${type} interactive`;
            toastTimeout = setTimeout(() => toast.classList.add("hidden"), 8000);
        } else {
            toast.className = `toast ${type}`;
            toastTimeout = setTimeout(() => toast.classList.add("hidden"), 3000);
        }
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
            currentBgmMap = resp.bgm_map || null;

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

    // ── Helper: Apply loaded screenplay data to UI ──────────
    function applyLoadedStory(name, resp) {
        currentStory  = resp.story_name || name;
        storyNameInput.value = currentStory;
        storyInput.value = "";
        currentScenes = resp.scenes || [];
        audioReady    = {};
        currentBgmMap = resp.bgm_map || null;
        if (resp.audio_ready_ids) {
            resp.audio_ready_ids.forEach(id => { audioReady[id] = true; });
        }

        storyNameBadge.textContent = "📖 " + currentStory;
        renderScenes();
        scenesSection.classList.remove("hidden");
        scenesSection.scrollIntoView({ behavior: "smooth" });
        showToast(`成功載入故事「${currentStory}」！共 ${currentScenes.length} 個場景 ✓`);
    }

    // ── Step 1.5: Story Selector Modal & Folder Picker ────────
    btnLoadScreenplay.addEventListener("click", async () => {
        // 防呆：若原稿輸入框已有未拆解文字，提示確認
        if (storyInput.value.trim().length > 0) {
            if (typeof window.confirm === "function") {
                const confirmed = window.confirm("故事原稿輸入框中已有文字，載入舊劇本將會清除這些文字，是否繼續？");
                if (!confirmed) return;
            }
        }

        // 開啟故事選單視窗並載入清單
        storyListContainer.innerHTML = '<div class="story-empty-hint">正在讀取既有故事清單...</div>';
        storySelectorModal.classList.remove("hidden");

        try {
            const resp = await api("list_stories");
            if (resp && resp.error) {
                storyListContainer.innerHTML = `<div class="story-empty-hint">讀取故事清單失敗：${resp.error}</div>`;
                return;
            }

            const stories = (resp && resp.stories) ? resp.stories : [];
            if (stories.length === 0) {
                storyListContainer.innerHTML = '<div class="story-empty-hint">目前沒有找到任何既有故事<br><small style="color: var(--text-muted); margin-top: 6px; display: inline-block;">您可以點選下方按鈕直接從電腦資料夾挑選</small></div>';
                return;
            }

            storyListContainer.innerHTML = "";
            stories.forEach(story => {
                const item = document.createElement("div");
                item.className = "story-item";

                const infoDiv = document.createElement("div");
                infoDiv.className = "story-item-info";

                const titleDiv = document.createElement("div");
                titleDiv.className = "story-item-title";
                titleDiv.textContent = "📖 " + story.name;

                const metaDiv = document.createElement("div");
                metaDiv.className = "story-item-meta";

                const badge = document.createElement("span");
                badge.className = "story-item-badge";
                badge.textContent = `🎬 ${story.scene_count} 個場景`;

                const timeSpan = document.createElement("span");
                timeSpan.textContent = `🕒 ${story.updated_at}`;

                metaDiv.appendChild(badge);
                metaDiv.appendChild(timeSpan);
                infoDiv.appendChild(titleDiv);
                infoDiv.appendChild(metaDiv);

                const arrowDiv = document.createElement("div");
                arrowDiv.style.fontSize = "13px";
                arrowDiv.style.color = "var(--accent2)";
                arrowDiv.textContent = "載入 ➔";

                item.appendChild(infoDiv);
                item.appendChild(arrowDiv);

                item.addEventListener("click", async () => {
                    storySelectorModal.classList.add("hidden");
                    setBtnLoading(btnLoadScreenplay, true, "讀取中...");
                    try {
                        const loadResp = await api("load_screenplay", story.name);
                        if (loadResp.error) {
                            showToast(loadResp.error, "error");
                            return;
                        }
                        applyLoadedStory(story.name, loadResp);
                    } catch (e) {
                        showToast("發生錯誤：" + e, "error");
                    } finally {
                        setBtnLoading(btnLoadScreenplay, false, "📂 載入舊劇本");
                    }
                });

                storyListContainer.appendChild(item);
            });
        } catch (e) {
            storyListContainer.innerHTML = `<div class="story-empty-hint">發生錯誤：${e}</div>`;
        }
    });

    btnCloseStorySelector.addEventListener("click", () => {
        storySelectorModal.classList.add("hidden");
    });

    btnBrowseFolder.addEventListener("click", async () => {
        btnBrowseFolder.disabled = true;
        try {
            const resp = await api("select_story_folder");
            if (resp && resp.cancelled) {
                return;
            }
            if (resp && resp.error) {
                showToast(resp.error, "error");
                return;
            }
            storySelectorModal.classList.add("hidden");
            applyLoadedStory(resp.story_name, resp);
        } catch (e) {
            showToast("選取資料夾失敗：" + e, "error");
        } finally {
            btnBrowseFolder.disabled = false;
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
        const btnText = isReady ? "🎙 重新生成" : "🎙 生成語音";
        
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
                        ${btnText}
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

        // ── 場景背景音樂 BGM 選單 ─────────────────────────────
        const sfxRow = document.createElement("div");
        sfxRow.className = "sfx-row";
        sfxRow.innerHTML = `<label class="sfx-label">🎵 場景背景音樂 BGM 主題（選填，留空則不生成）</label>`;
        
        const sfxSelect = document.createElement("select");
        sfxSelect.className = "sfx-prompt-input"; // 延用樣式或在 css 中修改
        sfxSelect.style.width = "100%";
        sfxSelect.style.padding = "8px";
        sfxSelect.style.marginTop = "6px";
        sfxSelect.style.borderRadius = "6px";
        sfxSelect.style.border = "1px solid var(--border-color)";
        sfxSelect.style.background = "var(--bg-card)";
        sfxSelect.style.color = "var(--text-main)";

        // 加入空選項
        const emptyOption = document.createElement("option");
        emptyOption.value = "";
        emptyOption.textContent = "無 (No BGM)";
        sfxSelect.appendChild(emptyOption);

        // 加入 BGM 主題選項
        if (currentBgmMap && currentBgmMap.themes) {
            for (const [themeId, themeData] of Object.entries(currentBgmMap.themes)) {
                const opt = document.createElement("option");
                opt.value = themeId;
                opt.textContent = `${themeData.name} - ${themeData.prompt}`;
                sfxSelect.appendChild(opt);
            }
        }

        sfxSelect.value = scene.bgm_theme_id || "";
        
        sfxSelect.addEventListener("change", (e) => {
            currentScenes[idx].bgm_theme_id = e.target.value || null;
            markSceneStale(scene.scene_id);
            api("save_screenplay_progress", currentStory, currentScenes);
        });
        
        sfxRow.appendChild(sfxSelect);
        body.appendChild(sfxRow);

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
                let displayMsg = resp.error;
                if (displayMsg.includes("今日額度已達上限") || displayMsg.includes("今日額度已用完")) {
                    displayMsg = "AI 今日免費額度已達上限（需等待一段時間或明天重設，或更換通行證）。";
                } else if (displayMsg.includes("429") || displayMsg.includes("RESOURCE_EXHAUSTED") || displayMsg.includes("額度已達每分鐘上限")) {
                    displayMsg = "AI 聲音額度已達每分鐘上限（每分鐘最多 10 句）。系統已嘗試自動排隊重試，若仍無法生成，請稍等一分鐘後再點擊生成。";
                }
                showToast(`場景 ${sceneId} 錯誤：${displayMsg}`, "error");
                status.className = "audio-status pending";
                status.textContent = "✕ 失敗";
                if (errorDiv) {
                    errorDiv.innerHTML = "";
                    const headerRow = document.createElement("div");
                    headerRow.style.display = "flex";
                    headerRow.style.justifyContent = "space-between";
                    headerRow.style.alignItems = "flex-start";
                    headerRow.style.gap = "8px";

                    const msgDiv = document.createElement("div");
                    msgDiv.style.flex = "1";
                    msgDiv.textContent = displayMsg;
                    headerRow.appendChild(msgDiv);

                    const copyBtn = document.createElement("button");
                    copyBtn.className = "copy-err-btn";
                    copyBtn.title = "點擊複製錯誤內容";
                    copyBtn.textContent = "📋 複製";
                    copyBtn.onclick = () => {
                        copyToClipboard(resp.error || displayMsg).then(() => {
                            copyBtn.textContent = "✓ 已複製";
                            setTimeout(() => { copyBtn.textContent = "📋 複製"; }, 2000);
                        });
                    };
                    headerRow.appendChild(copyBtn);
                    errorDiv.appendChild(headerRow);

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
            let errorMsg = e.toString();
            if (errorMsg.includes("今日額度已達上限") || errorMsg.includes("今日額度已用完")) {
                errorMsg = "AI 今日免費額度已達上限（需等待一段時間或明天重設，或更換通行證）。";
            } else if (errorMsg.includes("429") || errorMsg.includes("RESOURCE_EXHAUSTED") || errorMsg.includes("額度已達每分鐘上限")) {
                errorMsg = "AI 聲音額度已達每分鐘上限（每分鐘最多 10 句）。系統已嘗試自動排隊重試，若仍無法生成，請稍等一分鐘後再點擊生成。";
            }
            showToast("發生錯誤：" + errorMsg, "error");
            status.className = "audio-status pending";
            status.textContent = "✕ 失敗";
            if (errorDiv) {
                errorDiv.innerHTML = "";
                const headerRow = document.createElement("div");
                headerRow.style.display = "flex";
                headerRow.style.justifyContent = "space-between";
                headerRow.style.alignItems = "flex-start";
                headerRow.style.gap = "8px";

                const msgDiv = document.createElement("div");
                msgDiv.style.flex = "1";
                msgDiv.textContent = errorMsg;
                headerRow.appendChild(msgDiv);

                const copyBtn = document.createElement("button");
                copyBtn.className = "copy-err-btn";
                copyBtn.title = "點擊複製錯誤內容";
                copyBtn.textContent = "📋 複製";
                copyBtn.onclick = () => {
                    copyToClipboard(e.toString() || errorMsg).then(() => {
                        copyBtn.textContent = "✓ 已複製";
                        setTimeout(() => { copyBtn.textContent = "📋 複製"; }, 2000);
                    });
                };
                headerRow.appendChild(copyBtn);
                errorDiv.appendChild(headerRow);
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
