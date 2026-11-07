"""Global game state: progression, saved designs and scripts."""
import json, os
from physics.gravit import Universe
from spacecraft.parts import parts_db
from missions.mission_data import load_missions

SAVE_PATH = os.environ.get("MISSION_HORIZON_SAVE", os.path.join(os.path.dirname(os.path.dirname(__file__)), "save.json"))

class GameState:
    def __init__(self):
        self.universe = Universe()
        self.db = parts_db()
        self.missions = load_missions()
        self.completed = {}      # mission id -> best stars
        self.designs = {}        # mission id -> [part ids top->bottom]
        self.scripts = {}        # mission id -> script text
        self.selected = self.missions[0].id
        self.load()

    # --- lookups
    def mission(self, mid=None):
        mid = mid or self.selected
        return next(m for m in self.missions if m.id == mid)
    def mission_available(self, m):
        return m.available and (m.requires is None or m.requires in self.completed)
    def part_unlocked(self, p): return p.unlock is None or p.unlock in self.completed
    def design(self, mid=None):
        m = self.mission(mid)
        return self.designs.setdefault(m.id, list(m.template))
    def script(self, mid=None):
        m = self.mission(mid)
        return self.scripts.setdefault(m.id, m.script_template)

    def complete(self, mid, stars):
        self.completed[mid] = max(stars, self.completed.get(mid, 0)); self.save()

    # --- persistence
    def save(self):
        try:
            with open(SAVE_PATH, "w") as f:
                json.dump(dict(completed=self.completed, designs=self.designs, scripts=self.scripts, selected=self.selected), f, indent=1)
        except OSError: pass
    def load(self):
        try:
            with open(SAVE_PATH) as f: d = json.load(f)
        except (OSError, ValueError): return
        self.completed = d.get("completed", {}); self.designs = d.get("designs", {})
        self.scripts = d.get("scripts", {})
        sel = d.get("selected")
        if sel and any(m.id == sel for m in self.missions): self.selected = sel
    def reset(self):
        self.completed = {}; self.designs = {}; self.scripts = {}; self.selected = self.missions[0].id; self.save()

game = GameState()
