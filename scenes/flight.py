import math, random
import pygame
from core.scene import SceneBase
from core.settings import *
from core.game import game
from core.time import TimeWarp
from physics.sim import FlightSim
from physics.constants import G0
from spacecraft.spacecraft import Spacecraft
from scripting.parser import parse
from scripting.executor import Executor
from ui.components import Btn, text, paragraph
from ui.panels import draw_panel, fmt_dist, fmt_time

CAT_COL = {"pod": (205, 205, 215), "payload": (110, 190, 230), "tank": (225, 225, 230),
           "engine": (150, 90, 60), "decoupler": (120, 120, 140)}
SAS_KEYS = {pygame.K_1: "hold", pygame.K_2: "prograde", pygame.K_3: "retrograde", pygame.K_4: "radial_out", pygame.K_5: "radial_in"}
PX = 0.42  # vertical position of the ship on screen (fraction)

def lerp(a, b, t): return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

class FlightScene(SceneBase):
    def __init__(self):
        super().__init__()
        self.mission = game.mission(); self.mission.reset()
        self.U = game.universe
        self.design = game.design(self.mission.id)
        self.ship = Spacecraft(self.design)
        self.cost = self.ship.total_cost
        self.sim = FlightSim(self.U, self.ship, self.mission)
        prog, errs = parse(game.script(self.mission.id))
        self.script_errors = errs
        self.exec = Executor(prog) if (prog and not errs) else None
        self.script_on = False
        self.warp = TimeWarp()
        self.zoom = max(0.5, min(60.0, 170.0 / max(self.ship.height(), 1.0)))
        self._fit_pending = False; self.auto_zoom = True
        self.map = False; self.map_zoom = 1.4e-5; self.map_focus = None
        self.pred = None; self.pred_t = -1; self.pred_key = None
        self.paused = False; self.show_help = True
        self.overlay = None   # "success" | "crashed" | None
        self.overlay_seen = False
        self.stars = 0
        random.seed(7); self.stars_bg = [(random.random(), random.random(), random.random()) for _ in range(160)]
        self.real_t = 0.0
        self.b_resume = Btn("Resume", 760, 400, 400, 64, 28)
        self.b_restart = Btn("Restart flight", 760, 480, 400, 64, 28)
        self.b_abort = Btn("Abort to Space Center", 760, 560, 400, 64, 28)
        self.b_keep = Btn("Keep flying", 700, 640, 240, 64, 26)
        self.b_exit = Btn("Space Center", 980, 640, 240, 64, 26, accent=True)
        self.seen_log = 0

    # ------------------------------------------------------------ input
    def _exit(self):
        if self.mission.complete:
            nxt = next((m for m in game.missions if m.order > self.mission.order and game.mission_available(m)), None)
            if nxt and game.selected == self.mission.id: game.selected = nxt.id
        game.save()
        from scenes.space_center import SpaceCenterScene; self.switch_to(SpaceCenterScene())

    def process_input(self, events, keys):
        sim = self.sim
        for e in events:
            if self.overlay and not self.overlay_seen:
                if self.b_exit.is_clicked(e): self._exit(); return
                if self.b_keep.is_clicked(e) and self.overlay == "success": self.overlay_seen = True
                if self.b_keep.is_clicked(e) and self.overlay == "crashed": self.switch_to(FlightScene()); return
                continue
            if self.paused:
                if self.b_resume.is_clicked(e): self.paused = False
                if self.b_restart.is_clicked(e): self.switch_to(FlightScene()); return
                if self.b_abort.is_clicked(e): self._exit(); return
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: self.paused = False
                continue
            if e.type == pygame.KEYDOWN:
                k = e.key
                if k == pygame.K_ESCAPE: self.paused = True
                elif k == pygame.K_SPACE: sim.stage()
                elif k == pygame.K_z: sim.set_throttle(1.0)
                elif k == pygame.K_x: sim.set_throttle(0.0)
                elif k in SAS_KEYS: sim.set_sas(SAS_KEYS[k])
                elif k == pygame.K_PERIOD: self.warp.up(sim.max_safe_warp())
                elif k == pygame.K_COMMA: self.warp.down()
                elif k == pygame.K_m: self.map = not self.map; self.pred = None; self._fit_pending = self.map
                elif k == pygame.K_h: self.show_help = not self.show_help
                elif k == pygame.K_c: self.auto_zoom = True
                elif k == pygame.K_TAB: self.map_focus = "moon" if self._focus().key == "earth" else "earth"
                elif k == pygame.K_p: self._toggle_script()
                elif k == pygame.K_f and self.map: self.map_zoom = self._fit_zoom()
            if e.type == pygame.MOUSEWHEEL:
                f = 1.2 ** e.y
                if self.map: self.map_zoom = max(1e-9, min(1e-3, self.map_zoom * f))
                else: self.zoom = max(0.002, min(80.0, self.zoom * f)); self.auto_zoom = False
        if not self.paused and not self.overlay:
            dt = 1 / 60
            if keys[pygame.K_a]: sim.manual_rotate(+1, dt)
            if keys[pygame.K_d]: sim.manual_rotate(-1, dt)
            if keys[pygame.K_LSHIFT]: sim.set_throttle(sim.throttle + 0.6 * dt)
            if keys[pygame.K_LCTRL]: sim.set_throttle(sim.throttle - 0.6 * dt)

    def _toggle_script(self):
        if self.exec is None: sim_msg = "Script has errors" if self.script_errors else "No script"; self.sim.note(sim_msg); return
        self.script_on = not self.script_on
        self.sim.script = self.exec if self.script_on else None
        self.exec.enabled = True
        self.sim.note("Autopilot script ON" if self.script_on else "Autopilot script OFF")

    # ------------------------------------------------------------ update
    def update(self, dt=0.0):
        mp = pygame.mouse.get_pos()
        for b in (self.b_resume, self.b_restart, self.b_abort, self.b_keep, self.b_exit): b.update(mp)
        if self.paused or (self.overlay and not self.overlay_seen): return
        sim = self.sim
        if sim.requested_warp: self.warp.set_factor(sim.requested_warp); sim.requested_warp = None
        self.warp.clamp(sim.max_safe_warp())
        sim.advance(dt * self.warp.factor, max_steps=700 if self.warp.factor > 1 else 20)
        if sim.launched and self.show_help and self.real_t > 0: self.show_help = False
        if self.auto_zoom:
            target = max(0.5, min(60.0, 170.0 / max(self.ship.height(), 1.0)))
            self.zoom += (target - self.zoom) * min(1.0, 3 * dt)
        self.real_t += dt
        if self.mission.complete and self.overlay is None:
            self.stars = self.mission.stars(self.cost); game.complete(self.mission.id, self.stars)
            self.overlay = "success"; self.warp.reset()
        elif sim.crashed and self.overlay is None:
            self.overlay = "crashed"; self.warp.reset()

    # ------------------------------------------------------------ geometry
    def _focus(self):
        if self.map_focus: return self.U.bodies[self.map_focus]
        return self.sim.dom()

    def _frame(self):
        sim = self.sim; body = sim.dom()
        rx, ry, _, _ = sim.rel(body)
        r = math.hypot(rx, ry)
        phi = math.pi / 2 - math.atan2(ry, rx)
        return body, r, phi

    def _w2s(self, wx, wy, c, s):
        dx = wx - self.sim.x; dy = wy - self.sim.y
        xp = dx * c - dy * s; yp = dx * s + dy * c
        return (WIDTH / 2 + xp * self.zoom, HEIGHT * PX - yp * self.zoom)

    # ------------------------------------------------------------ drawing: flight view
    def _draw_body(self, screen, ctr, rad, color, soft=None):
        if rad < 2: pygame.draw.circle(screen, color, (int(ctr[0]), int(ctr[1])), 2); return
        dist = math.hypot(ctr[0] - WIDTH / 2, ctr[1] - HEIGHT / 2)
        if dist - rad > math.hypot(WIDTH, HEIGHT): return
        if rad < 6000: pygame.draw.circle(screen, color, (int(ctr[0]), int(ctr[1])), int(rad)); return
        # huge circle: draw only the visible arc as a polygon, thickened inward
        a0 = math.atan2(HEIGHT / 2 - ctr[1], WIDTH / 2 - ctr[0])
        half = min(math.pi, (math.hypot(WIDTH, HEIGHT) / rad) * 1.2 + 0.01)
        n = 48
        outer = []; inner = []
        for i in range(n + 1):
            a = a0 - half + 2 * half * i / n
            outer.append((ctr[0] + rad * math.cos(a), ctr[1] + rad * math.sin(a)))
            inner.append((ctr[0] + (rad - 4000) * math.cos(a), ctr[1] + (rad - 4000) * math.sin(a)))
        pygame.draw.polygon(screen, color, outer + inner[::-1])

    def _draw_stack(self, screen, parts, ctr, ang, zoom_px, flame=0.0):
        """Draw a stack of parts centred at ctr, nose along angle ang (screen, y-up angle)."""
        L = sum(p.length for p in parts)
        ax, ay = math.cos(ang), -math.sin(ang)       # screen-space axis (y down)
        px, py = -ay, ax
        off = L / 2
        for p in parts:
            w = max(p.diameter * zoom_px, 1.0) / 2
            a = off * zoom_px; b = (off - p.length) * zoom_px
            c = CAT_COL.get(p.category, (200, 200, 200))
            pts = [(ctr[0] + ax * a + px * w, ctr[1] + ay * a + py * w), (ctr[0] + ax * a - px * w, ctr[1] + ay * a - py * w),
                   (ctr[0] + ax * b - px * w, ctr[1] + ay * b - py * w), (ctr[0] + ax * b + px * w, ctr[1] + ay * b + py * w)]
            if p.category == "engine":
                n = 0.55
                pts = [pts[0], pts[1], (ctr[0] + ax * b - px * w, ctr[1] + ay * b - py * w), (ctr[0] + ax * b + px * w, ctr[1] + ay * b + py * w)]
                pts[0] = (ctr[0] + ax * a + px * w * n, ctr[1] + ay * a + py * w * n); pts[1] = (ctr[0] + ax * a - px * w * n, ctr[1] + ay * a - py * w * n)
            pygame.draw.polygon(screen, c, pts)
            off -= p.length
        if flame > 0:
            e = (off * zoom_px)
            w = max(parts[-1].diameter * zoom_px, 2) * 0.45
            ln = max(L * zoom_px * 0.6 * flame, 3)
            tip = (ctr[0] + ax * (e - ln), ctr[1] + ay * (e - ln))
            pts = [(ctr[0] + ax * e + px * w, ctr[1] + ay * e + py * w), (ctr[0] + ax * e - px * w, ctr[1] + ay * e - py * w), tip]
            pygame.draw.polygon(screen, (255, 170, 50), pts)
            pygame.draw.polygon(screen, (255, 240, 170), [((pts[0][0] + tip[0]) / 2, (pts[0][1] + tip[1]) / 2), ((pts[1][0] + tip[0]) / 2, (pts[1][1] + tip[1]) / 2), tip])

    def _render_flight(self, screen):
        sim = self.sim; U = self.U
        body, r, phi = self._frame()
        c, s = math.cos(phi), math.sin(phi)
        alt = r - body.radius
        # sky
        if body.key == "earth":
            t = min(1.0, max(0.0, alt / 75000.0)) ** 0.6
            sky = lerp((98, 160, 235), (4, 5, 11), t)
        else: sky = (4, 5, 11); t = 1.0
        screen.fill(sky)
        if t > 0.35:
            for x, y, b in self.stars_bg:
                v = int(255 * min(1, (t - 0.35) * 2) * (0.4 + 0.6 * b)); screen.set_at((int(x * WIDTH), int(y * HEIGHT)), (v, v, v))
        # bodies
        for b in (U.earth, U.moon):
            bx, by = b.pos(sim.t)
            ctr = self._w2s(bx, by, c, s); rad = b.radius * self.zoom
            col = (80, 112, 66) if (b.key == "earth" and rad > 5000) else b.color
            if b.key == "moon" and rad > 5000: col = (140, 140, 145)
            if b.key == "earth" and 0 < rad < 6000:
                halo = int((b.radius + b.atm_height) * self.zoom)
                if halo > 4: pygame.draw.circle(screen, (60, 100, 170), (int(ctr[0]), int(ctr[1])), halo)
            self._draw_body(screen, ctr, rad, col)
        # ground ticks + pad near the surface
        if alt < 6000 and self.zoom > 0.05:
            bx, by = body.pos(sim.t); rx, ry = sim.x - bx, sim.y - by; ang = math.atan2(ry, rx)
            step = 250.0 / body.radius; k0 = round(ang / step)
            for k in range(k0 - 40, k0 + 41):
                a = k * step; p0 = self._w2s(bx + body.radius * math.cos(a), by + body.radius * math.sin(a), c, s)
                p1 = self._w2s(bx + (body.radius + 40) * math.cos(a), by + (body.radius + 40) * math.sin(a), c, s)
                pygame.draw.line(screen, (60, 90, 55) if body.key == "earth" else (95, 95, 100), p0, p1, 2)
            if body.key == "earth":
                for dx, w in ((-60, 8), (60, 8)):
                    q = [(dx - w, 0), (dx + w, 0), (dx + w, 30), (dx - w, 30)]
                pad = [self._w2s(x, body.radius + yy, c, s) for x, yy in ((-25, 0), (25, 0), (25, 2), (-25, 2))]
                pygame.draw.polygon(screen, (120, 120, 130), pad)
                tw = [self._w2s(x, body.radius + yy, c, s) for x, yy in ((-32, 0), (-28, 0), (-28, 45), (-32, 45))]
                pygame.draw.polygon(screen, (160, 70, 60), tw)
        # debris
        for d in sim.debris:
            p = self._w2s(d["x"], d["y"], c, s)
            if -200 < p[0] < WIDTH + 200 and -200 < p[1] < HEIGHT + 200:
                self._draw_stack(screen, d["stage"].parts, p, d["att"] + phi, self.zoom)
        # ship
        ctr = (WIDTH / 2, HEIGHT * PX)
        if not sim.crashed:
            ang = sim.att + phi
            L = self.ship.height()
            if L * self.zoom < 14:
                a = ang; sz = 9
                pts = [(ctr[0] + math.cos(a) * sz * 1.4, ctr[1] - math.sin(a) * sz * 1.4),
                       (ctr[0] + math.cos(a + 2.5) * sz, ctr[1] - math.sin(a + 2.5) * sz),
                       (ctr[0] + math.cos(a - 2.5) * sz, ctr[1] - math.sin(a - 2.5) * sz)]
                pygame.draw.polygon(screen, (255, 255, 255), pts)
            else:
                self.ship_parts = [p for st in self.ship.stages for p in st.parts]
                self._draw_stack(screen, self.ship_parts, ctr, ang, self.zoom, flame=sim.throttle if sim.thrust_now > 0 else 0)
        else:
            pygame.draw.circle(screen, (255, 120, 40), (int(ctr[0]), int(ctr[1])), 30, 4)
            text(screen, "VEHICLE LOST", (ctr[0], ctr[1] - 60), 36, BAD, True, anchor="center")
        return body, phi

    # ------------------------------------------------------------ drawing: map view
    def _fit_zoom(self):
        pred = self.pred
        f = self._focus(); fx, fy = f.pos(self.sim.t)
        far = f.radius * 1.7
        if f.key == "moon":
            fx, fy = f.pos(self.sim.t); d = math.hypot(self.sim.x - fx, self.sim.y - fy)
            far = max(far, min(d * 1.3, 1.5 * f.soi), f.radius * 8)
        elif pred:
            for t, x, y in pred.pts[::5]:
                far = max(far, math.hypot(x, y))
        return 0.42 * min(WIDTH, HEIGHT) / far

    def _render_map(self, screen):
        sim = self.sim; U = self.U
        screen.fill((8, 10, 18))
        f = self._focus(); z = self.map_zoom
        cx, cy = WIDTH / 2 + 80, HEIGHT / 2
        fp = f.pos(sim.t)
        def P(x, y, t=None):
            if f.key == "moon" and t is not None:
                mx, my = U.moon.pos(t); x -= mx; y -= my
            elif f.key == "moon": x -= fp[0]; y -= fp[1]
            return (cx + x * z, cy - y * z)
        for b in (U.earth, U.moon):
            bx, by = b.pos(sim.t); p = P(bx, by, sim.t)
            rad = max(b.radius * z, 4)
            if abs(p[0] - cx) < 4000 and abs(p[1] - cy) < 4000 and rad < 4000:
                pygame.draw.circle(screen, b.color, (int(p[0]), int(p[1])), int(rad))
                if b.key == "earth" and (b.radius + b.atm_height) * z > rad:
                    pygame.draw.circle(screen, (70, 110, 190), (int(p[0]), int(p[1])), int((b.radius + b.atm_height) * z), 1)
            text(screen, b.name, (p[0] + rad + 6, p[1] - 10), 18, DIM)
            if b.soi:
                sr = b.soi * z
                if 3 < sr < 3000: pygame.draw.circle(screen, (70, 80, 100), (int(p[0]), int(p[1])), int(sr), 1)
        if f.key == "earth":
            mr = U.moon.orbit_r * z
            if 3 < mr < 4000: pygame.draw.circle(screen, (50, 56, 70), (int(P(0, 0)[0]), int(P(0, 0)[1])), int(mr), 1)
        # prediction
        key = (round(sim.t / 2), round(sim.throttle, 1), len(self.ship.stages), self.map_focus)
        if self.pred is None or self.real_t - self.pred_t > (0.25 if sim.throttle > 0 else 0.6):
            if not sim.crashed and sim.landed_on is None:
                self.pred = sim.predict(max_points=1800 if sim.throttle > 0 else 2600); self.pred_t = self.real_t
            else: self.pred = None
        pred = self.pred
        if self._fit_pending and (pred or sim.landed_on is not None):
            self.map_zoom = self._fit_zoom(); self._fit_pending = False; z = self.map_zoom
        if pred and len(pred.pts) > 1:
            src = pred.pts
            if f.key == "moon":
                lim = 1.5 * f.soi; keep = []
                for t, x, y in src:
                    mx, my = f.pos(t)
                    if math.hypot(x - mx, y - my) > lim:
                        if keep: break
                        continue
                    keep.append((t, x, y))
                src = keep if len(keep) > 1 else src[:2]
            pts = [P(x, y, t) for t, x, y in src]
            pts = [(max(-5000, min(6000, a)), max(-5000, min(6000, b))) for a, b in pts]
            pygame.draw.lines(screen, (90, 170, 255), False, pts, 2)
            dom = sim.dom()
            ds = [(math.hypot(x - dom.pos(t)[0], y - dom.pos(t)[1]), i) for i, (t, x, y) in enumerate(src)]
            if len(ds) > 3 and (dom.key == f.key):
                lo = min(ds); hi = max(ds)
                for (d, i), lab in ((lo, "Pe"), (hi, "Ap")):
                    q = pts[i]; pygame.draw.circle(screen, (255, 200, 60), (int(q[0]), int(q[1])), 5, 2)
                    text(screen, f"{lab} {fmt_dist(d - dom.radius)}", (q[0] + 8, q[1] - 8), 18, ACCENT)
            if pred.impact and len(src) == len(pred.pts):
                q = pts[-1]; pygame.draw.line(screen, BAD, (q[0] - 7, q[1] - 7), (q[0] + 7, q[1] + 7), 3); pygame.draw.line(screen, BAD, (q[0] - 7, q[1] + 7), (q[0] + 7, q[1] - 7), 3)
                text(screen, f"Impact {pred.impact[0].title()} in {fmt_time(pred.impact[1] - sim.t)}", (q[0] + 10, q[1] + 6), 18, BAD)
            if pred.moon_ca and f.key == "earth":
                tca, dist = pred.moon_ca
                mx, my = U.moon.pos(tca); mp = P(mx, my)
                if dist < 3 * U.moon.soi:
                    pygame.draw.circle(screen, (180, 180, 190), (int(mp[0]), int(mp[1])), max(4, int(U.moon.radius * z)), 1)
                    pygame.draw.circle(screen, (110, 120, 150), (int(mp[0]), int(mp[1])), max(8, int(U.moon.soi * z)), 1)
                    text(screen, f"Moon @ T+{fmt_time(tca - sim.t)}", (mp[0] + 12, mp[1] + 14), 18, DIM)
        sp = P(sim.x, sim.y, sim.t)
        pygame.draw.circle(screen, (255, 255, 255), (int(sp[0]), int(sp[1])), 6, 2)
        text(screen, "Ship", (sp[0] + 10, sp[1] - 22), 18, TEXT)
        # info
        draw_panel(screen, (30, 30, 520, 250), "Map view")
        o, dom = sim.orbit(); y = 80
        for k, v in [("Orbiting", dom.name), ("Apoapsis", fmt_dist(o.ra - dom.radius) if o.bound else "escape"), ("Periapsis", fmt_dist(o.rp - dom.radius)),
                     ("Period", fmt_time(o.period)), ("Eccentricity", f"{o.e:.3f}")]:
            text(screen, k, (50, y), 20, DIM); text(screen, v, (300, y), 20, TEXT, True); y += 28
        if pred and pred.moon_ca and pred.moon_ca[1] < 2.2 * U.moon.soi:
            tca, dist = pred.moon_ca
            text(screen, f"Moon closest approach: {fmt_dist(dist - U.moon.radius)} alt in {fmt_time(tca - sim.t)}", (50, y + 4), 19, ACCENT if dist < U.moon.soi else DIM)
        text(screen, "Wheel: zoom | F: fit | Tab: Earth/Moon focus | M: back to flight", (30, HEIGHT - 40), 20, DIM)

    # ------------------------------------------------------------ HUD
    def _navball(self, screen, ctr, R, body, phi):
        sim = self.sim
        pygame.draw.circle(screen, (30, 34, 48), ctr, R + 6)
        pygame.draw.circle(screen, (60, 100, 160), ctr, R)
        # ground half: below horizon = opposite of radial-up (screen up in our rotated frame)
        rect = pygame.Rect(ctr[0] - R, ctr[1] - R, 2 * R, 2 * R)
        surf = pygame.Surface((2 * R, 2 * R), pygame.SRCALPHA)
        pygame.draw.rect(surf, (110, 80, 50), (0, R, 2 * R, R))
        mask = pygame.Surface((2 * R, 2 * R), pygame.SRCALPHA); pygame.draw.circle(mask, (255, 255, 255, 255), (R, R), R)
        surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        screen.blit(surf, rect.topleft)
        pygame.draw.line(screen, (240, 240, 240), (ctr[0] - R, ctr[1]), (ctr[0] + R, ctr[1]), 2)
        def mark(a, col, r=8, ring=True):
            x = ctr[0] + math.cos(a) * R * 0.75; y = ctr[1] - math.sin(a) * R * 0.75
            pygame.draw.circle(screen, col, (int(x), int(y)), r, 2 if ring else 0)
        # attitude arrow
        a = sim.att + phi
        tip = (ctr[0] + math.cos(a) * R * 0.9, ctr[1] - math.sin(a) * R * 0.9)
        pygame.draw.line(screen, ACCENT, ctr, tip, 4); pygame.draw.circle(screen, ACCENT, (int(tip[0]), int(tip[1])), 6)
        rx, ry, vx, vy = sim.rel(body)
        if math.hypot(vx, vy) > 1.0:
            va = math.atan2(vy, vx) + phi
            mark(va, GOOD); mark(va + math.pi, BAD)
        text(screen, "up", (ctr[0], ctr[1] - R - 22), 16, DIM, anchor="midtop")

    def _render_hud(self, screen, body, phi):
        sim = self.sim; T = sim.telemetry(); m = self.mission
        # telemetry (right)
        draw_panel(screen, (WIDTH - 450, 20, 430, 470), "Telemetry")
        y = 68
        def row(k, v, col=TEXT):
            nonlocal y
            text(screen, k, (WIDTH - 430, y), 20, DIM); text(screen, v, (WIDTH - 40, y), 20, col, True, anchor="topright"); y += 28
        row("Body", body.name)
        row("Altitude", fmt_dist(T.altitude)); row("Speed", f"{T.speed:,.0f} m/s")
        row("Vertical", f"{T.vertical_speed:,.0f} m/s"); row("Horizontal", f"{T.horizontal_speed:,.0f} m/s")
        row("Apoapsis", fmt_dist(T.apoapsis) if T.apoapsis != math.inf else "escape")
        row("Periapsis", fmt_dist(T.periapsis), BAD if T.periapsis < 0 else TEXT)
        row("ETA apoapsis", fmt_time(T.eta_apoapsis)); row("ETA periapsis", fmt_time(T.eta_periapsis))
        row("Eccentricity", f"{T.eccentricity:.3f}"); row("Dyn. pressure", f"{T.q/1000:.1f} kPa", WARN if T.q > 30000 else TEXT)
        row("Mission time", "T+" + fmt_time(sim.t)); row("Mass", f"{T.mass/1000:,.2f} t")
        rep = self.ship.stage_report(g_surface=body.mu / body.radius ** 2)
        dv = sum(r["dv_vac"] for r in rep); row("Δv left (vac)", f"{dv:,.0f} m/s")
        # bottom centre: controls
        draw_panel(screen, (WIDTH / 2 - 330, HEIGHT - 150, 660, 135))
        cx = WIDTH / 2 - 300
        text(screen, "THR", (cx, HEIGHT - 140), 16, DIM, True)
        pygame.draw.rect(screen, (40, 44, 58), (cx, HEIGHT - 116, 26, 90), border_radius=4)
        h = int(90 * sim.throttle); pygame.draw.rect(screen, ACCENT, (cx, HEIGHT - 26 - h, 26, h), border_radius=4)
        text(screen, f"{sim.throttle*100:.0f}%", (cx + 13, HEIGHT - 22), 16, TEXT, anchor="midtop")
        text(screen, "FUEL", (cx + 50, HEIGHT - 140), 16, DIM, True)
        fr = self.ship.active.fuel.fraction
        pygame.draw.rect(screen, (40, 44, 58), (cx + 50, HEIGHT - 116, 22, 90), border_radius=4)
        h = int(90 * fr); pygame.draw.rect(screen, GOOD if fr > 0.15 else BAD, (cx + 50, HEIGHT - 26 - h, 22, h), border_radius=4)
        text(screen, f"TWR {T.twr:.2f}", (cx + 95, HEIGHT - 116), 20, TEXT, True)
        text(screen, f"SAS: {sim.sas}" + (f" {sim.pitch_deg:.0f}°" if sim.sas == "pitch" else ""), (cx + 95, HEIGHT - 88), 20, TEXT, True)
        wf = self.warp.factor
        text(screen, f"Warp x{wf:,}" + ("" if wf <= sim.max_safe_warp() else " (limited)"), (cx + 95, HEIGHT - 60), 20, WARN if wf > 1 else DIM, True)
        text(screen, f"Stages left: {len(self.ship.stages) - 1}", (cx + 95, HEIGHT - 32), 18, DIM)
        self._navball(screen, (WIDTH // 2 + 220, HEIGHT - 82), 52, body, phi)
        # script / autopilot
        if self.exec:
            col = GOOD if self.script_on else DIM
            ln = self.exec.current_line
            st = "ON" if self.script_on else "OFF (press P)"
            if self.exec.finished: st += " - finished"
            text(screen, f"Autopilot {st}" + (f"   line {ln}" if ln and self.script_on else ""), (WIDTH / 2 - 330, HEIGHT - 175), 20, col, True)
        elif self.script_errors:
            text(screen, f"Script error line {self.script_errors[0][0]} - fix it in Mission Control", (WIDTH / 2 - 330, HEIGHT - 175), 20, BAD, True)
        # mission panel
        draw_panel(screen, (20, 20, 470, 60 + 34 * len(m.objectives) + 70), m.name)
        y = 66
        for o in m.objectives:
            col = GOOD if o.done else TEXT
            text(screen, ("[OK] " if o.done else "[ ] ") + o.label, (36, y), 20, col, True, maxw=440); y += 30
            if not o.done and o.hold > 0 and o.timer > 0:
                ProgressRect = pygame.Rect(36, y - 4, 300, 8); pygame.draw.rect(screen, (40, 44, 58), ProgressRect)
                pygame.draw.rect(screen, ACCENT, (36, y - 4, int(300 * min(1, o.timer / o.hold)), 8)); y += 10
        text(screen, f"Max altitude {fmt_dist(sim.max_alt)}   Cost ${self.cost:.1f}M / ${m.budget:.1f}M", (36, y + 4), 18, DIM, maxw=440)
        # log
        y0 = HEIGHT - 40
        for t, msg in sim.log[-7:][::-1]:
            text(screen, f"T+{fmt_time(t)}  {msg}", (20, y0), 20, TEXT if sim.t - t < 12 else (190, 196, 210), shadow=True); y0 -= 26
        # idle prompt
        if sim.landed_on is not None and not sim.launched and sim.t < 1 + (0 if not self.script_on else 0) and sim.throttle == 0:
            text(screen, "Z = full throttle    P = run mission script    Space = stage    H = help", (WIDTH / 2, 120), 28, ACCENT, True, anchor="center")
        if self.show_help:
            draw_panel(screen, (20, 560, 470, 400), "Controls (H hides)")
            lines = ["Z / X  full / cut throttle", "Shift / Ctrl  throttle up / down", "A / D  rotate (switches SAS to hold)",
                     "1-5  SAS: hold, prograde, retrograde,", "      radial out, radial in", "Space  stage (drops bottom stage)",
                     ". / ,  time warp up / down", "Wheel  zoom (C: auto)   M  map view", "P  toggle autopilot script", "Esc  pause menu"]
            for i, ln in enumerate(lines): text(screen, ln, (36, 608 + i * 28), 19, TEXT)

    def _render_overlays(self, screen):
        if self.paused:
            s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); s.fill((0, 0, 0, 150)); screen.blit(s, (0, 0))
            draw_panel(screen, (700, 300, 520, 360), "Paused")
            for b in (self.b_resume, self.b_restart, self.b_abort): b.render(screen)
        if self.overlay and not self.overlay_seen:
            s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); s.fill((0, 0, 0, 160)); screen.blit(s, (0, 0))
            draw_panel(screen, (660, 300, 600, 460), "Mission report")
            if self.overlay == "success":
                text(screen, "MISSION SUCCESS", (WIDTH / 2, 380), 52, GOOD, True, anchor="center")
                text(screen, f"{self.stars} / 3 stars", (WIDTH / 2, 450), 36, ACCENT, True, anchor="center")
                text(screen, f"Cost ${self.cost:.1f}M of ${self.mission.budget:.1f}M budget", (WIDTH / 2, 505), 24, TEXT, anchor="center")
                text(screen, "2 stars: under 70% of budget   3 stars: under 50%", (WIDTH / 2, 540), 20, DIM, anchor="center")
                if self.mission.unlocks:
                    text(screen, "Unlocked: " + ", ".join(game.db.get(u).name for u in self.mission.unlocks), (WIDTH / 2, 585), 20, GOOD, anchor="center", maxw=560)
                self.b_keep.set_text("Keep flying")
            else:
                text(screen, "VEHICLE LOST", (WIDTH / 2, 380), 52, BAD, True, anchor="center")
                text(screen, self.sim.crash_msg, (WIDTH / 2, 450), 26, TEXT, anchor="center")
                text(screen, "Check your Δv, TWR and staging in the VAB, then try again.", (WIDTH / 2, 500), 22, DIM, anchor="center")
                self.b_keep.set_text("Retry")
            self.b_keep.render(screen); self.b_exit.render(screen)

    def render(self, screen):
        if self.map:
            self._render_map(screen)
            body, r, phi = self._frame()
            self._render_hud_min(screen)
        else:
            body, phi = self._render_flight(screen)
            self._render_hud(screen, body, phi)
        self._render_overlays(screen)

    def _render_hud_min(self, screen):
        sim = self.sim
        wf = self.warp.factor
        text(screen, f"Warp x{wf:,}   Throttle {sim.throttle*100:.0f}%   T+{fmt_time(sim.t)}   alt {fmt_dist(sim.altitude())}", (WIDTH - 40, HEIGHT - 40), 22, TEXT, True, anchor="topright")
        y0 = HEIGHT - 80
        for t, msg in sim.log[-4:][::-1]:
            text(screen, f"T+{fmt_time(t)}  {msg}", (WIDTH - 40, y0), 18, TEXT if sim.t - t < 12 else DIM, anchor="topright"); y0 -= 22
