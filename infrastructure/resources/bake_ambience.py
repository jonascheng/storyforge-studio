import math
import os
import random

from pydub import AudioSegment, effects, generators

try:
    import static_ffmpeg

    static_ffmpeg.add_paths(weak=True)
except Exception:
    pass

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ambience")
os.makedirs(OUT_DIR, exist_ok=True)
SR = 44100
DUR_MS = 8000  # 8 秒基礎循環片段


def _create_rain() -> AudioSegment:
    """雨聲：細密雨絲聲，中高頻平滑白噪音 + 微小雨滴輕響。"""
    noise = generators.WhiteNoise().to_audio_segment(duration=DUR_MS, volume=-12)
    filtered = effects.low_pass_filter(noise, 2400)
    filtered = effects.high_pass_filter(filtered, 300)
    return filtered - 4


def _create_wind() -> AudioSegment:
    """風聲：呼嘯陣風，低通雜訊搭配緩慢週期性音量湧動。"""
    noise = generators.WhiteNoise().to_audio_segment(duration=DUR_MS, volume=-10)
    filtered = effects.low_pass_filter(noise, 500)
    filtered = effects.high_pass_filter(filtered, 70)
    # 疊加緩慢的陣風呼吸感（分塊調整增益）
    chunk_len = 200
    chunks = []
    num_chunks = DUR_MS // chunk_len
    for i in range(num_chunks):
        t = (i * chunk_len) / 1000.0
        # 4 秒一個微風湧動週期
        gain_db = 4.0 * math.sin(2 * math.pi * t / 4.0)
        c = filtered[i * chunk_len : (i + 1) * chunk_len] + gain_db
        chunks.append(c)
    combined = AudioSegment.empty()
    for c in chunks:
        combined += c
    return combined - 6


def _create_forest() -> AudioSegment:
    """森林：柔和微風墊底 + 隨機清脆鳥鳴聲。"""
    # 微風墊底
    breeze = generators.WhiteNoise().to_audio_segment(duration=DUR_MS, volume=-24)
    breeze = effects.low_pass_filter(breeze, 1200)
    breeze = effects.high_pass_filter(breeze, 200)

    # 鳥鳴：高頻短促音調 (3000 ~ 4200 Hz)
    rng = random.Random(42)
    birds = AudioSegment.silent(duration=DUR_MS)
    for _ in range(8):
        pos = rng.randint(500, DUR_MS - 800)
        base_f = rng.randint(3200, 4200)
        chirp_len = rng.randint(80, 150)
        chirp = generators.Sine(base_f).to_audio_segment(duration=chirp_len, volume=-18)
        chirp = chirp.fade_in(15).fade_out(25)
        birds = birds.overlay(chirp, position=pos)
        # 偶爾雙音
        if rng.random() > 0.4:
            chirp2 = generators.Sine(base_f + 400).to_audio_segment(
                duration=chirp_len - 20, volume=-20
            )
            chirp2 = chirp2.fade_in(15).fade_out(25)
            birds = birds.overlay(chirp2, position=pos + 120)

    return breeze.overlay(birds) - 4


def _create_night() -> AudioSegment:
    """夜晚：靜夜微底噪 + 規律節奏的夏夜蟋蟀鳴叫。"""
    tone = generators.WhiteNoise().to_audio_segment(duration=DUR_MS, volume=-30)
    tone = effects.low_pass_filter(tone, 800)

    # 蟋蟀鳴叫：高頻 (4500 Hz)，規律脈衝組
    crickets = AudioSegment.silent(duration=DUR_MS)
    pulse_dur = 40
    pulse_gap = 50
    # 每 1.2 秒一組鳴叫
    for t_start in range(200, DUR_MS - 600, 1200):
        for p in range(4):
            pos = t_start + p * (pulse_dur + pulse_gap)
            chirp = generators.Sine(4600).to_audio_segment(duration=pulse_dur, volume=-22)
            chirp = chirp.fade_in(8).fade_out(8)
            crickets = crickets.overlay(chirp, position=pos)

    return tone.overlay(crickets) - 6


def _create_fireplace() -> AudioSegment:
    """壁爐：低沉溫暖的燃燒悶響 + 木柴偶爾爆開的劈啪聲。"""
    rumble = generators.WhiteNoise().to_audio_segment(duration=DUR_MS, volume=-18)
    rumble = effects.low_pass_filter(rumble, 250)

    crackle = AudioSegment.silent(duration=DUR_MS)
    rng = random.Random(7)
    for _ in range(16):
        pos = rng.randint(100, DUR_MS - 200)
        pop_len = rng.randint(25, 60)
        pop_noise = generators.WhiteNoise().to_audio_segment(duration=pop_len, volume=-12)
        pop_noise = effects.high_pass_filter(pop_noise, 1500)
        pop_noise = pop_noise.fade_in(3).fade_out(15)
        crackle = crackle.overlay(pop_noise, position=pos)

    return rumble.overlay(crackle) - 4


def _create_sea() -> AudioSegment:
    """海浪：潮汐波濤起伏，5 秒一次海浪湧上岸的深沉白噪音。"""
    noise = generators.WhiteNoise().to_audio_segment(duration=DUR_MS, volume=-12)
    filtered = effects.low_pass_filter(noise, 750)
    filtered = effects.high_pass_filter(filtered, 90)

    chunk_len = 200
    chunks = []
    num_chunks = DUR_MS // chunk_len
    for i in range(num_chunks):
        t = (i * chunk_len) / 1000.0
        # 5 秒一波海浪
        gain_db = 6.0 * math.sin(2 * math.pi * t / 5.0)
        c = filtered[i * chunk_len : (i + 1) * chunk_len] + gain_db
        chunks.append(c)
    combined = AudioSegment.empty()
    for c in chunks:
        combined += c
    return combined - 6


def _create_room() -> AudioSegment:
    """安靜室內：極輕微的房間空氣感底噪，平靜安全。"""
    noise = generators.WhiteNoise().to_audio_segment(duration=DUR_MS, volume=-32)
    filtered = effects.low_pass_filter(noise, 400)
    return filtered - 6


def _create_cafe() -> AudioSegment:
    """咖啡廳：溫暖低頻底噪 + 偶爾清脆瓷杯敲擊微聲。"""
    murmur = generators.WhiteNoise().to_audio_segment(duration=DUR_MS, volume=-20)
    murmur = effects.low_pass_filter(murmur, 650)
    murmur = effects.high_pass_filter(murmur, 180)

    clinks = AudioSegment.silent(duration=DUR_MS)
    rng = random.Random(99)
    for _ in range(4):
        pos = rng.randint(1000, DUR_MS - 1000)
        freq = rng.randint(2200, 3100)
        clink = generators.Sine(freq).to_audio_segment(duration=80, volume=-22)
        clink = clink.fade_in(5).fade_out(40)
        clinks = clinks.overlay(clink, position=pos)

    return murmur.overlay(clinks) - 6


GENERATORS = {
    "rain": _create_rain,
    "wind": _create_wind,
    "forest": _create_forest,
    "night": _create_night,
    "fireplace": _create_fireplace,
    "sea": _create_sea,
    "room": _create_room,
    "cafe": _create_cafe,
}


def bake_all(output_dir: str = OUT_DIR):
    os.makedirs(output_dir, exist_ok=True)
    for name, gen_fn in GENERATORS.items():
        out_path = os.path.join(output_dir, f"{name}.mp3")
        segment = gen_fn()
        # 確保首尾 500ms 平滑，方便後續循環
        segment = segment.fade_in(500).fade_out(500)
        segment.export(out_path, format="mp3", bitrate="64k")
        size = os.path.getsize(out_path)
        print(f"Baked {name}.mp3 -> {size} bytes")


if __name__ == "__main__":
    bake_all()
