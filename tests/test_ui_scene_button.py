import subprocess
import os

def test_loaded_screenplay_scene_button_text():
    """驗證載入已有語音的舊劇本時，按鈕文字應正確顯示為『🎙 重新生成』"""
    node_script = """
const fs = require('fs');
let appJs = fs.readFileSync('ui/app.js', 'utf8');

let loadHandler;
let capturedHeaders = [];
let clickListeners = {};
let storyItemClicks = [];

const mockElement = (id) => {
    let _className = '';
    return {
        id: id || '',
        get className() { return _className; },
        set className(val) { _className = val; },
        addEventListener: (evt, fn) => {
            if (id) clickListeners[id + ':' + evt] = fn;
            if (_className === 'story-item' && evt === 'click') {
                storyItemClicks.push(fn);
            }
        },
        classList: { add: () => {}, remove: () => {} },
        appendChild: (child) => {
            if (child && child.className === 'story-item' && child._clickHandler) {
                storyItemClicks.push(child._clickHandler);
            }
        },
        querySelectorAll: () => [],
        querySelector: () => mockElement(),
        scrollIntoView: () => {},
        value: '',
        textContent: '',
        style: {}
    };
};

global.document = {
    addEventListener: (evt, fn) => { if (evt === 'DOMContentLoaded') loadHandler = fn; },
    getElementById: (id) => mockElement(id),
    createElement: (tag) => {
        const el = mockElement();
        Object.defineProperty(el, 'innerHTML', {
            set(val) {
                if (typeof val === 'string' && val.includes('scene-regen-btn')) capturedHeaders.push(val);
                this._html = val;
            },
            get() { return this._html || ''; }
        });
        const origAddEventListener = el.addEventListener;
        el.addEventListener = (evt, fn) => {
            origAddEventListener(evt, fn);
            if (evt === 'click') {
                el._clickHandler = fn;
                storyItemClicks.push(fn);
            }
        };
        return el;
    }
};
global.window = {
    confirm: () => true,
    pywebview: {
        api: {
            list_stories: async () => ({
                stories: [
                    { name: 'test-story', scene_count: 2, updated_at: '2026-09-14 08:00' }
                ]
            }),
            load_screenplay: async () => ({
                story_name: 'test-story',
                scenes: [
                    { scene_id: 1, title: '場景一', lines: [] },
                    { scene_id: 2, title: '場景二', lines: [] }
                ],
                audio_ready_ids: [1]
            })
        }
    }
};
global.pywebview = global.window.pywebview;

eval(appJs);
loadHandler();

(async () => {
    await clickListeners['btnLoadScreenplay:click']();
    // 點擊清單中的故事項目以載入
    if (storyItemClicks.length > 0) {
        await storyItemClicks[storyItemClicks.length - 1]();
    }
    if (capturedHeaders.length !== 2) {
        console.error('Expected 2 scenes rendered, got ' + capturedHeaders.length);
        process.exit(1);
    }
    const btn1 = capturedHeaders[0].match(/<button class="scene-regen-btn"[^>]*>([\\s\\S]*?)<\\/button>/)[1].trim();
    const btn2 = capturedHeaders[1].match(/<button class="scene-regen-btn"[^>]*>([\\s\\S]*?)<\\/button>/)[1].trim();
    
    if (!btn1.includes('重新生成')) {
        console.error(`場景 1 已有語音，但按鈕文字為: "${btn1}"，預期應為 "🎙 重新生成"`);
        process.exit(1);
    }
    if (!btn2.includes('生成語音')) {
        console.error(`場景 2 尚未生成語音，但按鈕文字為: "${btn2}"，預期應為 "🎙 生成語音"`);
        process.exit(1);
    }
    console.log('SUCCESS');
})().catch(err => {
    console.error(err);
    process.exit(1);
});
"""
    result = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True,
        text=True,
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    )
    assert result.returncode == 0, f"測試未通過: {result.stderr or result.stdout}"


def test_ui_error_copy_button():
    """驗證當顯示錯誤訊息時，Toast 應包含複製按鈕"""
    node_script = """
const fs = require('fs');
let appJs = fs.readFileSync('ui/app.js', 'utf8');

let loadHandler;
let toastChildren = [];
let toastClass = '';
let clickListeners = {};

const mockElement = (id) => ({
    id: id || '',
    addEventListener: (evt, fn) => {
        if (id) clickListeners[id + ':' + evt] = fn;
    },
    classList: { add: () => {}, remove: () => {} },
    appendChild: (child) => {
        if (id === 'toast') toastChildren.push(child);
    },
    querySelectorAll: () => [],
    querySelector: () => mockElement(),
    scrollIntoView: () => {},
    value: '',
    textContent: '',
    style: {}
});

const toastEl = {
    id: 'toast',
    textContent: '',
    children: [],
    appendChild: (c) => { toastChildren.push(c); },
    classList: { add: () => {}, remove: () => {} },
    set className(val) { toastClass = val; },
    get className() { return toastClass; }
};

global.document = {
    addEventListener: (evt, fn) => { if (evt === 'DOMContentLoaded') loadHandler = fn; },
    getElementById: (id) => (id === 'toast' ? toastEl : mockElement(id)),
    createElement: (tag) => {
        const el = mockElement();
        el.tagName = tag;
        return el;
    }
};
global.window = { pywebview: { api: {} } };
global.pywebview = global.window.pywebview;
global.navigator = { clipboard: { writeText: async () => {} } };

eval(appJs);
loadHandler();

// 觸發一個錯誤 Toast（例如未輸入文字點擊拆解故事）
clickListeners['btnBreakdown:click']();
// 測試是否有 toast-copy-btn
const hasCopyBtn = toastChildren.some(c => c.className === 'toast-copy-btn');
if (!hasCopyBtn) {
    console.error('Toast 應包含 class 為 toast-copy-btn 的複製按鈕');
    process.exit(1);
}
console.log('SUCCESS');
"""
    result = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True,
        text=True,
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    )
    assert result.returncode == 0, f"測試未通過: {result.stderr or result.stdout}"


def test_ui_browse_folder_and_unsaved_warning():
    """驗證：1. 輸入框有原稿時提示防呆；2. 點選瀏覽資料夾時自動載入故事"""
    node_script = """
const fs = require('fs');
let appJs = fs.readFileSync('ui/app.js', 'utf8');

let loadHandler;
let clickListeners = {};
let elements = {};
let confirmCalled = false;
let confirmReturn = true;

const mockElement = (id) => {
    let classes = new Set(['hidden']);
    let _val = '';
    const el = {
        id: id || '',
        classList: {
            add: (c) => classes.add(c),
            remove: (c) => classes.delete(c),
            contains: (c) => classes.has(c)
        },
        addEventListener: (evt, fn) => {
            if (id) clickListeners[id + ':' + evt] = fn;
        },
        appendChild: () => {},
        querySelectorAll: () => [],
        querySelector: () => mockElement(),
        scrollIntoView: () => {},
        get value() { return _val; },
        set value(v) { _val = v; },
        textContent: '',
        innerHTML: '',
        style: {}
    };
    if (id) elements[id] = el;
    return el;
};

global.document = {
    addEventListener: (evt, fn) => { if (evt === 'DOMContentLoaded') loadHandler = fn; },
    getElementById: (id) => elements[id] || mockElement(id),
    createElement: (tag) => mockElement()
};

let selectStoryFolderCalled = false;
global.window = {
    confirm: (msg) => {
        confirmCalled = true;
        return confirmReturn;
    },
    pywebview: {
        api: {
            list_stories: async () => ({ stories: [] }),
            select_story_folder: async () => {
                selectStoryFolderCalled = true;
                return {
                    story_name: '外部新故事',
                    scenes: [{ scene_id: 1, title: '第一幕', lines: [] }],
                    audio_ready_ids: []
                };
            }
        }
    }
};
global.pywebview = global.window.pywebview;

eval(appJs);
loadHandler();

(async () => {
    // 測試 1：輸入框有文字且使用者按下「取消」，視窗不應開啟
    const storyInput = elements['storyInput'];
    storyInput.value = '很久很久以前的故事原稿...';
    confirmReturn = false;
    await clickListeners['btnLoadScreenplay:click']();
    if (!confirmCalled) {
        console.error('輸入框有文字時應觸發 confirm 防呆確認');
        process.exit(1);
    }
    if (!elements['storySelectorModal'].classList.contains('hidden')) {
        console.error('使用者取消後，故事選單視窗不應開啟');
        process.exit(1);
    }

    // 測試 2：使用者確認繼續，視窗應開啟
    confirmReturn = true;
    await clickListeners['btnLoadScreenplay:click']();
    if (elements['storySelectorModal'].classList.contains('hidden')) {
        console.error('確認繼續後，故事選單視窗應開啟');
        process.exit(1);
    }

    // 測試 3：點擊「從電腦資料夾瀏覽」
    await clickListeners['btnBrowseFolder:click']();
    if (!selectStoryFolderCalled) {
        console.error('點選瀏覽資料夾應呼叫 select_story_folder');
        process.exit(1);
    }
    if (elements['storyNameInput'].value !== '外部新故事') {
        console.error('載入後故事名稱應更新為外部新故事，得到: ' + elements['storyNameInput'].value);
        process.exit(1);
    }
    if (!elements['storySelectorModal'].classList.contains('hidden')) {
        console.error('載入完成後故事選單視窗應自動關閉');
        process.exit(1);
    }

    console.log('SUCCESS');
})().catch(err => {
    console.error(err);
    process.exit(1);
});
"""
    result = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True,
        text=True,
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    )
    assert result.returncode == 0, f"測試未通過: {result.stderr or result.stdout}"

