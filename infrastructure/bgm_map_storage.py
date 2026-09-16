import json
import os

from core.entities import BgmMap, BgmTheme


class BgmMapStorage:
    def __init__(self, story_folder: str):
        self.path = os.path.join(story_folder, "bgm_map.json")

    def load(self) -> BgmMap | None:
        if not os.path.exists(self.path):
            return None
        with open(self.path, encoding="utf-8") as f:
            try:
                data = json.load(f)
                themes = {}
                for k, v in data.get("themes", {}).items():
                    themes[k] = BgmTheme(name=v.get("name", ""), prompt=v.get("prompt", ""))
                return BgmMap(themes=themes)
            except json.JSONDecodeError:
                return None

    def save(self, bgm_map: BgmMap) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(bgm_map.to_dict(), f, ensure_ascii=False, indent=2)
