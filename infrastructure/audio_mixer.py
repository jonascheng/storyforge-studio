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
    FADE_IN_MS = 2000
    FADE_OUT_MS = 2000
    CROSSFADE_MS = 1000

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
    ) -> AudioSegment:
        """三層混音管道：對白（頂層 0 dB）+ 配樂（中層 -18 dB）+ 環境音（底層 -22 dB / 無配樂時 -18 dB）。"""
        dialogue_ms = len(dialogue)
        if dialogue_ms == 0:
            return dialogue

        has_bgm = bgm is not None and len(bgm) > 0
        has_ambience = ambience is not None and len(ambience) > 0

        if not has_bgm and not has_ambience:
            return dialogue

        # 1. 處理配樂 (BGM)
        bgm_track = None
        if has_bgm:
            looped_bgm = cls.build_looped_audio(bgm, dialogue_ms, cls.CROSSFADE_MS)
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
        else:
            bg_track = ambience_track

        # 4. 對齊長度並以對白覆蓋在最頂層
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
