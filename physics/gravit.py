"""Bodies (Earth, Moon on rails) and gravity."""
import json, math, os

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

class Body:
    def __init__(self, key, d):
        self.key = key; self.name = d["name"]; self.mu = d["mu"]; self.radius = d["radius"]
        self.color = tuple(d["color"]); self.soi = d.get("soi")
        atm = d.get("atmosphere")
        self.rho0 = atm["rho0"] if atm else 0.0
        self.scale_h = atm["scale_height"] if atm else 1.0
        self.atm_height = atm["height"] if atm else 0.0
        o = d.get("orbit")
        if o:
            self.orbit_r = o["radius"]; self.w = 2 * math.pi / o["period_s"] * o["direction"]
            self.phase = math.radians(o["phase_deg"])
        else:
            self.orbit_r = 0.0; self.w = 0.0; self.phase = 0.0

    def pos(self, t):
        if not self.orbit_r: return (0.0, 0.0)
        a = self.phase + self.w * t
        return (self.orbit_r * math.cos(a), self.orbit_r * math.sin(a))

    def vel(self, t):
        if not self.orbit_r: return (0.0, 0.0)
        a = self.phase + self.w * t
        s = self.orbit_r * self.w
        return (-s * math.sin(a), s * math.cos(a))

    def density(self, alt):
        if alt >= self.atm_height or self.rho0 == 0: return 0.0
        return self.rho0 * math.exp(-max(alt, 0.0) / self.scale_h)

class Universe:
    def __init__(self, path=None):
        with open(path or os.path.join(DATA, "planets.json")) as f:
            raw = json.load(f)
        self.bodies = {k: Body(k, v) for k, v in raw.items()}
        self.earth = self.bodies["earth"]; self.moon = self.bodies["moon"]

    def accel(self, x, y, t):
        e = self.earth
        r2 = x * x + y * y; r = math.sqrt(r2)
        k = -e.mu / (r2 * r)
        ax = k * x; ay = k * y
        mx, my = self.moon.pos(t)
        dx = x - mx; dy = y - my
        d2 = dx * dx + dy * dy; d = math.sqrt(d2)
        km = -self.moon.mu / (d2 * d)
        # moon also pulls Earth's frame: omitted (Earth fixed at origin)
        return ax + km * dx, ay + km * dy

    def dominant(self, x, y, t):
        mx, my = self.moon.pos(t)
        if math.hypot(x - mx, y - my) < self.moon.soi: return self.moon
        return self.earth

    def rel_state(self, x, y, vx, vy, t, body):
        bx, by = body.pos(t); bvx, bvy = body.vel(t)
        return x - bx, y - by, vx - bvx, vy - bvy
