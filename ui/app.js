document.addEventListener("DOMContentLoaded", () => {
    // ── Elements ──────────────────────────────────────────────
    const btnSettings      = document.getElementById("btnSettings");
    const settingsModal    = document.getElementById("settingsModal");
    const btnCloseSettings = document.getElementById("btnCloseSettings");
    const btnSaveSettings  = document.getElementById("btnSaveSettings");
    const apiKeyInput      = document.getElementById("apiKeyInput");

    const storyInput       = document.getElementById("storyInput");
    const storyNameInput   = document.getElementById("storyNameInput");
    const btnBreakdown     = document.getElementById("btnBreakdown");

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
        const key = await api("get_api_key");
        apiKeyInput.value = key || "";
        settingsModal.classList.remove("hidden");
    });
    btnCloseSettings.addEventListener("click", () => settingsModal.classList.add("hidden"));
    btnSaveSettings.addEventListener("click", async () => {
        const key = apiKeyInput.value.trim();
        await api("save_api_key", key);
        settingsModal.classList.add("hidden");
        showToast("通行證已儲存 ✓");
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

    // ── Render Scenes ─────────────────────────────────────────
    function renderScenes() {
        scenesList.innerHTML = "";
        currentScenes.forEach((scene, idx) => renderSceneCard(scene, idx));
    }

    function renderSceneCard(scene, idx) {
        const card = document.createElement("div");
        card.className = "scene-card";
        card.id = `scene-card-${scene.scene_id}`;

        // Header
        const header = document.createElement("div");
        header.className = "scene-header";
        header.innerHTML = `
            <div class="scene-title-group">
                <span class="scene-number">場景 ${scene.scene_id}</span>
                <span class="scene-title">${scene.title}</span>
            </div>
            <div class="scene-actions">
                <span class="audio-status pending" id="status-${scene.scene_id}">
                    ○ 尚未生成
                </span>
                <button class="scene-regen-btn" id="regen-${scene.scene_id}">
                    🎙 生成語音
                </button>
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
            });

            const emotionInput = document.createElement("input");
            emotionInput.className = "emotion";
            emotionInput.value = line.emotion;
            emotionInput.title = "情緒";
            emotionInput.addEventListener("change", (e) => {
                currentScenes[idx].lines[lineIdx].emotion = e.target.value;
            });

            const textArea = document.createElement("textarea");
            textArea.value = line.text;
            textArea.title = "台詞";
            textArea.addEventListener("change", (e) => {
                currentScenes[idx].lines[lineIdx].text = e.target.value;
                // Mark audio as stale when content changes
                markSceneStale(scene.scene_id);
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

        btn.disabled = true;
        btn.textContent = "處理中...";
        card.classList.add("generating");
        card.classList.remove("has-audio");
        status.className = "audio-status working";
        status.textContent = "⟳ 生成中...";

        try {
            const sceneData = currentScenes[idx];
            const resp = await api("generate_scene_audio", sceneData, currentStory);

            if (resp.error) {
                showToast(`場景 ${sceneId} 錯誤：${resp.error}`, "error");
                status.className = "audio-status pending";
                status.textContent = "✕ 失敗";
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
