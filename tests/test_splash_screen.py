import os
import subprocess
from unittest.mock import patch

from main import StoryForgeApi


def test_api_check_system_ready():
    with patch("infrastructure.file_storage.LocalFileStorage.get_api_key", return_value="test_key"):
        api = StoryForgeApi()
        res = api.check_system_ready()
        assert res.get("status") == "ok"
        assert res.get("ambience_count") >= 8
        assert res.get("foley_count") >= 10
        assert res.get("has_key") is True


def test_ui_splash_screen_flow():
    node_script = """
const fs = require('fs');
let appJs = fs.readFileSync('ui/app.js', 'utf8');

let domLoadHandler;
let webviewReadyHandler;
let elements = {};
let clickListeners = {};

const mockElement = (id) => {
    let classes = new Set();
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
        value: '',
        textContent: '',
        innerHTML: '',
        style: {}
    };
    if (id) elements[id] = el;
    return el;
};

// 預先建立 splash 相關元件
mockElement('splashScreen');
mockElement('splashProgressBar');
mockElement('splashStatus');
mockElement('btnSettings');
mockElement('settingsModal');

global.document = {
    addEventListener: (evt, fn) => {
        if (evt === 'DOMContentLoaded') domLoadHandler = fn;
    },
    getElementById: (id) => elements[id] || mockElement(id),
    querySelectorAll: () => [],
    createElement: (tag) => mockElement()
};

let checkSystemReadyCalled = false;
global.window = {
    addEventListener: (evt, fn) => {
        if (evt === 'pywebviewready') webviewReadyHandler = fn;
    },
    confirm: () => true,
    alert: () => {},
    pywebview: {
        api: {
            check_system_ready: async () => {
                checkSystemReadyCalled = true;
                return { status: 'ok', ambience_count: 8, foley_count: 10, has_key: false };
            },
            get_settings: async () => ({ key: '', thinking_level: 'MEDIUM', pause_seconds: 1 })
        }
    }
};
global.pywebview = global.window.pywebview;

eval(appJs);
domLoadHandler();

(async () => {
    // 驗證初始狀態：splashScreen 不應有 fade-out
    if (elements['splashScreen'].classList.contains('fade-out')) {
        console.error('初始狀態下 splashScreen 不應帶有 fade-out');
        process.exit(1);
    }

    // 觸發 pywebviewready 初始化
    if (webviewReadyHandler) {
        await webviewReadyHandler();
    }

    if (!checkSystemReadyCalled) {
        console.error('啟動流程應呼叫 check_system_ready');
        process.exit(1);
    }

    // 初始化完成後，splashScreen 應被加上 fade-out
    if (!elements['splashScreen'].classList.contains('fade-out')) {
        console.error('就緒完成後 splashScreen 應帶有 fade-out 類別');
        process.exit(1);
    }

    // 當 has_key 為 false 時，應自動開啟設定視窗（移除 settingsModal 的 hidden 類別）
    if (elements['settingsModal'].classList.contains('hidden')) {
        console.error('尚未設定通行證時，就緒後應自動開啟設定視窗');
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
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    )
    assert result.returncode == 0, f"測試未通過: {result.stderr or result.stdout}"
