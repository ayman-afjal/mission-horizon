"""Flies every mission's template craft with its template script, headless.
Run:  python tests/test_missions.py        (about 30 s)"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot import fly
from missions.mission_data import load_missions
from spacecraft.spacecraft import Spacecraft

ok = True
for m in load_missions():
    if not m.available: continue
    errs, _ = Spacecraft(m.template).validate(m)
    t0 = time.time()
    sim = fly(m.template, m.script_template, m)
    status = "PASS" if (m.complete and not errs) else "FAIL"
    ok &= status == "PASS"
    print(f"{status} {m.id} {m.name:14s} design errors={errs} sim_t={sim.t:,.0f}s wall={time.time()-t0:.1f}s")
sys.exit(0 if ok else 1)
