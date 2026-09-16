import json
import os


def _upgrade_voice_map(raw: dict) -> dict:
    """將舊格式 {"角色": "VoiceName"} 自動升級為新格式 {"角色": {"voice": "VoiceName", "audio_profile": ""}}。

    新格式直接原樣通過。混合格式逐條升級。
    """
    upgraded = {}
    for role, value in raw.items():
        if isinstance(value, str):
            upgraded[role] = {"voice": value, "audio_profile": ""}
        elif isinstance(value, dict):
            upgraded[role] = {
                "voice": value.get("voice", ""),
                "audio_profile": value.get("audio_profile", ""),
            }
        else:
            upgraded[role] = {"voice": str(value), "audio_profile": ""}
    return upgraded


class VoiceMapStorage:
    def __init__(self, story_folder: str):
        self.path = os.path.join(story_folder, "voice_map.json")

    def load(self) -> dict:
        """載入 voice_map，自動升級舊格式為新格式。

        回傳格式：{"角色": {"voice": "VoiceName", "audio_profile": "..."}}
        """
        if not os.path.exists(self.path):
            return {}
        with open(self.path, encoding="utf-8") as f:
            try:
                raw = json.load(f)
                return _upgrade_voice_map(raw)
            except json.JSONDecodeError:
                return {}

    def load_voice_names(self) -> dict[str, str]:
        """只回傳 role → voice 字串字典，供需要純聲線名稱的地方使用。"""
        return {role: entry["voice"] for role, entry in self.load().items()}

    def save(self, voice_map: dict) -> None:
        """儲存 voice_map（新格式物件或舊格式字串均可，儲存前自動升級）。"""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(_upgrade_voice_map(voice_map), f, ensure_ascii=False, indent=2)
