import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.gravit import Universe
from physics.sim import FlightSim
from spacecraft.spacecraft import Spacecraft
from scripting.parser import parse
from scripting.executor import Executor

def fly(part_ids, script, mission=None, max_t=900000, warp_cap=100000, verbose=False, stop_on_complete=True):
    U = Universe(); ship = Spacecraft(part_ids)
    if mission: mission.reset()
    sim = FlightSim(U, ship, mission)
    prog, errs = parse(script); assert not errs, errs
    sim.script = Executor(prog)
    seen = 0; frames = 0
    while sim.t < max_t and not sim.crashed:
        w = min(warp_cap, sim.max_safe_warp())
        if sim.requested_warp: w = min(w, sim.requested_warp)
        sim.advance(w / 60.0, max_steps=3000); frames += 1
        if verbose:
            while seen < len(sim.log): print(f"  T+{sim.log[seen][0]:8.1f} {sim.log[seen][1]}"); seen += 1
        if mission and mission.complete and stop_on_complete: break
        if sim.script.finished and sim.throttle == 0 and sim.t > 5 and not mission: break
    return sim

if __name__ == "__main__":
    from missions.mission_data import load_missions
    ms = {m.id: m for m in load_missions()}
    m = ms[sys.argv[1]]
    sim = fly(m.template, m.script_template, m, verbose=True)
    t = sim.telemetry()
    print("complete", m.complete, "t", round(sim.t), "crashed", sim.crashed, sim.crash_msg, "cost", Spacecraft(m.template).total_cost)
    print("alt km", t.altitude / 1e3, "ap km", t.apoapsis / 1e3, "pe km", t.periapsis / 1e3, "body", t.body)
