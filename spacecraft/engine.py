from physics.constants import G0

def isp_at(part, pressure_ratio):
    """pressure_ratio: 1 at sea level, 0 in vacuum."""
    return part.isp_vac + (part.isp_sl - part.isp_vac) * min(1.0, max(0.0, pressure_ratio))

def thrust_and_flow(part, throttle, pressure_ratio):
    """Return (thrust N, mass flow kg/s). Mass flow is fixed by vacuum rating."""
    mdot_full = part.thrust_vac / (G0 * part.isp_vac)
    isp = isp_at(part, pressure_ratio)
    return throttle * mdot_full * G0 * isp, throttle * mdot_full
