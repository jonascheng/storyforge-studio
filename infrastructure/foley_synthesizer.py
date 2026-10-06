from dataclasses import dataclass

import numpy as np
from pydub import AudioSegment
from scipy.signal import butter, sosfilt

SR = 48000
_rng = np.random.default_rng(42)


def _t(d: float, sr: int = SR) -> np.ndarray:
    return np.arange(int(round(d * sr))) / sr


def _env_exp(d: float, tau: float, sr: int = SR) -> np.ndarray:
    return np.exp(-_t(d, sr) / tau)


def _bp(x: np.ndarray, lo: float, hi: float, o: int = 2, sr: int = SR) -> np.ndarray:
    sos = butter(o, [lo, hi], "band", fs=sr, output="sos")
    return sosfilt(sos, x)


def _lp(x: np.ndarray, f: float, o: int = 2, sr: int = SR) -> np.ndarray:
    sos = butter(o, f, "low", fs=sr, output="sos")
    return sosfilt(sos, x)


def _hp(x: np.ndarray, f: float, o: int = 2, sr: int = SR) -> np.ndarray:
    sos = butter(o, f, "high", fs=sr, output="sos")
    return sosfilt(sos, x)


def _noise(d: float, sr: int = SR) -> np.ndarray:
    return _rng.standard_normal(int(round(d * sr)))


def _norm(x: np.ndarray, p: float = 1.0) -> np.ndarray:
    m = np.abs(x).max()
    return (x * (p / m) if m > 0 else x).astype(np.float32)


def _brown(d: float, sr: int = SR) -> np.ndarray:
    w = np.cumsum(_noise(d, sr))
    w -= np.linspace(w[0], w[-1], len(w))
    return _norm(_hp(w, 20, sr=sr))


# --- Procedural SFX DSP Generators ---


def _gen_click(v: float = 1.0, sr: int = SR) -> np.ndarray:
    d = 0.06
    tt = _t(d, sr)
    tr = _hp(_noise(d, sr), 2500, sr=sr) * _env_exp(d, 0.0015, sr)
    res = sum(
        a * np.sin(2 * np.pi * f * tt + _rng.random() * 6) * _env_exp(d, tau, sr)
        for f, a, tau in [(2900, 0.6, 0.012), (4600, 0.4, 0.008), (1500, 0.35, 0.018)]
    )
    body = np.sin(2 * np.pi * 190 * tt) * _env_exp(d, 0.01, sr) * 0.5
    return _norm(tr * 0.8 + res + body) * v


def _gen_step(v: float = 1.0, sr: int = SR) -> np.ndarray:
    d = 0.05
    tt = _t(d, sr)
    return (
        _norm(
            _hp(_noise(d, sr), 1800, sr=sr) * _env_exp(d, 0.004, sr)
            + np.sin(2 * np.pi * 2200 * tt) * _env_exp(d, 0.006, sr) * 0.5
        )
        * v
    )


def _gen_whoosh(d: float = 0.35, v: float = 1.0, sr: int = SR) -> np.ndarray:
    n = _noise(d, sr)
    tt = _t(d, sr)
    out = np.zeros_like(n)
    hop = int(sr * 0.01)
    for i in range(0, len(n), hop):
        hi = min(len(n), i + hop)
        f = 600 + 2600 * np.sin(np.pi * i / len(n))
        lo_f = max(50.0, f * 0.7)
        hi_f = min(sr * 0.45, f * 1.3)
        seg = _bp(n[max(0, i - 2000) : hi], lo_f, hi_f, sr=sr)[-(hi - i) :]
        out[i:hi] = seg
    return _norm(out * np.sin(np.pi * tt / d) ** 2) * v


def _gen_creak(v: float = 1.0, sr: int = SR) -> np.ndarray:
    d = 0.22
    tt = _t(d, sr)
    f0 = 70 + _rng.random() * 40
    saw = 2 * ((tt * f0 * (1 + 0.3 * np.sin(2 * np.pi * 9 * tt))) % 1) - 1
    return (
        _norm(
            _bp(saw, 400, 3000, sr=sr)
            * (np.abs(np.sin(2 * np.pi * 23 * tt)) ** 3)
            * np.sin(np.pi * tt / d)
        )
        * v
    )


def _gen_thump(v: float = 1.0, f: float = 70, sr: int = SR) -> np.ndarray:
    d = 0.35
    tt = _t(d, sr)
    return (
        _norm(
            np.sin(2 * np.pi * f * tt * (1 - 0.3 * tt)) * _env_exp(d, 0.07, sr)
            + _lp(_noise(d, sr), 300, sr=sr) * _env_exp(d, 0.02, sr) * 0.5
        )
        * v
    )


def _gen_crash(v: float = 1.0, sr: int = SR) -> np.ndarray:
    d = 0.9
    out = np.zeros(int(d * sr), dtype=np.float32)
    for k in range(18):
        s = int((k / 18) ** 1.4 * 0.6 * sr)
        cd = 0.09
        ctt = _t(cd, sr)
        p = (0.8 + _rng.random() * 0.6) * (0.85 + _rng.random() * 0.3)
        cx = _hp(_noise(cd, sr), 1200, sr=sr) * _env_exp(cd, 0.004, sr) + sum(
            a * np.sin(2 * np.pi * freq * p * ctt) * _env_exp(cd, tau, sr)
            for freq, a, tau in [(1200, 0.6, 0.02), (2300, 0.5, 0.012), (380, 0.5, 0.03)]
        )
        c = _norm(cx) * (0.4 + _rng.random() * 0.6)
        end_idx = min(len(out), s + len(c))
        out[s:end_idx] += c[: end_idx - s]
    out[: int(0.2 * sr)] += _lp(_noise(0.2, sr), 400, sr=sr) * _env_exp(0.2, 0.05, sr) * 0.8
    return _norm(out) * v


def _gen_heartbeat(v: float = 1.0, sr: int = SR) -> np.ndarray:
    t1 = _gen_thump(1.0, 55, sr=sr)
    t2 = _gen_thump(0.7, 50, sr=sr)
    pad = int(0.22 * sr)
    total_len = max(len(t1), pad + len(t2))
    out = np.zeros(total_len, dtype=np.float32)
    out[: len(t1)] += t1
    out[pad : pad + len(t2)] += t2
    return _norm(out) * v


def _gen_rumble(d: float = 1.5, v: float = 1.0, sr: int = SR) -> np.ndarray:
    tt = _t(d, sr)
    b = _brown(d, sr=sr)
    filtered = _lp(b, 200, sr=sr)
    envelope = np.sin(np.pi * tt / d / 2) ** 2
    return _norm(filtered * envelope) * v


def _gen_ding(v: float = 1.0, sr: int = SR) -> np.ndarray:
    d = 1.6
    tt = _t(d, sr)
    x = sum(
        a * np.sin(2 * np.pi * f * tt) * _env_exp(d, tau, sr)
        for f, a, tau in [
            (1318, 1.0, 0.6),
            (2637, 0.5, 0.35),
            (3951, 0.3, 0.2),
            (1976, 0.25, 0.5),
            (5274, 0.15, 0.1),
        ]
    )
    return _norm(x) * v


def _gen_ignite(v: float = 1.0, sr: int = SR) -> np.ndarray:
    d = 1.8
    tt = _t(d, sr)
    sub = np.sin(2 * np.pi * 45 * tt * (1 - 0.25 * tt)) * _env_exp(d, 0.5, sr)
    burst = _lp(_noise(d, sr), 1200, sr=sr) * _env_exp(d, 0.35, sr)
    return _norm(sub * 0.9 + burst) * v


@dataclass(frozen=True)
class FoleyDefinition:
    sfx_id: str
    name: str
    description: str
    duration_sec: float
    keywords: list[str]


_CATALOG: dict[str, tuple[FoleyDefinition, callable]] = {
    "creak": (
        FoleyDefinition(
            sfx_id="creak",
            name="開門吱呀聲",
            description="木門或老舊家具緩慢開啟的吱呀摩擦聲",
            duration_sec=0.22,
            keywords=["門", "開門", "關門", "吱呀", "推開", "木門"],
        ),
        lambda v, d, sr: _gen_creak(v=v, sr=sr),
    ),
    "step": (
        FoleyDefinition(
            sfx_id="step",
            name="腳步聲",
            description="鞋底踏在地面上的短促踏步聲",
            duration_sec=0.05,
            keywords=["腳步", "走路", "腳步聲", "走動", "踏步"],
        ),
        lambda v, d, sr: _gen_step(v=v, sr=sr),
    ),
    "whoosh": (
        FoleyDefinition(
            sfx_id="whoosh",
            name="呼嘯掠過聲",
            description="快速揮動手臂、利刃破空或狂風呼嘯的掠過聲",
            duration_sec=0.35,
            keywords=["風聲", "呼嘯", "揮動", "掠過", "快速", "破空"],
        ),
        lambda v, d, sr: _gen_whoosh(d=d or 0.35, v=v, sr=sr),
    ),
    "thump": (
        FoleyDefinition(
            sfx_id="thump",
            name="重擊悶響聲",
            description="重拳砸落、重物落地或沉悶撞擊聲",
            duration_sec=0.35,
            keywords=["重擊", "撞擊", "沉悶", "落地", "砸", "倒地", "擊打", "痛擊"],
        ),
        lambda v, d, sr: _gen_thump(v=v, sr=sr),
    ),
    "crash": (
        FoleyDefinition(
            sfx_id="crash",
            name="碎裂撞擊聲",
            description="器物破碎、砸落或劇烈撞擊的混亂碎裂聲",
            duration_sec=0.9,
            keywords=["破碎", "摔碎", "撞碎", "打碎", "崩塌", "碎裂"],
        ),
        lambda v, d, sr: _gen_crash(v=v, sr=sr),
    ),
    "heartbeat": (
        FoleyDefinition(
            sfx_id="heartbeat",
            name="心跳咚咚聲",
            description="緊張、恐懼或瀕死時的心臟規律跳動聲",
            duration_sec=0.57,
            keywords=["心跳", "緊張", "跳動", "害怕", "呼吸急促", "心慌"],
        ),
        lambda v, d, sr: _gen_heartbeat(v=v, sr=sr),
    ),
    "rumble": (
        FoleyDefinition(
            sfx_id="rumble",
            name="低鳴雷聲",
            description="遠方雷鳴、地震低頻震動或沉重咆哮聲",
            duration_sec=1.5,
            keywords=["雷聲", "打雷", "轟鳴", "震動", "低鳴", "地震", "雷鳴"],
        ),
        lambda v, d, sr: _gen_rumble(d=d or 1.5, v=v, sr=sr),
    ),
    "click": (
        FoleyDefinition(
            sfx_id="click",
            name="機械扣合聲",
            description="按鈕、鎖扣或金屬機關清脆扣合聲",
            duration_sec=0.06,
            keywords=["點擊", "扣合", "按鈕", "鎖", "喀嗒", "清脆"],
        ),
        lambda v, d, sr: _gen_click(v=v, sr=sr),
    ),
    "ding": (
        FoleyDefinition(
            sfx_id="ding",
            name="清脆鈴鐺聲",
            description="金屬叮聲、提示音或清脆鈴響",
            duration_sec=1.6,
            keywords=["鈴聲", "叮", "提示音", "鈴鐺", "清脆鈴聲"],
        ),
        lambda v, d, sr: _gen_ding(v=v, sr=sr),
    ),
    "ignite": (
        FoleyDefinition(
            sfx_id="ignite",
            name="火焰燃起聲",
            description="火柴劃過、火焰瞬間爆發燃燒聲",
            duration_sec=1.8,
            keywords=["火焰", "燃燒", "點燃", "著火", "火光", "火"],
        ),
        lambda v, d, sr: _gen_ignite(v=v, sr=sr),
    ),
}


class FoleySynthesizer:
    """動作擬音合成器：基於純數學 DSP 演算法合成動作擬音 (Foley SFX)。"""

    SAMPLE_RATE = SR

    @classmethod
    def list_sfx(cls) -> list[FoleyDefinition]:
        return [defn for defn, _ in _CATALOG.values()]

    @classmethod
    def get_sfx_info(cls, sfx_id: str) -> FoleyDefinition | None:
        if sfx_id not in _CATALOG:
            return None
        return _CATALOG[sfx_id][0]

    @classmethod
    def find_by_keyword(cls, keyword: str) -> FoleyDefinition | None:
        """依關鍵字搜尋最符合的動作擬音定義。"""
        if not keyword:
            return None
        kw = keyword.strip()
        # 1. 完全相符優先
        for defn, _ in _CATALOG.values():
            if kw in defn.keywords:
                return defn
        # 2. 子字串包含，以最長相符關鍵字為準
        best_match = None
        best_len = 0
        for defn, _ in _CATALOG.values():
            for k in defn.keywords:
                if k in kw or kw in k:
                    match_len = len(k)
                    if match_len > best_len:
                        best_match = defn
                        best_len = match_len
        return best_match

    @classmethod
    def synthesize_signal(
        cls, sfx_id: str, volume: float = 1.0, duration_sec: float | None = None
    ) -> tuple[np.ndarray, int]:
        """純演算法合成單聲道 float32 音訊訊號陣列。"""
        if sfx_id not in _CATALOG:
            raise ValueError(f"找不到動作音效: {sfx_id}。可用音效: {list(_CATALOG.keys())}")

        _, generator = _CATALOG[sfx_id]
        sig = generator(volume, duration_sec, cls.SAMPLE_RATE)
        return sig, cls.SAMPLE_RATE

    @classmethod
    def synthesize(
        cls, sfx_id: str, volume: float = 1.0, duration_sec: float | None = None
    ) -> AudioSegment:
        """合成指定動作音效並包裝為 pydub AudioSegment 物件。"""
        sig, sr = cls.synthesize_signal(sfx_id, volume=volume, duration_sec=duration_sec)
        clipped = np.clip(sig, -1.0, 1.0)
        int16_data = (clipped * 32767).astype(np.int16)
        return AudioSegment(
            int16_data.tobytes(),
            frame_rate=sr,
            sample_width=2,
            channels=1,
        )
