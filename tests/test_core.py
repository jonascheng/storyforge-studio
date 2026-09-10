import pytest
from core.entities import ScriptLine, Script

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
