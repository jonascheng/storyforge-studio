from core.entities import Scene, Screenplay, Script, ScriptLine


def test_script_line_creation():
    line = ScriptLine(role="旁白", emotion="平靜", text="從前從前...")
    assert line.role == "旁白"
    assert line.emotion == "平靜"
    assert line.text == "從前從前..."


def test_script_creation():
    line1 = ScriptLine(role="旁白", emotion="平靜", text="從前從前...")
    line2 = ScriptLine(role="小明", emotion="開心", text="你好！")

    script = Script(lines=[line1, line2])

    assert len(script.lines) == 2
    assert script.lines[1].role == "小明"


def test_script_to_dict():
    line1 = ScriptLine(role="旁白", emotion="平靜", text="從前從前...")
    script = Script(lines=[line1])
    data = script.to_dict()

    assert data["lines"][0]["role"] == "旁白"
    assert data["lines"][0]["emotion"] == "平靜"
    assert data["lines"][0]["text"] == "從前從前..."


def test_script_line_has_voice_direction_note():
    line = ScriptLine(
        role="旁白", emotion="平靜", text="從前從前...", voice_direction_note="[calm, slow]"
    )
    assert line.voice_direction_note == "[calm, slow]"


def test_scene_creation():
    line = ScriptLine(
        role="旁白", emotion="平靜", text="從前從前...", voice_direction_note="[calm]"
    )
    scene = Scene(scene_id=1, title="開場白", lines=[line])
    assert scene.scene_id == 1
    assert scene.title == "開場白"
    assert len(scene.lines) == 1
    assert scene.scene_description == ""  # 預設為空字串


def test_scene_creation_with_description():
    line = ScriptLine(role="旁白", emotion="平靜", text="從前從前...")
    scene = Scene(
        scene_id=1,
        title="開場白",
        lines=[line],
        scene_description="A quiet forest at dawn. Mist drifts between ancient trees.",
    )
    assert scene.scene_description == "A quiet forest at dawn. Mist drifts between ancient trees."


def test_scene_to_dict():
    line = ScriptLine(role="小明", emotion="開心", text="你好！", voice_direction_note="[cheerful]")
    scene = Scene(
        scene_id=2,
        title="相遇",
        lines=[line],
        scene_description="A sunny park in the afternoon.",
    )
    data = scene.to_dict()
    assert data["scene_id"] == 2
    assert data["title"] == "相遇"
    assert data["lines"][0]["voice_direction_note"] == "[cheerful]"
    assert data["scene_description"] == "A sunny park in the afternoon."


def test_screenplay_creation():
    line = ScriptLine(role="旁白", emotion="平靜", text="結束。", voice_direction_note="[calm]")
    scene = Scene(scene_id=1, title="結局", lines=[line])
    screenplay = Screenplay(scenes=[scene])
    assert len(screenplay.scenes) == 1


def test_screenplay_to_dict():
    line = ScriptLine(role="旁白", emotion="平靜", text="結束。", voice_direction_note="[calm]")
    scene = Scene(scene_id=1, title="結局", lines=[line])
    screenplay = Screenplay(scenes=[scene])
    data = screenplay.to_dict()
    assert len(data["scenes"]) == 1
    assert data["scenes"][0]["title"] == "結局"
    assert data["voice_map"] == {}


def test_screenplay_with_voice_map_new_format():
    """voice_map 新格式：每個值為包含 voice + audio_profile 的 dict。"""
    line = ScriptLine(role="主角", emotion="高興", text="嗨！")
    scene = Scene(scene_id=1, title="開始", lines=[line])
    vm = {
        "主角": {"voice": "Puck", "audio_profile": "Young hero, energetic and brave."},
        "旁白": {"voice": "Kore", "audio_profile": "Calm, steady audiobook narrator."},
    }
    screenplay = Screenplay(scenes=[scene], voice_map=vm)
    assert screenplay.voice_map == vm
    assert screenplay.to_dict()["voice_map"] == vm


def test_screenplay_with_voice_map_old_format_compatible():
    """舊格式字串仍可放入 voice_map（Screenplay entity 不強制格式，由 storage 負責升級）。"""
    line = ScriptLine(role="主角", emotion="高興", text="嗨！")
    scene = Scene(scene_id=1, title="開始", lines=[line])
    vm = {"主角": "Puck", "旁白": "Kore"}
    screenplay = Screenplay(scenes=[scene], voice_map=vm)  # type: ignore[arg-type]
    assert screenplay.voice_map["主角"] == "Puck"
