import json, os
from dataclasses import dataclass, field
from typing import Optional

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

@dataclass
class Part:
    id: str; name: str; category: str
    mass: float; cost: float; length: float; diameter: float
    role: Optional[str] = None
    fuel: float = 0.0
    thrust_vac: float = 0.0; isp_vac: float = 0.0; isp_sl: float = 0.0
    unlock: Optional[str] = None
    description: str = ""

class PartDB:
    def __init__(self, path=None):
        with open(path or os.path.join(DATA, "parts.json")) as f:
            self.parts = {d["id"]: Part(**d) for d in json.load(f)}
    def get(self, pid): return self.parts[pid]
    def by_category(self, cat): return [p for p in self.parts.values() if p.category == cat]

_db = None
def parts_db():
    global _db
    if _db is None: _db = PartDB()
    return _db
