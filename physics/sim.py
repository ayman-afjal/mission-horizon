"""Headless flight simulation (no pygame). The Flight scene is only a view on this."""
import math
from .gravit import Universe
from .orbit import Orbit, predict
from .constants import G0

SAFE_LANDING_SPEED = 5.0      # m/s
TURN_RATE = math.radians(40)  # rad/s

class Telemetry:
    pass

class FlightSim:
    def __init__(self, universe, ship, mission=None):
        self.u = universe; self.ship = ship; self.mission = mission
        self.t = 0.0
        e = universe.earth
        self.x, self.y, self.vx, self.vy = 0.0, e.radius, 0.0, 0.0
        self.landed_on = e; self.land_rel = (0.0, e.radius)
        self.launched = False
        self.att = math.pi / 2
        self.sas = "hold"; self.hold_angle = math.pi / 2; self.pitch_deg = 90.0
        self.throttle = 0.0
        self.crashed = False; self.crash_msg = ""
        self.max_alt = 0.0
        self.log = []          # (t, text)
        self.debris = []       # dicts: x,y,vx,vy,stage,age
        self.requested_warp = None
        self.script = None
        self.q = 0.0           # dynamic pressure
        self.thrust_now = 0.0
        self.flameout_noted = False

    # ------------------------------------------------ helpers
    def note(self, text): self.log.append((self.t, text))

    def dom(self): return self.u.dominant(self.x, self.y, self.t)

    def rel(self, body=None):
        body = body or self.dom()
        return self.u.rel_state(self.x, self.y, self.vx, self.vy, self.t, body)

    def altitude(self, body=None):
        body = body or self.dom()
        rx, ry, _, _ = self.rel(body); return math.hypot(rx, ry) - body.radius

    def orbit(self):
        body = self.dom(); rx, ry, vx, vy = self.rel(body)
        return Orbit(rx, ry, vx, vy, body.mu), body

    def telemetry(self):
        T = Telemetry(); body = self.dom()
        rx, ry, vx, vy = self.rel(body)
        r = math.hypot(rx, ry); ux, uy = rx / r, ry / r
        T.body = body.key
        T.altitude = r - body.radius
        T.speed = math.hypot(vx, vy)
        T.vertical_speed = vx * ux + vy * uy
        T.horizontal_speed = vx * uy - vy * ux      # clockwise (east) positive
        o = Orbit(rx, ry, vx, vy, body.mu)
        T.orbit = o
        T.apoapsis = o.ra - body.radius if o.ra != math.inf else math.inf
        T.periapsis = o.rp - body.radius
        T.eta_apoapsis = o.eta_apoapsis(); T.eta_periapsis = o.eta_periapsis()
        T.mission_time = self.t
        T.throttle = self.throttle
        T.stage_fuel = self.ship.active.fuel.fraction
        T.mass = self.ship.mass
        T.stages = len(self.ship.stages) - 1
        g = body.mu / r ** 2
        F, _ = self.ship.thrust(1.0, 0.0)
        T.twr = F / (self.ship.mass * g)
        T.thrust = self.thrust_now
        T.q = self.q
        T.landed = 1.0 if self.landed_on is not None else 0.0
        T.eccentricity = o.e
        # Moon geometry (Earth frame): angle AHEAD of the ship along its (clockwise) orbit, 0..360
        mx, my = self.u.moon.pos(self.t)
        T.moon_angle = (math.degrees(math.atan2(self.y, self.x) - math.atan2(my, mx))) % 360.0
        T.moon_distance = math.hypot(self.x - mx, self.y - my)
        T.in_moon_soi = 1.0 if body.key == "moon" else 0.0
        T.gravity = g
        return T

    # ------------------------------------------------ controls
    def set_throttle(self, v): self.throttle = min(1.0, max(0.0, v))
    def set_sas(self, mode, value=None):
        self.sas = mode
        if mode == "hold": self.hold_angle = self.att if value is None else value
        if mode == "pitch" and value is not None: self.pitch_deg = value
    def manual_rotate(self, direction, dt):
        self.sas = "hold"; self.hold_angle = self.att + direction * TURN_RATE * dt; self.att = self.hold_angle

    def stage(self):
        st = self.ship.stage()
        if st is None: return False
        self.debris.append(dict(x=self.x, y=self.y, vx=self.vx, vy=self.vy, stage=st, age=0.0, att=self.att))
        self.note(f"Staging! {len(self.ship.stages)} stage(s) left")
        self.flameout_noted = False
        return True

    # ------------------------------------------------ attitude
    def _desired_angle(self):
        if self.sas == "hold": return self.hold_angle
        body = self.dom(); rx, ry, vx, vy = self.rel(body)
        r = math.hypot(rx, ry); ux, uy = rx / r, ry / r
        if self.sas == "pitch":
            p = math.radians(self.pitch_deg); ex, ey = uy, -ux
            return math.atan2(math.cos(p) * ey + math.sin(p) * uy, math.cos(p) * ex + math.sin(p) * ux)
        if self.sas in ("prograde", "retrograde"):
            if math.hypot(vx, vy) < 0.5: return self.att
            a = math.atan2(vy, vx)
            return a if self.sas == "prograde" else a + math.pi
        if self.sas == "radial_out": return math.atan2(uy, ux)
        if self.sas == "radial_in": return math.atan2(-uy, -ux)
        return self.att

    def _update_attitude(self, dt):
        if self.landed_on is not None and not self.launched and self.sas == "hold":
            return
        want = self._desired_angle()
        d = (want - self.att + math.pi) % (2 * math.pi) - math.pi
        m = TURN_RATE * dt
        self.att += max(-m, min(m, d))
        self.att = (self.att + math.pi) % (2 * math.pi) - math.pi

    # ------------------------------------------------ step
    def _atmos(self, x, y):
        e = self.u.earth
        alt = math.hypot(x, y) - e.radius
        rho = e.density(alt)
        return rho

    def step(self, dt):
        if self.crashed: self.t += dt; return
        ship = self.ship; U = self.u
        self._update_attitude(dt)
        if self.script is not None: self.script.tick(self)
        ca, sa = math.cos(self.att), math.sin(self.att)

        rho = self._atmos(self.x, self.y)
        pr = rho / U.earth.rho0 if U.earth.rho0 else 0.0
        F, mdot = ship.thrust(self.throttle, pr)
        burn = mdot * dt; fuel = ship.active.fuel.amount
        if burn > fuel > 0 or (burn > 0 and fuel <= 0):
            frac = fuel / burn if burn > 0 else 0.0
            F *= frac; burn = fuel
        if self.throttle > 0 and ship.active.fuel.amount <= 0 and not self.flameout_noted:
            self.note("Flameout - stage out of fuel"); self.flameout_noted = True
        self.thrust_now = F
        m0 = ship.mass

        if self.landed_on is not None:
            b = self.landed_on
            ux, uy = self.land_rel[0] / b.radius, self.land_rel[1] / b.radius
            g = b.mu / b.radius ** 2
            up_thrust = F * (ca * ux + sa * uy)
            if up_thrust > m0 * g * 1.0001:
                self.landed_on = None; self.launched = True
                bvx, bvy = b.vel(self.t); self.vx, self.vy = bvx, bvy
                self.note("Liftoff!")
            else:
                ship.burn(burn)
                self.t += dt
                bx, by = b.pos(self.t); bvx, bvy = b.vel(self.t)
                self.x, self.y = bx + self.land_rel[0], by + self.land_rel[1]
                self.vx, self.vy = bvx, bvy
                self._post(dt); return

        # kick-drift-kick
        cda = ship.drag_area()
        def acc(x, y, vx, vy, t, F, m):
            ax, ay = U.accel(x, y, t)
            ax += F * ca / m; ay += F * sa / m
            rho = self._atmos(x, y)
            if rho > 0:
                v = math.hypot(vx, vy)
                k = 0.5 * rho * v * cda / m
                ax -= k * vx; ay -= k * vy
            return ax, ay
        ax, ay = acc(self.x, self.y, self.vx, self.vy, self.t, F, m0)
        vx = self.vx + 0.5 * dt * ax; vy = self.vy + 0.5 * dt * ay
        self.x += dt * vx; self.y += dt * vy
        ship.burn(burn)
        self.t += dt
        ax, ay = acc(self.x, self.y, vx, vy, self.t, F, ship.mass)
        self.vx = vx + 0.5 * dt * ax; self.vy = vy + 0.5 * dt * ay
        self._contact()
        self._post(dt)

    def _contact(self):
        for b in (self.u.earth, self.u.moon):
            bx, by = b.pos(self.t); bvx, bvy = b.vel(self.t)
            rx, ry = self.x - bx, self.y - by
            r = math.hypot(rx, ry)
            if r < b.radius:
                sp = math.hypot(self.vx - bvx, self.vy - bvy)
                ux, uy = rx / r, ry / r
                if sp <= SAFE_LANDING_SPEED and self.ship.has_role("lander") or (sp <= 2.0):
                    self.landed_on = b; self.land_rel = (ux * b.radius, uy * b.radius)
                    self.x, self.y = bx + self.land_rel[0], by + self.land_rel[1]
                    self.vx, self.vy = bvx, bvy
                    self.hold_angle = self.att
                    self.note(f"Touchdown on the {b.name} at {sp:.1f} m/s")
                else:
                    self.crashed = True
                    self.crash_msg = f"Crashed into the {b.name} at {sp:.0f} m/s"
                    self.note(self.crash_msg); self.throttle = 0.0
                return

    def _post(self, dt):
        body = self.dom()
        alt = self.altitude(body)
        if body is self.u.earth: self.max_alt = max(self.max_alt, alt)
        rho = self._atmos(self.x, self.y)
        v = math.hypot(self.vx, self.vy); self.q = 0.5 * rho * v * v
        if self.mission is not None: self.mission.update(self, dt)

    # ------------------------------------------------ stepping policy
    def choose_dt(self, remaining):
        body = self.dom(); alt = self.altitude(body)
        if self.landed_on is not None or self.throttle > 0 or alt < max(body.atm_height, 30000.0):
            dt = 0.02
        else:
            e, m = self.u.earth, self.u.moon
            de = math.hypot(self.x, self.y); mx, my = m.pos(self.t)
            dm = math.hypot(self.x - mx, self.y - my)
            dt = 0.02 * min(math.sqrt(de ** 3 / e.mu), math.sqrt(dm ** 3 / m.mu))
            dt = max(0.02, min(dt, 600.0))
        return min(dt, remaining)

    def advance(self, total, max_steps=800):
        rem = total; n = 0
        while rem > 1e-9 and n < max_steps:
            dt = self.choose_dt(rem)
            self.step(dt); rem -= dt; n += 1
            if self.crashed: break
        self._update_debris(total - rem)
        return total - rem

    def max_safe_warp(self):
        if self.crashed: return 1
        if self.throttle > 0: return 10
        alt = self.altitude()
        body = self.dom()
        if self.landed_on is not None: return 10
        if alt < body.atm_height: return 4
        if alt < 30000: return 4
        if alt < 100000 and body is self.u.moon: return 10
        return 100000

    def _update_debris(self, dt):
        if not self.debris: return
        if dt > 5: self.debris.clear(); return
        e = self.u.earth; keep = []
        for d in self.debris:
            ax, ay = self.u.accel(d["x"], d["y"], self.t)
            r = math.hypot(d["x"], d["y"]); alt = r - e.radius
            rho = e.density(alt)
            v = math.hypot(d["vx"], d["vy"])
            if rho > 0 and v > 0:
                k = 0.5 * rho * v * 0.5 / max(d["stage"].mass, 1.0)
                ax -= k * d["vx"]; ay -= k * d["vy"]
            d["vx"] += ax * dt; d["vy"] += ay * dt
            d["x"] += d["vx"] * dt; d["y"] += d["vy"] * dt
            d["age"] += dt
            if r > e.radius and d["age"] < 600: keep.append(d)
        self.debris = keep

    def predict(self, **kw):
        return predict(self.u, self.x, self.y, self.vx, self.vy, self.t, **kw)
