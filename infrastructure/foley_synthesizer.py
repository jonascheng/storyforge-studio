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


def _gen_click(v: float = 1.0, d: float | None = None, sr: int = SR) -> np.ndarray:
    """精準清脆的機械鎖扣與機關扣合聲 (0.14s)"""
    dur = d or 0.14
    tt = _t(dur, sr)
    sig = np.zeros(len(tt), dtype=np.float32)

    c1_d = 0.06
    c1_tt = _t(c1_d, sr)
    c1 = (
        _hp(_noise(c1_d, sr), 3000, sr=sr) * _env_exp(c1_d, 0.002, sr) * 0.8
        + np.sin(2 * np.pi * 2400 * c1_tt) * _env_exp(c1_d, 0.01, sr) * 0.5
    )
    sig[: len(c1)] += c1

    c2_start = int(0.032 * sr)
    c2_d = 0.09
    c2_tt = _t(c2_d, sr)
    c2 = (
        _hp(_noise(c2_d, sr), 2200, sr=sr) * _env_exp(c2_d, 0.003, sr) * 1.1
        + np.sin(2 * np.pi * 3200 * c2_tt) * _env_exp(c2_d, 0.012, sr) * 0.6
        + np.sin(2 * np.pi * 1450 * c2_tt) * _env_exp(c2_d, 0.025, sr) * 0.4
        + np.sin(2 * np.pi * 4800 * c2_tt) * _env_exp(c2_d, 0.008, sr) * 0.3
    )
    end_idx = min(len(sig), c2_start + len(c2))
    sig[c2_start:end_idx] += c2[: end_idx - c2_start]
    return _norm(sig) * v


def _gen_step(v: float = 1.0, d: float | None = None, sr: int = SR) -> np.ndarray:
    """紮實清晰的踏步聲：鞋跟觸地 + 鞋掌著地 + 地面摩擦 (0.42s，支援長時長多步步態)"""
    if d and d >= 1.0:
        total_d = d
        sig = np.zeros(int(round(total_d * sr)), dtype=np.float32)
        step_interval = 0.70
        step_times = np.arange(0.0, max(0.1, total_d - 0.35), step_interval)
        for idx, st in enumerate(step_times):
            h_d = 0.18
            h_tt = _t(h_d, sr)
            pitch_mod = 1.0 if idx % 2 == 0 else 1.08
            heel_thump = np.sin(
                2 * np.pi * (160 * pitch_mod - 50 * (h_tt / h_d)) * h_tt
            ) * _env_exp(h_d, 0.025, sr)
            heel_grit = _bp(_noise(h_d, sr), 700, 2800, sr=sr) * _env_exp(h_d, 0.016, sr) * 0.7
            h_start = int(st * sr)
            sig[h_start : h_start + len(h_tt)] += heel_thump * 1.2 + heel_grit

            t_start = int((st + 0.11) * sr)
            t_d = 0.28
            t_tt = _t(t_d, sr)
            toe_thump = np.sin(2 * np.pi * (130 * pitch_mod - 40 * (t_tt / t_d)) * t_tt) * _env_exp(
                t_d, 0.04, sr
            )
            toe_grit = _bp(_noise(t_d, sr), 500, 3400, sr=sr) * _env_exp(t_d, 0.035, sr) * 0.9
            end_idx = min(len(sig), t_start + len(t_tt))
            sig[t_start:end_idx] += (toe_thump * 1.0 + toe_grit)[: end_idx - t_start]
        return _norm(sig) * v

    dur = d or 0.42
    tt = _t(dur, sr)
    sig = np.zeros(len(tt), dtype=np.float32)
    h_d = 0.18
    h_tt = _t(h_d, sr)
    heel_thump = np.sin(2 * np.pi * (160 - 50 * (h_tt / h_d)) * h_tt) * _env_exp(h_d, 0.025, sr)
    heel_grit = _bp(_noise(h_d, sr), 800, 2600, sr=sr) * _env_exp(h_d, 0.015, sr) * 0.7
    sig[: len(h_tt)] += heel_thump * 1.2 + heel_grit

    t_start = int(0.11 * sr)
    t_d = 0.28
    t_tt = _t(t_d, sr)
    toe_thump = np.sin(2 * np.pi * (130 - 40 * (t_tt / t_d)) * t_tt) * _env_exp(t_d, 0.04, sr)
    toe_grit = _bp(_noise(t_d, sr), 600, 3200, sr=sr) * _env_exp(t_d, 0.035, sr) * 0.9
    end_idx = min(len(sig), t_start + len(t_tt))
    sig[t_start:end_idx] += (toe_thump * 1.0 + toe_grit)[: end_idx - t_start]
    return _norm(sig) * v


def _gen_whoosh(v: float = 1.0, d: float | None = None, sr: int = SR) -> np.ndarray:
    """疾風掠過、利刃破空的生動呼嘯聲 (0.65s)"""
    dur = d or 0.65
    tt = _t(dur, sr)
    n = _noise(dur, sr)
    b = _brown(dur, sr)
    f_center = 350.0 + 2200.0 * (np.sin(np.pi * tt / dur) ** 1.8)
    env = np.where(tt < 0.25 * dur, (tt / (0.25 * dur)) ** 2, ((dur - tt) / (0.75 * dur)) ** 1.5)
    air_sweep = np.zeros_like(n)
    hop = int(sr * 0.005)
    for i in range(0, len(n), hop):
        hi = min(len(n), i + hop)
        fc = f_center[i]
        seg = _bp(
            n[max(0, i - 1200) : hi],
            max(50.0, fc * 0.6),
            min(sr * 0.48, fc * 1.5),
            sr=sr,
        )[-(hi - i) :]
        air_sweep[i:hi] = seg
    sub_rush = _lp(b, 400, sr=sr) * env * 0.8
    sig = air_sweep * env + sub_rush
    return _norm(sig) * v


def _gen_creak(v: float = 1.0, d: float | None = None, sr: int = SR) -> np.ndarray:
    """厚重木門伴隨金屬鉸鏈摩擦的開門吱呀聲 (0.85s)"""
    dur = d or 0.85
    tt = _t(dur, sr)
    f_curve = 85.0 + 160.0 * np.sin(np.pi * tt / dur) ** 0.8 + 25.0 * np.sin(2 * np.pi * 12 * tt)
    phase = 2 * np.pi * np.cumsum(f_curve) / sr
    saw = 2 * ((phase / (2 * np.pi)) % 1.0) - 1.0
    stiction = np.abs(np.sin(2 * np.pi * 19 * tt + 0.5 * np.sin(2 * np.pi * 4 * tt))) ** 2.5
    wood_body = _bp(saw * stiction, 180, 750, sr=sr) * 1.8
    hinge_grit = _bp(_noise(dur, sr), 1400, 3800, sr=sr) * stiction * 0.6
    env = np.sin(np.pi * tt / dur) ** 0.6
    sig = (wood_body + hinge_grit) * env
    return _norm(sig) * v


def _gen_thump(v: float = 1.0, d: float | None = None, f: float = 95.0, sr: int = SR) -> np.ndarray:
    """具有震撼打擊力與中頻穿透力的重擊悶響 (0.50s)"""
    dur = d or 0.50
    tt = _t(dur, sr)
    snap = _hp(_noise(dur, sr), 1500, sr=sr) * _env_exp(dur, 0.006, sr) * 0.7
    f_drop = 220.0 * np.exp(-tt / 0.04) + f
    punch = np.sin(2 * np.pi * f_drop * tt) * _env_exp(dur, 0.08, sr) * 1.4
    sub = np.sin(2 * np.pi * 65.0 * tt) * _env_exp(dur, 0.20, sr) * 0.9
    body_noise = _lp(_noise(dur, sr), 280, sr=sr) * _env_exp(dur, 0.07, sr) * 0.6
    sig = snap + punch + sub + body_noise
    return _norm(sig) * v


def _gen_crash(v: float = 1.0, d: float | None = None, sr: int = SR) -> np.ndarray:
    """物品劇烈破裂砸碎聲：爆裂起音 + 重擊落地 + 瓷器碎屑四濺殘響 (1.20s)"""
    dur = d or 1.20
    tt = _t(dur, sr)
    sig = np.zeros(len(tt), dtype=np.float32)
    blast = _hp(_noise(dur, sr), 800, sr=sr) * _env_exp(dur, 0.08, sr) * 1.5
    thud = np.sin(2 * np.pi * 110.0 * tt) * _env_exp(dur, 0.12, sr) * 1.2
    sig += blast + thud
    chimes = sum(
        0.4 * np.sin(2 * np.pi * freq * tt) * _env_exp(dur, tau, sr)
        for freq, tau in [(2100, 0.15), (3400, 0.22), (4800, 0.18), (1650, 0.25)]
    )
    sig += chimes
    for k in range(12):
        s_time = 0.08 + (k / 12.0) ** 1.3 * 0.75
        s_idx = int(s_time * sr)
        if s_idx >= len(sig):
            continue
        c_d = 0.08
        c_tt = _t(c_d, sr)
        f_shard = 1800.0 + _rng.random() * 3200.0
        shard_hit = (
            np.sin(2 * np.pi * f_shard * c_tt)
            * _env_exp(c_d, 0.015, sr)
            * (0.3 + _rng.random() * 0.4)
        )
        shard_grit = _hp(_noise(c_d, sr), 2400, sr=sr) * _env_exp(c_d, 0.008, sr) * 0.2
        frag = (shard_hit + shard_grit) * (_rng.random() * 0.6 + 0.4)
        e_idx = min(len(sig), s_idx + len(frag))
        sig[s_idx:e_idx] += frag[: e_idx - s_idx]
    return _norm(sig) * v


def _gen_heartbeat(v: float = 1.0, d: float | None = None, sr: int = SR) -> np.ndarray:
    """真實雙重規律心跳聲 (Lub-Dub)：具備胸腔共鳴與緊張迫促感 (1.35s)"""
    dur = d or 1.35
    tt = _t(dur, sr)
    sig = np.zeros(len(tt), dtype=np.float32)

    def single_lub_dub(start_sec: float, amp: float = 1.0):
        l_d = 0.22
        l_tt = _t(l_d, sr)
        lub = (
            np.sin(2 * np.pi * (140 - 55 * (l_tt / l_d)) * l_tt) * _env_exp(l_d, 0.065, sr) * 1.3
            + np.sin(2 * np.pi * 65 * l_tt) * _env_exp(l_d, 0.09, sr) * 0.9
            + _lp(_noise(l_d, sr), 220, sr=sr) * _env_exp(l_d, 0.05, sr) * 0.5
        ) * amp
        idx_l = int(start_sec * sr)
        end_l = min(len(sig), idx_l + len(lub))
        sig[idx_l:end_l] += lub[: end_l - idx_l]

        d_d = 0.18
        d_tt = _t(d_d, sr)
        dub = (
            (
                np.sin(2 * np.pi * (165 - 60 * (d_tt / d_d)) * d_tt) * _env_exp(d_d, 0.05, sr) * 1.1
                + np.sin(2 * np.pi * 75 * d_tt) * _env_exp(d_d, 0.07, sr) * 0.7
                + _lp(_noise(d_d, sr), 280, sr=sr) * _env_exp(d_d, 0.04, sr) * 0.4
            )
            * amp
            * 0.85
        )
        idx_d = int((start_sec + 0.18) * sr)
        end_d = min(len(sig), idx_d + len(dub))
        sig[idx_d:end_d] += dub[: end_d - idx_d]

    single_lub_dub(0.05, 1.0)
    if dur >= 1.0:
        single_lub_dub(0.68, 0.9)
    if dur >= 2.0:
        single_lub_dub(1.63, 0.85)
    return _norm(sig) * v


def _gen_rumble(v: float = 1.0, d: float | None = None, sr: int = SR) -> np.ndarray:
    """遠方雷鳴與地鳴翻滾聲 (Rolling Thunder)：劈裂前導 + 波浪巨湧 + 遠山回響 (2.60s)"""
    dur = d or 2.60
    tt = _t(dur, sr)
    b = _brown(dur, sr)
    n = _noise(dur, sr)
    wave1 = np.exp(-(((tt - 0.5) / 0.45) ** 2)) * 1.2
    wave2 = np.exp(-(((tt - 1.4) / 0.70) ** 2)) * 0.9
    trail = np.exp(-tt / 1.6) * 0.4
    rumble_env = wave1 + wave2 + trail
    body = _bp(b, 45, 320, sr=sr) * rumble_env
    crackle = _bp(n, 1200, 4500, sr=sr) * (_rng.random(len(tt)) > 0.992) * 2.5 * np.exp(-tt / 0.8)
    sig = body * 1.5 + crackle * 0.4
    return _norm(sig) * v


def _gen_ding(v: float = 1.0, d: float | None = None, sr: int = SR) -> np.ndarray:
    """通透空靈的金屬銅鈴聲：清亮敲擊瞬態 + 拍頻微顫 + 悠長泛音 (2.20s)"""
    dur = d or 2.20
    tt = _t(dur, sr)
    strike = _hp(_noise(dur, sr), 4000, sr=sr) * _env_exp(dur, 0.004, sr) * 0.5
    f0 = 1320.0
    f0_beat = 1323.5
    tones = (
        0.9 * np.sin(2 * np.pi * f0 * tt) * _env_exp(dur, 0.85, sr)
        + 0.5 * np.sin(2 * np.pi * f0_beat * tt) * _env_exp(dur, 0.85, sr)
        + 0.45 * np.sin(2 * np.pi * (f0 * 2.01) * tt) * _env_exp(dur, 0.55, sr)
        + 0.30 * np.sin(2 * np.pi * (f0 * 3.02) * tt) * _env_exp(dur, 0.35, sr)
        + 0.20 * np.sin(2 * np.pi * (f0 * 4.05) * tt) * _env_exp(dur, 0.20, sr)
        + 0.15 * np.sin(2 * np.pi * (f0 * 5.8) * tt) * _env_exp(dur, 0.12, sr)
    )
    sig = strike + tones
    return _norm(sig) * v


def _gen_ignite(v: float = 1.0, d: float | None = None, sr: int = SR) -> np.ndarray:
    """火柴劃擦與火焰蓬然爆燃聲：劃擦摩擦 + 空氣吸捲 + 火焰燃燒劈啪 (1.90s)"""
    dur = d or 1.90
    tt = _t(dur, sr)
    sig = np.zeros(len(tt), dtype=np.float32)
    s_d = 0.12
    s_tt = _t(s_d, sr)
    strike = (
        _bp(_noise(s_d, sr), 1600, 5500, sr=sr) * np.sin(np.pi * s_tt / s_d) ** 0.5 * 1.2
        + np.sin(2 * np.pi * 950 * s_tt) * _env_exp(s_d, 0.04, sr) * 0.4
    )
    sig[: len(strike)] += strike

    f_start = int(0.08 * sr)
    f_d = 0.75
    f_tt = _t(f_d, sr)
    f_env = np.sin(np.pi * f_tt / f_d) ** 1.5
    f_whoosh = _bp(_noise(f_d, sr), 220, 1400, sr=sr) * f_env * 1.5
    f_sub = np.sin(2 * np.pi * (70 - 20 * (f_tt / f_d)) * f_tt) * _env_exp(f_d, 0.25, sr) * 0.9
    end_f = min(len(sig), f_start + len(f_tt))
    sig[f_start:end_f] += (f_whoosh + f_sub)[: end_f - f_start]

    c_start = int(0.35 * sr)
    c_len = len(sig) - c_start
    c_dur = c_len / sr
    flame_hum = _lp(_noise(c_dur, sr), 450, sr=sr) * _env_exp(c_dur, 0.6, sr) * 0.5
    crackles = (
        _bp(_noise(c_dur, sr), 2000, 7000, sr=sr)
        * (_rng.random(c_len) > 0.995)
        * 1.5
        * _env_exp(c_dur, 0.5, sr)
    )
    sig[c_start:] += flame_hum + crackles
    return _norm(sig) * v


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
            duration_sec=0.85,
            keywords=["門", "開門", "關門", "吱呀", "推開", "木門"],
        ),
        lambda v, d, sr: _gen_creak(v=v, d=d, sr=sr),
    ),
    "step": (
        FoleyDefinition(
            sfx_id="step",
            name="腳步聲",
            description="鞋底踏在地面上的短促踏步聲",
            duration_sec=0.42,
            keywords=["腳步", "走路", "腳步聲", "走動", "踏步"],
        ),
        lambda v, d, sr: _gen_step(v=v, d=d, sr=sr),
    ),
    "whoosh": (
        FoleyDefinition(
            sfx_id="whoosh",
            name="呼嘯掠過聲",
            description="快速揮動手臂、利刃破空或狂風呼嘯的掠過聲",
            duration_sec=0.65,
            keywords=["風聲", "呼嘯", "揮動", "掠過", "快速", "破空"],
        ),
        lambda v, d, sr: _gen_whoosh(v=v, d=d, sr=sr),
    ),
    "thump": (
        FoleyDefinition(
            sfx_id="thump",
            name="重擊悶響聲",
            description="重拳砸落、重物落地或沉悶撞擊聲",
            duration_sec=0.50,
            keywords=["重擊", "撞擊", "沉悶", "落地", "砸", "倒地", "擊打", "痛擊"],
        ),
        lambda v, d, sr: _gen_thump(v=v, d=d, sr=sr),
    ),
    "crash": (
        FoleyDefinition(
            sfx_id="crash",
            name="碎裂撞擊聲",
            description="器物破碎、砸落或劇烈撞擊的混亂碎裂聲",
            duration_sec=1.20,
            keywords=["破碎", "摔碎", "撞碎", "打碎", "崩塌", "碎裂"],
        ),
        lambda v, d, sr: _gen_crash(v=v, d=d, sr=sr),
    ),
    "heartbeat": (
        FoleyDefinition(
            sfx_id="heartbeat",
            name="心跳咚咚聲",
            description="緊張、恐懼或瀕死時的心臟規律跳動聲",
            duration_sec=1.35,
            keywords=["心跳", "緊張", "跳動", "害怕", "呼吸急促", "心慌"],
        ),
        lambda v, d, sr: _gen_heartbeat(v=v, d=d, sr=sr),
    ),
    "rumble": (
        FoleyDefinition(
            sfx_id="rumble",
            name="低鳴雷聲",
            description="遠方雷鳴、地震低頻震動或沉重咆哮聲",
            duration_sec=2.60,
            keywords=["雷聲", "打雷", "轟鳴", "震動", "低鳴", "地震", "雷鳴"],
        ),
        lambda v, d, sr: _gen_rumble(v=v, d=d, sr=sr),
    ),
    "click": (
        FoleyDefinition(
            sfx_id="click",
            name="機械扣合聲",
            description="按鈕、鎖扣或金屬機關清脆扣合聲",
            duration_sec=0.14,
            keywords=["點擊", "扣合", "按鈕", "鎖", "喀嗒", "清脆"],
        ),
        lambda v, d, sr: _gen_click(v=v, d=d, sr=sr),
    ),
    "ding": (
        FoleyDefinition(
            sfx_id="ding",
            name="清脆鈴鐺聲",
            description="金屬叮聲、提示音或清脆鈴響",
            duration_sec=2.20,
            keywords=["鈴聲", "叮", "提示音", "鈴鐺", "清脆鈴聲"],
        ),
        lambda v, d, sr: _gen_ding(v=v, d=d, sr=sr),
    ),
    "ignite": (
        FoleyDefinition(
            sfx_id="ignite",
            name="火焰燃起聲",
            description="火柴劃過、火焰瞬間爆發燃燒聲",
            duration_sec=1.90,
            keywords=["火焰", "燃燒", "點燃", "著火", "火光", "火"],
        ),
        lambda v, d, sr: _gen_ignite(v=v, d=d, sr=sr),
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
