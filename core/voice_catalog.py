from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceActor:
    name: str
    tone: str
    description: str
    family: str
    gender: str


# Gemini TTS 官方支援的 30 位演員庫與特色說明
VOICE_CATALOG: dict[str, VoiceActor] = {
    # ── 童趣活潑家族 (Youthful & Upbeat) ──
    "Puck": VoiceActor("Puck", "Upbeat", "歡快活潑、充滿活力", "youthful_upbeat", "男"),
    "Leda": VoiceActor("Leda", "Youthful", "年輕稚嫩、清脆生動", "youthful_upbeat", "女"),
    "Fenrir": VoiceActor("Fenrir", "Excitable", "激昂興奮、情感強烈", "youthful_upbeat", "男"),
    "Zephyr": VoiceActor("Zephyr", "Bright", "明亮清爽、朝氣蓬勃", "youthful_upbeat", "男"),
    "Autonoe": VoiceActor("Autonoe", "Bright", "明亮靈巧、生動敏捷", "youthful_upbeat", "女"),
    "Laomedeia": VoiceActor("Laomedeia", "Upbeat", "節奏輕快、樂觀開朗", "youthful_upbeat", "女"),
    "Sadachbia": VoiceActor("Sadachbia", "Lively", "活力充沛、熱情躍動", "youthful_upbeat", "女"),
    # ── 溫柔親切家族 (Warm & Gentle) ──
    "Aoede": VoiceActor("Aoede", "Breezy", "微風般輕鬆愜意、自然舒暢", "warm_gentle", "女"),
    "Callirrhoe": VoiceActor(
        "Callirrhoe", "Easy-going", "隨和悠閒、溫柔好親近", "warm_gentle", "女"
    ),
    "Umbriel": VoiceActor("Umbriel", "Easy-going", "平易近人、柔和放鬆", "warm_gentle", "男"),
    "Achernar": VoiceActor("Achernar", "Soft", "柔和細膩、輕聲細語", "warm_gentle", "男"),
    "Achird": VoiceActor("Achird", "Friendly", "親切友善、溫暖陪伴", "warm_gentle", "女"),
    "Vindemiatrix": VoiceActor("Vindemiatrix", "Gentle", "溫柔慈愛、平撫人心", "warm_gentle", "女"),
    "Sulafat": VoiceActor("Sulafat", "Warm", "溫暖醇厚、富有包容感", "warm_gentle", "女"),
    # ── 成熟沉穩家族 (Mature & Steady) ──
    "Kore": VoiceActor("Kore", "Firm", "堅定沉穩、字句分明（經典說書人）", "mature_steady", "中性"),
    "Schedar": VoiceActor("Schedar", "Even", "平穩勻稱、平心靜氣", "mature_steady", "女"),
    "Charon": VoiceActor("Charon", "Informative", "資訊條理、知性冷靜", "mature_steady", "男"),
    "Gacrux": VoiceActor("Gacrux", "Mature", "成熟穩健、長者智慧", "mature_steady", "男"),
    "Iapetus": VoiceActor("Iapetus", "Clear", "清晰乾淨、咬字精準", "mature_steady", "男"),
    "Erinome": VoiceActor("Erinome", "Clear", "清澈透亮、條理明晰", "mature_steady", "女"),
    "Algieba": VoiceActor("Algieba", "Smooth", "圓滑流暢、絲滑沉著", "mature_steady", "男"),
    "Despina": VoiceActor("Despina", "Smooth", "流暢優雅、平和從容", "mature_steady", "女"),
    "Rasalgethi": VoiceActor(
        "Rasalgethi", "Informative", "知性詳實、解說風格", "mature_steady", "男"
    ),
    "Sadaltager": VoiceActor(
        "Sadaltager", "Knowledgeable", "博學多聞、篤定可信", "mature_steady", "男"
    ),
    "Zubenelgenubi": VoiceActor(
        "Zubenelgenubi", "Casual", "自然隨意、真實日常", "mature_steady", "男"
    ),
    # ── 威嚴粗獷家族 (Firm & Gravelly) ──
    "Algenib": VoiceActor(
        "Algenib", "Gravelly", "低沉粗獷、沙啞有力（適合怪獸/威猛角色）", "firm_gravelly", "中性"
    ),
    "Orus": VoiceActor("Orus", "Firm", "威嚴果決、氣場強大", "firm_gravelly", "男"),
    "Alnilam": VoiceActor("Alnilam", "Firm", "堅毅深厚、剛正不阿", "firm_gravelly", "男"),
    "Pulcherrima": VoiceActor(
        "Pulcherrima", "Forward", "直接果敢、具穿透力", "firm_gravelly", "女"
    ),
    "Enceladus": VoiceActor("Enceladus", "Breathy", "氣息濃厚、神秘深邃", "firm_gravelly", "男"),
}

VOICE_FAMILIES: dict[str, list[str]] = {
    "youthful_upbeat": [v.name for v in VOICE_CATALOG.values() if v.family == "youthful_upbeat"],
    "warm_gentle": [v.name for v in VOICE_CATALOG.values() if v.family == "warm_gentle"],
    "mature_steady": [v.name for v in VOICE_CATALOG.values() if v.family == "mature_steady"],
    "firm_gravelly": [v.name for v in VOICE_CATALOG.values() if v.family == "firm_gravelly"],
}


def resolve_voice_map(
    ai_suggestions: dict[str, str] | None,
    roles: list[str],
    narrator_voice: str = "Kore",
    role_line_counts: dict[str, int] | None = None,
) -> dict[str, str]:
    """將 AI 導演建議的角色聲音進行防撞與驗證，確保一角一聲。

    規則：
    1. 「旁白」固定指派為 narrator_voice（預設 Kore），其餘角色避開該聲線。
    2. 若角色挑選的演員在候選庫中且未被佔用，直接採用。
    3. 若發生衝突或不存在，優先從同特質家族中尋找未被佔用的演員替換。
    4. 若同家族已滿，則從剩餘所有可用演員中指派。
    5. 若角色數超過演員庫（> 29），安全共用可用演員。
    """
    suggestions = ai_suggestions or {}
    result: dict[str, str] = {}
    used_voices: set[str] = set()

    # 1. 旁白處理
    has_narrator = "旁白" in roles or "旁白" in suggestions
    if has_narrator:
        result["旁白"] = narrator_voice
        used_voices.add(narrator_voice)

    # 2. 準備一般角色
    non_narrator_roles = [r for r in roles if r != "旁白"]
    # 若有台詞計數，台詞多的角色優先保留其所選聲音
    if role_line_counts:
        non_narrator_roles.sort(key=lambda r: role_line_counts.get(r, 0), reverse=True)

    # 排除旁白後的可用演員庫（29 位）
    available_pool = [name for name in VOICE_CATALOG if name != narrator_voice]

    # 第一輪：先為沒有衝突的有效建議定案
    unassigned_roles: list[str] = []
    for role in non_narrator_roles:
        suggested = suggestions.get(role)
        if (
            suggested
            and suggested in VOICE_CATALOG
            and suggested != narrator_voice
            and suggested not in used_voices
        ):
            result[role] = suggested
            used_voices.add(suggested)
        else:
            unassigned_roles.append(role)

    # 第二輪：為衝突或無建議的角色進行同特質家族遞補
    for role in unassigned_roles:
        suggested = suggestions.get(role)
        assigned: str | None = None

        # 優先嘗試同家族
        if suggested and suggested in VOICE_CATALOG:
            family = VOICE_CATALOG[suggested].family
            for candidate in VOICE_FAMILIES[family]:
                if candidate != narrator_voice and candidate not in used_voices:
                    assigned = candidate
                    break

        # 同家族皆滿或無指定家族，自全局可用庫挑選尚未使用的演員
        if not assigned:
            for candidate in available_pool:
                if candidate not in used_voices:
                    assigned = candidate
                    break

        # 極端狀況：所有 29 位演員都已用罄，安全共用
        if not assigned:
            assigned = available_pool[len(used_voices) % len(available_pool)]

        result[role] = assigned
        used_voices.add(assigned)

    return result
