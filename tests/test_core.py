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
    assert scene.audio_path is None


def test_scene_to_dict():
    line = ScriptLine(role="小明", emotion="開心", text="你好！", voice_direction_note="[cheerful]")
    scene = Scene(scene_id=2, title="相遇", lines=[line])
    data = scene.to_dict()
    assert data["scene_id"] == 2
    assert data["title"] == "相遇"
    assert data["lines"][0]["voice_direction_note"] == "[cheerful]"
    assert data["audio_path"] is None


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
