from core.voice_catalog import (
    VOICE_CATALOG,
    VOICE_FAMILIES,
    resolve_voice_map,
)


def test_voice_catalog_contains_30_official_voices():
    # 確保包含 Gemini 官方支援的 30 位演員
    assert len(VOICE_CATALOG) == 30
    expected_voices = {
        "Zephyr",
        "Puck",
        "Charon",
        "Kore",
        "Fenrir",
        "Leda",
        "Orus",
        "Aoede",
        "Callirrhoe",
        "Autonoe",
        "Enceladus",
        "Iapetus",
        "Umbriel",
        "Algieba",
        "Despina",
        "Erinome",
        "Algenib",
        "Rasalgethi",
        "Laomedeia",
        "Achernar",
        "Alnilam",
        "Schedar",
        "Gacrux",
        "Pulcherrima",
        "Achird",
        "Zubenelgenubi",
        "Vindemiatrix",
        "Sadachbia",
        "Sadaltager",
        "Sulafat",
    }
    assert set(VOICE_CATALOG.keys()) == expected_voices


def test_voice_families_cover_all_voices():
    # 確保每個演員都歸屬於四大特質家族之一
    all_family_voices = []
    for family, voices in VOICE_FAMILIES.items():
        all_family_voices.extend(voices)
    assert set(all_family_voices) == set(VOICE_CATALOG.keys())
    assert len(all_family_voices) == 30


def test_resolve_voice_map_narrator_is_kore_and_exclusive():
    # 旁白固定為 Kore，且其他角色絕不重複使用 Kore
    roles = ["旁白", "爸爸", "小松鼠"]
    ai_suggestions = {"旁白": "Kore", "爸爸": "Kore", "小松鼠": "Puck"}

    result = resolve_voice_map(ai_suggestions, roles)

    assert result["旁白"] == "Kore"
    assert result["小松鼠"] == "Puck"
    assert result["爸爸"] != "Kore"  # 爸爸避開旁白
    assert len(set(result.values())) == 3  # 三個角色聲音完全不同


def test_resolve_voice_map_resolves_duplicates_with_same_family_fallback():
    # 當多個角色撞聲時，優先使用同家族中未使用的演員替換
    roles = ["旁白", "小男孩", "小精靈"]
    # 假設 AI 挑選小男孩和小精靈都是活潑的 Puck
    ai_suggestions = {"小男孩": "Puck", "小精靈": "Puck"}

    result = resolve_voice_map(ai_suggestions, roles)

    assert result["旁白"] == "Kore"
    # 其中一位維持 Puck，另一位遞補為同為活潑家族的演員（如 Leda, Fenrir 等）
    assigned = [result["小男孩"], result["小精靈"]]
    assert len(set(assigned)) == 2
    assert "Puck" in assigned
    # 另一位應當也是活潑童趣家族成員
    other = assigned[0] if assigned[1] == "Puck" else assigned[1]
    assert other in VOICE_FAMILIES["youthful_upbeat"]


def test_resolve_voice_map_handles_empty_or_invalid_suggestions():
    # 當 AI 沒給建議或給了不存在的演員名時，程式自動補齊且不撞聲
    roles = ["旁白", "角色A", "角色B", "角色C"]
    ai_suggestions = {"角色A": "NonExistentVoice"}

    result = resolve_voice_map(ai_suggestions, roles)

    assert result["旁白"] == "Kore"
    assert len(result) == 4
    # 所有被分配的角色聲音都在演員庫內
    for r, v in result.items():
        assert v in VOICE_CATALOG
    # 完全不重複
    assert len(set(result.values())) == 4


def test_resolve_voice_map_handles_extreme_roles_over_30():
    # 若角色超過 30 個，不拋出異常，安全共用
    roles = [f"路人_{i}" for i in range(35)]
    roles.append("旁白")

    result = resolve_voice_map({}, roles)

    assert len(result) == 36
    assert result["旁白"] == "Kore"
    # 所有值都是有效演員
    for v in result.values():
        assert v in VOICE_CATALOG
