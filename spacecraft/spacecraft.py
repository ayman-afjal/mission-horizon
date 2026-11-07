import math
from physics.constants import G0
from .parts import parts_db
from .engine import thrust_and_flow
from .fuel import FuelPool

class Stage:
    """A group of parts starting at a decoupler (or the top of the craft)."""
    def __init__(self, parts):
        self.parts = parts
        self.fuel = FuelPool(sum(p.fuel for p in parts))
        self.dry = sum(p.mass for p in parts)
        self.engines = [p for p in parts if p.category == "engine"]
    @property
    def mass(self): return self.dry + self.fuel.amount
    @property
    def cost(self): return sum(p.cost for p in self.parts)

class Spacecraft:
    def __init__(self, part_ids):
        db = parts_db()
        self.part_ids = list(part_ids)
        parts = [db.get(i) for i in part_ids]
        groups, cur = [], []
        for p in parts:
            if p.category == "decoupler" and cur:
                groups.append(cur); cur = []
            cur.append(p)
        if cur: groups.append(cur)
        self.stages = [Stage(g) for g in groups]
        self.total_cost = sum(p.cost for p in parts)
        self.parts = parts
        self.mass = sum(s.mass for s in self.stages)

    # ---- queries
    @property
    def active(self): return self.stages[-1]
    @property
    def can_stage(self): return len(self.stages) > 1
    def recompute_mass(self): self.mass = sum(s.mass for s in self.stages)

    def max_diameter(self):
        return max((p.diameter for s in self.stages for p in s.parts), default=1.0)
    def drag_area(self, cd=0.2):
        d = self.max_diameter(); return cd * math.pi * d * d / 4

    def has_role(self, role): return any(p.role == role for p in self.parts)
    def height(self): return sum(p.length for s in self.stages for p in s.parts)

    def thrust(self, throttle, pressure_ratio):
        """(thrust N, mdot kg/s) of the active stage at this throttle."""
        st = self.active
        if throttle <= 0 or st.fuel.amount <= 0: return 0.0, 0.0
        f = m = 0.0
        for e in st.engines:
            a, b = thrust_and_flow(e, throttle, pressure_ratio); f += a; m += b
        return f, m

    def burn(self, kg):
        used = self.active.fuel.draw(kg); self.mass -= used; return used

    def stage(self):
        """Drop the bottom stage; returns it (or None)."""
        if not self.can_stage: return None
        s = self.stages.pop(); self.recompute_mass(); return s

    # ---- design analysis
    def stage_report(self, g_surface=G0):
        """Per-stage figures in firing order (bottom stage first)."""
        out = []
        for i in range(len(self.stages) - 1, -1, -1):
            st = self.stages[i]
            m0 = sum(s.mass for s in self.stages[: i + 1])
            fuel = st.fuel.amount
            F = sum(e.thrust_vac for e in st.engines)
            flow = sum(e.thrust_vac / (G0 * e.isp_vac) for e in st.engines)
            flow_sl = sum(e.thrust_vac / (G0 * e.isp_sl) for e in st.engines)
            isp_vac = F / (flow * G0) if flow else 0.0
            isp_sl = F / (flow_sl * G0) if flow_sl else 0.0
            # sea-level thrust uses sl isp at constant mdot
            F_sl = sum(e.thrust_vac * e.isp_sl / e.isp_vac for e in st.engines)
            mf = m0 - fuel
            ln = math.log(m0 / mf) if mf > 0 and m0 > mf else 0.0
            out.append(dict(index=i, m0=m0, mf=mf, fuel=fuel, has_engine=bool(st.engines),
                            dv_vac=isp_vac * G0 * ln, dv_sl=isp_sl * G0 * ln,
                            twr_sl=F_sl / (m0 * g_surface), twr_vac=F / (m0 * g_surface)))
        return out

    def total_dv_vac(self): return sum(r["dv_vac"] for r in self.stage_report())

    def validate(self, mission=None):
        """Returns (errors, warnings)."""
        errs, warns = [], []
        if not self.parts: return ["Craft is empty."], warns
        if self.parts[0].category != "pod": errs.append("Top part must be a pod (guidance unit / lander probe).")
        if sum(1 for p in self.parts if p.category == "pod") > 1: errs.append("Only one pod allowed.")
        for i, st in enumerate(self.stages):
            if len(st.parts) == 0 or (i > 0 and len(st.parts) == 1 and st.parts[0].category == "decoupler"):
                errs.append(f"Stage {i + 1} is empty (decoupler with nothing below).")
        if not self.active.engines: errs.append("Bottom stage has no engine.")
        rep = self.stage_report()
        if rep and rep[0]["has_engine"] and rep[0]["twr_sl"] < 1.0: errs.append(f"Liftoff TWR {rep[0]['twr_sl']:.2f} < 1.0 - it will never leave the pad.")
        for i, st in enumerate(self.stages[:-1]):
            if not st.engines and st.fuel.capacity > 0: warns.append(f"Stage {i + 1} has fuel but no engine.")
        if mission:
            if self.total_cost > mission.budget: errs.append(f"Over budget: ${self.total_cost:.1f}M > ${mission.budget:.1f}M")
            if len(self.parts) > mission.max_parts: errs.append(f"Too many parts: {len(self.parts)} > {mission.max_parts}")
            if self.mass > mission.max_mass: errs.append(f"Too heavy: {self.mass/1000:.1f} t > {mission.max_mass/1000:.0f} t")
            for r in mission.required_roles:
                if not self.has_role(r): errs.append(f"Mission requires a '{r}' part.")
        return errs, warns
