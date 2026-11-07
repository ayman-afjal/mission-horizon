import sys; sys.path.insert(0,'.'); sys.path.insert(0,'tests')
from bot import fly
D=['guidance_unit','sat_small','decoupler_s','tank_m','engine_swift','decoupler_m','tank_m','tank_m','engine_swift','decoupler_m','tank_m','engine_kestrel']
def script(kick_alt=1000, pitch0=84, turn_alt=4000, ap=185):
    return f"""throttle 1
wait until altitude > {kick_alt}
pitch {pitch0}
wait until altitude > {turn_alt}
sas prograde
wait until stage_fuel < 0.01
stage
wait until apoapsis > {ap}km
throttle 0
wait until eta_apoapsis < 45
stage
throttle 1
wait until periapsis > 170km
throttle 0
"""
if __name__=="__main__":
    for ka,p0,ta in [(1000,84,4000),(800,80,3000),(1000,75,3000),(500,70,2000)]:
        sim=fly(D,script(ka,p0,ta),None,max_t=9000,warp_cap=10)
        t=sim.telemetry()
        print(ka,p0,ta,"| t",round(sim.t),"crash",sim.crashed,"alt",round(t.altitude/1e3),"ap",round(t.apoapsis/1e3),"pe",round(t.periapsis/1e3),"stages",t.stages,"fuel",round(t.stage_fuel,2))
