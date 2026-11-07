import sys, copy, math; sys.path.insert(0,'.'); sys.path.insert(0,'tests')
from physics.gravit import Universe
from physics.sim import FlightSim
from spacecraft.spacecraft import Spacecraft
from scripting.parser import parse
from scripting.executor import Executor
import m3try
A="""throttle 1
wait until altitude > 600
pitch 80
wait until altitude > 2500
pitch 62
wait until altitude > 9km
pitch 45
wait until altitude > 25km
pitch 30
wait until stage_fuel < 0.01
stage
pitch 5
wait until stage_fuel < 0.01
throttle 0
stage
sas prograde
warp 50
wait until eta_apoapsis < 70
warp 1
throttle 1
wait until periapsis > 440km
throttle 0
print Parking orbit reached
"""
def run(sim, src, T, cap=100):
    sim.script=Executor(parse(src)[0])
    while sim.t<T and not sim.crashed and not sim.script.finished:
        w=min(cap,sim.max_safe_warp())
        if sim.requested_warp: w=min(w,sim.requested_warp)
        sim.advance(w/60,max_steps=3000)
    return sim
if __name__=="__main__":
    U=Universe(); ship=Spacecraft(m3try.D); sim=FlightSim(U,ship,None)
    run(sim,A,5000)
    T=sim.telemetry(); print("parking: t",round(sim.t),"ap",round(T.apoapsis/1e3),"pe",round(T.periapsis/1e3),"crash",sim.crashed,"stages",T.stages,"fuel",round(T.stage_fuel,2),"moon_angle",round(T.moon_angle))
    import pickle; pickle.dump(sim,open('/tmp/m3park.pkl','wb'))
    B="""warp 50
wait until moon_angle > 330
wait until moon_angle < {L}
warp 1
sas prograde
throttle 1
wait until apoapsis > 380000km
throttle 0
"""
    for L in (95,105,115,125,135):
        s=copy.deepcopy(sim); run(s,B.format(L=L),s.t+9000)
        pr=s.predict(max_points=3000,max_days=8)
        ca=pr.moon_ca
        print("L",L,"crash",s.crashed,"ap km",round(s.telemetry().apoapsis/1e3),"fuel",round(s.telemetry().stage_fuel,2),"moon closest alt km",round((ca[1]-U.moon.radius)/1e3) if ca else None,"at day",round((ca[0]-s.t)/86400,2) if ca else None)
