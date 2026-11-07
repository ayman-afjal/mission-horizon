import json, os, math
from .mission import Mission

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def _reach_altitude(sim, p):
    return sim.max_alt >= p["altitude_m"] and not sim.crashed

def _stable_orbit(sim, p):
    if sim.crashed or sim.landed_on is not None: return False
    o, body = sim.orbit()
    if body.key != p["body"] or not o.bound: return False
    return o.rp - body.radius >= p["min_periapsis_m"] and o.ra - body.radius <= p.get("max_apoapsis_m", 1e15)

def _soft_landing(sim, p):
    return (sim.landed_on is not None and sim.landed_on.key == p["body"] and not sim.crashed
            and sim.launched)

EVALUATORS = {"reach_altitude": _reach_altitude, "stable_orbit": _stable_orbit, "soft_landing": _soft_landing}

def load_missions(path=None):
    with open(path or os.path.join(DATA, "missions.json")) as f:
        ms = [Mission(d) for d in json.load(f)]
    return sorted(ms, key=lambda m: m.order)
