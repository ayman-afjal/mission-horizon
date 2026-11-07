"""Keplerian elements (2D) and a numerical trajectory predictor."""
import math

class Orbit:
    def __init__(self, rx, ry, vx, vy, mu):
        self.mu = mu
        r = math.hypot(rx, ry); v2 = vx * vx + vy * vy
        self.r = r
        self.h = rx * vy - ry * vx
        rv = rx * vx + ry * vy
        ex = ((v2 - mu / r) * rx - rv * vx) / mu
        ey = ((v2 - mu / r) * ry - rv * vy) / mu
        self.e = math.hypot(ex, ey)
        self.energy = v2 / 2 - mu / r
        self.bound = self.energy < 0
        self.rp = self.h * self.h / (mu * (1 + self.e)) if self.e > -1 else 0.0
        if self.e < 1e-9:
            self.nu = math.atan2(ry, rx)
        else:
            c = ex * ry - ey * rx
            d = ex * rx + ey * ry
            self.nu = math.atan2(c if self.h >= 0 else -c, d)
        if abs(self.energy) > 1e-12:
            self.a = -mu / (2 * self.energy)
        else:
            self.a = math.inf
        self.ra = (2 * self.a - self.rp) if self.energy < 0 else math.inf
        self.period = 2 * math.pi * math.sqrt(self.a ** 3 / mu) if self.bound else math.inf

    def _mean_anomaly(self):
        e, nu = min(self.e, 1 - 1e-12), self.nu
        E = 2 * math.atan2(math.sqrt(1 - e) * math.sin(nu / 2), math.sqrt(1 + e) * math.cos(nu / 2))
        return E - e * math.sin(E)

    def eta_apoapsis(self):
        if not self.bound or self.a <= 0: return math.inf
        n = math.sqrt(self.mu / self.a ** 3)
        M = self._mean_anomaly() % (2 * math.pi)
        return ((math.pi - M) % (2 * math.pi)) / n

    def eta_periapsis(self):
        n_ok = self.bound
        if n_ok:
            n = math.sqrt(self.mu / self.a ** 3)
            M = self._mean_anomaly() % (2 * math.pi)
            return ((2 * math.pi - M) % (2 * math.pi)) / n
        # hyperbolic: only if inbound
        if self.nu < 0 and self.e > 1:
            H = 2 * math.atanh(math.sqrt((self.e - 1) / (self.e + 1)) * math.tan(self.nu / 2))
            M = self.e * math.sinh(H) - H
            n = math.sqrt(self.mu / (-self.a) ** 3)
            return -M / n
        return math.inf

class Prediction:
    def __init__(self):
        self.pts = []          # (t, x, y)
        self.impact = None     # (body_key, t)
        self.moon_ca = None    # (t, distance)

def predict(universe, x, y, vx, vy, t0, max_points=2500, max_days=10.0):
    """Coasting prediction (gravity only) with kick-drift-kick."""
    U = universe
    P = Prediction()
    t = t0
    dom = U.dominant(x, y, t)
    rx, ry, rvx, rvy = U.rel_state(x, y, vx, vy, t, dom)
    o = Orbit(rx, ry, rvx, rvy, dom.mu)
    horizon = max_days * 86400.0
    if o.bound:
        horizon = min(horizon, o.period * 1.02)
    t_end = t0 + horizon
    ax, ay = U.accel(x, y, t)
    P.pts.append((t, x, y))
    best = None
    earth, moon = U.earth, U.moon
    for _ in range(max_points * 4):
        mx, my = moon.pos(t)
        de = math.hypot(x, y); dm = math.hypot(x - mx, y - my)
        if de < earth.radius: P.impact = ("earth", t); break
        if dm < moon.radius: P.impact = ("moon", t); break
        if best is None or dm < best[1]: best = (t, dm)
        dt = 0.02 * min(math.sqrt(de ** 3 / earth.mu), math.sqrt(dm ** 3 / moon.mu))
        dt = max(1.0, min(dt, 4000.0))
        vx += 0.5 * dt * ax; vy += 0.5 * dt * ay
        x += dt * vx; y += dt * vy
        t += dt
        ax, ay = U.accel(x, y, t)
        vx += 0.5 * dt * ax; vy += 0.5 * dt * ay
        P.pts.append((t, x, y))
        if t >= t_end or len(P.pts) >= max_points: break
    P.moon_ca = best
    return P
