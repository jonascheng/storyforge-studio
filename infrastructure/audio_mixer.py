from typing import List
from pydub import AudioSegment

try:
    import static_ffmpeg
    static_ffmpeg.add_paths(weak=True)
except Exception:
    pass



class AudioMixer:

    @staticmethod
    def mix(scene_audio_paths: List[str], output_path: str) -> str:
        if not scene_audio_paths:
            raise ValueError("至少需要一個場景才能拼接。")

        combined = AudioSegment.empty()
        for path in scene_audio_paths:
            segment = AudioSegment.from_mp3(path)
            combined += segment

        combined.export(output_path, format="mp3")
        return output_path
