import math

class Objective:
    def __init__(self, d):
        self.type = d["type"]; self.params = d; self.label = d["label"]
        self.hold = d.get("hold_s", 0.0)
        self.timer = 0.0; self.done = False

class Mission:
    def __init__(self, d):
        self.id = d["id"]; self.name = d["name"]; self.brief = d["brief"]
        self.order = d.get("order", 0)
        self.available = d.get("available", True)
        self.budget = d["budget"]; self.max_parts = d["max_parts"]; self.max_mass = d["max_mass"]
        self.required_roles = d.get("required_roles", [])
        self.objectives = [Objective(o) for o in d["objectives"]]
        self.unlocks = d.get("unlocks", [])
        self.requires = d.get("requires")
        self.template = d.get("template", [])
        self.script_template = "\n".join(d.get("script_template", []))
        self.hint = d.get("hint", "")
        self.complete = False

    def reset(self):
        self.complete = False
        for o in self.objectives: o.done = False; o.timer = 0.0

    def update(self, sim, dt):
        from .mission_data import EVALUATORS
        if self.complete: return
        for o in self.objectives:
            if o.done: continue
            if EVALUATORS[o.type](sim, o.params):
                o.timer += dt
                if o.timer >= o.hold:
                    o.done = True; sim.note(f"Objective complete: {o.label}")
            else:
                o.timer = 0.0
        if all(o.done for o in self.objectives):
            self.complete = True; sim.note("MISSION SUCCESS")

    def stars(self, cost):
        if not self.complete: return 0
        s = 1
        if cost <= 0.7 * self.budget: s += 1
        if cost <= 0.5 * self.budget: s += 1
        return s
