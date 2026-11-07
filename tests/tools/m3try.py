import sys; sys.path.insert(0,'.'); sys.path.insert(0,'tests')
from trace import trace
D=['guidance_unit','sat_small','decoupler_s','tank_m','tank_m','engine_swift','decoupler_m','tank_l','engine_heron','decoupler_l','tank_xxl','engine_titan','engine_titan']
ASC="""throttle 1
wait until altitude > 800
pitch 80
wait until altitude > 4km
sas prograde
wait until stage_fuel < 0.01
stage
wait until apoapsis > 200km
throttle 0
warp 10
wait until eta_apoapsis < 60
warp 1
throttle 1
wait until periapsis > 185km
throttle 0
"""
if __name__=="__main__":
    trace(D,ASC,T=1200,every=40,warp=1)
