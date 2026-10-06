import os
from dataclasses import dataclass

from pydub import AudioSegment

try:
    import static_ffmpeg

    static_ffmpeg.add_paths(weak=True)
except Exception:
    pass

RESOURCES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "ambience")


@dataclass(frozen=True)
class AmbienceTheme:
    theme_id: str
    name: str
    description: str
    keywords: list[str]


_THEMES: dict[str, AmbienceTheme] = {
    "rain": AmbienceTheme(
        theme_id="rain",
        name="雨聲",
        description="細密雨絲與雨滴打在窗戶地面的聲音，適合憂傷、沉思或室內避雨場景",
        keywords=["雨", "下雨", "暴雨", "雨滴", "雷雨", "陰雨"],
    ),
    "wind": AmbienceTheme(
        theme_id="wind",
        name="陣風",
        description="呼嘯而過的風聲與氣流湧動，適合高山、曠野、寒冬或緊張對峙場景",
        keywords=["風", "大風", "狂風", "寒風", "曠野", "懸崖"],
    ),
    "forest": AmbienceTheme(
        theme_id="forest",
        name="森林鳥鳴",
        description="微風拂過樹梢伴隨隨機清脆鳥鳴，適合白天大自然、冒險啟程或鄉間漫步",
        keywords=["森林", "樹林", "小鳥", "鳥鳴", "樹木", "大自然", "公園"],
    ),
    "night": AmbienceTheme(
        theme_id="night",
        name="夏夜蟲鳴",
        description="靜謐夜色與規律蟋蟀鳴叫，適合夜晚深談、庭院賞月或夜間潛伏",
        keywords=["夜晚", "深夜", "夜色", "蟲鳴", "蟋蟀", "月亮", "星空"],
    ),
    "fireplace": AmbienceTheme(
        theme_id="fireplace",
        name="壁爐柴火",
        description="溫暖燃燒的低鳴與木柴劈啪聲，適合客廳聚會、寒夜取暖或溫馨對話",
        keywords=["壁爐", "柴火", "木柴", "火堆", "劈啪", "營火", "燃燒"],
    ),
    "sea": AmbienceTheme(
        theme_id="sea",
        name="海浪波濤",
        description="深沉平緩的潮汐拍打岸邊聲，適合海灘漫步、碼頭離別或海上航行",
        keywords=["海", "海浪", "潮汐", "沙灘", "海邊", "海洋", "海島"],
    ),
    "room": AmbienceTheme(
        theme_id="room",
        name="安靜室內",
        description="極微弱的室內空氣流動感，適合平靜的日常生活、書房閱讀或私人密談",
        keywords=["室內", "房間", "臥室", "書房", "安靜", "日常", "辦公室"],
    ),
    "cafe": AmbienceTheme(
        theme_id="cafe",
        name="咖啡廳氛圍",
        description="柔和的背景人群微噪與清脆瓷杯輕響，適合城市聚會、街角相遇或輕鬆休閒",
        keywords=["咖啡廳", "餐廳", "茶館", "人群", "店裡", "聚會", "聊天"],
    ),
}


class AmbienceCatalog:
    """環境音百寶箱：管理內建免版權環境音效資源與長度延伸。"""

    @classmethod
    def list_themes(cls) -> list[AmbienceTheme]:
        return list(_THEMES.values())

    @classmethod
    def get_theme(cls, theme_id: str) -> AmbienceTheme | None:
        return _THEMES.get(theme_id)

    @classmethod
    def has_theme(cls, theme_id: str) -> bool:
        return theme_id in _THEMES

    @classmethod
    def get_ambience_path(cls, theme_id: str) -> str | None:
        if theme_id not in _THEMES:
            return None
        path = os.path.join(RESOURCES_DIR, f"{theme_id}.mp3")
        return path if os.path.exists(path) else None

    @classmethod
    def get_looped_ambience(
        cls, theme_id: str, target_ms: int, crossfade_ms: int = 1000
    ) -> AudioSegment:
        """取得指定主題的環境音，並透過平滑 crossfade 循環延長至目標毫秒長度。"""
        if not cls.has_theme(theme_id):
            raise ValueError(f"找不到環境音主題: {theme_id}")

        if target_ms <= 0:
            return AudioSegment.empty()

        audio_path = cls.get_ambience_path(theme_id)
        if not audio_path or not os.path.exists(audio_path):
            # 若檔案遺失，自動即時烘烤
            from infrastructure.resources.bake_ambience import GENERATORS

            if theme_id in GENERATORS:
                seg = GENERATORS[theme_id]()
                seg = seg.fade_in(500).fade_out(500)
                os.makedirs(RESOURCES_DIR, exist_ok=True)
                audio_path = os.path.join(RESOURCES_DIR, f"{theme_id}.mp3")
                seg.export(audio_path, format="mp3", bitrate="64k")
            else:
                raise FileNotFoundError(f"無法載入環境音檔: {theme_id}")

        base_audio = AudioSegment.from_file(audio_path)

        if len(base_audio) >= target_ms:
            return base_audio[:target_ms]

        result = base_audio
        cf = min(crossfade_ms, len(base_audio) - 1)
        while len(result) < target_ms:
            result = result.append(base_audio, crossfade=cf)

        return result[:target_ms]
