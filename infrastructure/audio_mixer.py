import numpy as np
from pydub import AudioSegment

try:
    import static_ffmpeg

    static_ffmpeg.add_paths(weak=True)
except Exception:
    pass


class AudioMixer:
    BGM_DB = -18
    AMBIENCE_WITH_BGM_DB = -22
    AMBIENCE_STANDALONE_DB = -18
    DEFAULT_DUCK_DB = 8.0
    FADE_IN_MS = 2000
    FADE_OUT_MS = 2000
    CROSSFADE_MS = 1000

    @classmethod
    def apply_ducking(
        cls,
        audio: AudioSegment,
        cues: list,
        duck_db: float = 8.0,
        attack_ms: int = 60,
        release_ms: int = 300,
        default_duration_ms: int = 300,
    ) -> AudioSegment:
        """智慧音樂讓路 (Audio Ducking)：在指定時間點與區間內平滑降低音量，結束後平滑淡回。"""
        if not cues or len(audio) == 0:
            return audio

        total_ms = len(audio)
        sr = audio.frame_rate
        raw_samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        num_frames = len(raw_samples) // audio.channels

        duck_linear = float(10 ** (-abs(duck_db) / 20.0))
        gain = np.ones(num_frames, dtype=np.float32)

        for cue in cues:
            start_ms = 0
            dur_ms = default_duration_ms

            if isinstance(cue, tuple | list) and len(cue) >= 2:
                start_ms, dur_ms = cue[0], cue[1]
            elif hasattr(cue, "timestamp_ms"):
                start_ms = getattr(cue, "timestamp_ms", 0)
                sfx_id = getattr(cue, "sfx_id", None)
                if sfx_id:
                    try:
                        from infrastructure.foley_synthesizer import FoleySynthesizer

                        info = FoleySynthesizer.get_sfx_info(sfx_id)
                        if info:
                            dur_ms = int(info.duration_sec * 1000)
                    except Exception:
                        pass
            elif hasattr(cue, "start_ms"):
                start_ms = getattr(cue, "start_ms", 0)
                dur_ms = getattr(cue, "duration_ms", default_duration_ms)

            if start_ms >= total_ms or (start_ms + dur_ms) <= 0:
                continue

            s = max(0, min(num_frames, int(round((start_ms / 1000.0) * sr))))
            e = max(0, min(num_frames, int(round(((start_ms + dur_ms) / 1000.0) * sr))))
            a_start = max(0, s - int(round((attack_ms / 1000.0) * sr)))
            r_end = min(num_frames, e + int(round((release_ms / 1000.0) * sr)))

            # Attack: 平滑淡出 (1.0 -> duck_linear)
            if s > a_start:
                r = np.linspace(0, 1, s - a_start, endpoint=False, dtype=np.float32)
                gain[a_start:s] = np.minimum(gain[a_start:s], 1.0 - (1.0 - duck_linear) * r)

            # Hold: 維持讓路音量
            if e > s:
                gain[s:e] = np.minimum(gain[s:e], duck_linear)

            # Release: 平滑淡回 (duck_linear -> 1.0)
            if r_end > e:
                r = np.linspace(0, 1, r_end - e, endpoint=True, dtype=np.float32)
                gain[e:r_end] = np.minimum(
                    gain[e:r_end], duck_linear + (1.0 - duck_linear) * (r**2)
                )

        if audio.channels == 2:
            samples = raw_samples.reshape(-1, 2)
            ducked = samples * gain[: len(samples), None]
            int16_samples = np.clip(ducked.reshape(-1), -32768, 32767).astype(np.int16)
        else:
            ducked = raw_samples * gain[: len(raw_samples)]
            int16_samples = np.clip(ducked, -32768, 32767).astype(np.int16)

        return AudioSegment(
            int16_samples.tobytes(),
            frame_rate=audio.frame_rate,
            sample_width=audio.sample_width,
            channels=audio.channels,
        )

    @classmethod
    def build_looped_audio(
        cls, segment: AudioSegment, target_ms: int, crossfade_ms: int = 1000
    ) -> AudioSegment:
        """循環拼接音訊直到長度達 target_ms，並透過 crossfade 平滑過渡。"""
        if len(segment) >= target_ms:
            return segment[:target_ms]
        result = segment
        cf = min(crossfade_ms, len(segment) - 1)
        while len(result) < target_ms:
            result = result.append(segment, crossfade=cf)
        return result[:target_ms]

    @classmethod
    def mix_scene_layers(
        cls,
        dialogue: AudioSegment,
        bgm: AudioSegment | None = None,
        ambience: AudioSegment | None = None,
        foley_track: AudioSegment | None = None,
        foley_cues: list | None = None,
        duck_db: float = DEFAULT_DUCK_DB,
    ) -> AudioSegment:
        """四層混音管道：對白（頂層 0 dB）+ 動作擬音 + 配樂（中層 -18 dB，智慧讓路）+ 環境音（底層 -22 dB / 無配樂時 -18 dB）。"""
        dialogue_ms = len(dialogue)
        if dialogue_ms == 0:
            return dialogue

        has_bgm = bgm is not None and len(bgm) > 0
        has_ambience = ambience is not None and len(ambience) > 0
        has_foley = foley_track is not None and len(foley_track) > 0

        if not has_bgm and not has_ambience and not has_foley:
            return dialogue

        # 1. 處理配樂 (BGM) 並依動作音效 (Foley Cues) 套用智慧讓路
        bgm_track = None
        if has_bgm:
            looped_bgm = cls.build_looped_audio(bgm, dialogue_ms, cls.CROSSFADE_MS)
            if foley_cues:
                looped_bgm = cls.apply_ducking(looped_bgm, cues=foley_cues, duck_db=duck_db)
            bgm_track = (looped_bgm + cls.BGM_DB).fade_in(cls.FADE_IN_MS).fade_out(cls.FADE_OUT_MS)

        # 2. 處理環境音 (Ambience)
        ambience_track = None
        if has_ambience:
            amb_db = cls.AMBIENCE_WITH_BGM_DB if has_bgm else cls.AMBIENCE_STANDALONE_DB
            looped_amb = cls.build_looped_audio(ambience, dialogue_ms, cls.CROSSFADE_MS)
            ambience_track = (looped_amb + amb_db).fade_in(cls.FADE_IN_MS).fade_out(cls.FADE_OUT_MS)

        # 3. 疊加底層伴奏與環境音
        if bgm_track is not None and ambience_track is not None:
            bg_track = bgm_track.overlay(ambience_track)
        elif bgm_track is not None:
            bg_track = bgm_track
        elif ambience_track is not None:
            bg_track = ambience_track
        else:
            bg_track = AudioSegment.silent(duration=dialogue_ms)

        # 4. 疊加動作擬音軌道 (Foley)
        if has_foley:
            bg_track = bg_track.overlay(foley_track)

        # 5. 對齊長度並以對白覆蓋在最頂層
        max_len = max(len(bg_track), dialogue_ms)
        bg_track_padded = bg_track + AudioSegment.silent(duration=max_len - len(bg_track))
        dialogue_padded = dialogue + AudioSegment.silent(duration=max_len - dialogue_ms)

        return bg_track_padded.overlay(dialogue_padded)

    @staticmethod
    def mix(scene_audio_paths: list[str], output_path: str, pause_seconds: int = 1) -> str:
        if not scene_audio_paths:
            raise ValueError("至少需要一個場景才能拼接。")

        combined = AudioSegment.empty()
        silence = AudioSegment.silent(duration=pause_seconds * 1000)
        for path in scene_audio_paths:
            segment = AudioSegment.from_mp3(path)
            combined += segment
            combined += silence

        combined.export(output_path, format="mp3")
        return output_path
