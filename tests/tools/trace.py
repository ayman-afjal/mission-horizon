import sys,math; sys.path.insert(0,'.'); sys.path.insert(0,'tests')
from physics.gravit import Universe
from physics.sim import FlightSim
from spacecraft.spacecraft import Spacecraft
from scripting.parser import parse
from scripting.executor import Executor
def trace(D, src, T=900, every=20, warp=1):
    U=Universe(); ship=Spacecraft(D); sim=FlightSim(U,ship,None)
    sim.script=Executor(parse(src)[0]); nxt=0; seen=0
    while sim.t<T and not sim.crashed:
        sim.advance(warp/60, max_steps=3000)
        while seen<len(sim.log): print("   LOG",round(sim.log[seen][0]),sim.log[seen][1]); seen+=1
        if sim.t>=nxt:
            Tm=sim.telemetry(); print(round(sim.t),"alt",round(Tm.altitude/1e3,1),"vs",round(Tm.vertical_speed),"hs",round(Tm.horizontal_speed),"att",round(math.degrees(sim.att)),sim.sas,"thr",round(sim.thrust_now/1e3),"st",Tm.stages,"fuel",round(Tm.stage_fuel,2),"ap",(round(Tm.apoapsis/1e3) if Tm.apoapsis<1e12 else "inf"),"pe",round(Tm.periapsis/1e3)); nxt+=every
    return sim
