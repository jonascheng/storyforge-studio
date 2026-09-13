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

const mockElement = (id) => ({
    id: id || '',
    addEventListener: (evt, fn) => {
        if (id) clickListeners[id + ':' + evt] = fn;
    },
    classList: { add: () => {}, remove: () => {} },
    appendChild: () => {},
    querySelectorAll: () => [],
    querySelector: () => mockElement(),
    scrollIntoView: () => {},
    value: 'test-story',
    textContent: '',
    style: {}
});

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
        return el;
    }
};
global.window = {
    pywebview: {
        api: {
            load_screenplay: async () => ({
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
