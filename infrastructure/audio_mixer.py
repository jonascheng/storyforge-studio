from pydub import AudioSegment

try:
    import static_ffmpeg

    static_ffmpeg.add_paths(weak=True)
except Exception:
    pass


class AudioMixer:
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
