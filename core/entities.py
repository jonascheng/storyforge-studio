from dataclasses import dataclass, asdict
from typing import List

@dataclass
class ScriptLine:
    role: str
    emotion: str
    text: str
    
@dataclass
class Script:
    lines: List[ScriptLine]
    
    def to_dict(self):
        return {"lines": [asdict(line) for line in self.lines]}
