import sys, math, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from physics.gravit import Universe
from physics.orbit import Orbit, predict

U = Universe()
R = U.earth.radius + 400e3
v = math.sqrt(U.earth.mu / R)
o = Orbit(0, R, v, 0, U.earth.mu)
assert o.e < 1e-9 and abs(o.rp - R) < 1 and abs(o.ra - R) < 1, (o.e, o.rp, o.ra)
print("LEO period min", o.period / 60)
P = predict(U, 0, R, v, 0, 0)
rs = [math.hypot(x, y) for _, x, y in P.pts]
print("circular drift m:", max(rs) - min(rs), "points", len(P.pts))
assert max(rs) - min(rs) < 2000
# elliptical: eta apoapsis consistency
o = Orbit(0, R, v * 1.1, 0, U.earth.mu)
print("e", o.e, "ra km", (o.ra - 6371000) / 1e3, "eta_ap min", o.eta_apoapsis() / 60, "T/2", o.period / 120)
assert abs(o.eta_apoapsis() - o.period / 2) < 1
# escape is unbound
o = Orbit(0, R, v * 1.5, 0, U.earth.mu)
assert not o.bound
print("physics OK")
