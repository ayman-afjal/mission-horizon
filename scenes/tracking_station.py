import pygame, math, json, os
from core.scene import SceneBase
from core.settings import *
from core.game import game
from ui.components import Btn, text, paragraph
from ui.panels import draw_panel, fmt_dist

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "nasa_data")

class TrackingStationScene(SceneBase):
    """Orbit reference chart: where real satellites live vs. your mission targets."""
    def __init__(self):
        super().__init__()
        self.back = Btn("Back", 80, 985, 200, 60, 24)
        R = game.universe.earth.radius
        self.marks = [("Karman line", 100e3, "mission"), ("Mission 2 target", 160e3, "mission"),
                      ("ISS (approx.)", 420e3, "sat"), ("GPS", 20200e3, "sat"), ("Geostationary", 35786e3, "sat"),
                      ("Moon", 384400e3 - R, "moon"), ("Moon SOI edge", 384400e3 - R - 66100e3, "moon")]
        try:
            with open(os.path.join(DATA, "satellite_orbits.json")) as f: self.raw = json.load(f)
        except (OSError, ValueError): self.raw = None

    def process_input(self, events, keys):
        for e in events:
            if self.back.is_clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                from scenes.space_center import SpaceCenterScene; self.switch_to(SpaceCenterScene())

    def update(self, dt=0.0): self.back.update(pygame.mouse.get_pos())

    def render(self, screen):
        screen.fill(BG)
        text(screen, "TRACKING STATION - ORBIT REFERENCE", (80, 70), 48, ACCENT, True)
        text(screen, "Altitude above Earth's surface, logarithmic scale", (82, 130), 24, DIM)
        draw_panel(screen, (70, 180, 1780, 780))
        R = game.universe.earth.radius
        x0, x1 = 160, 1760
        lo, hi = math.log10(50e3), math.log10(4e8)
        def X(alt): return x0 + (math.log10(max(alt, 50e3)) - lo) / (hi - lo) * (x1 - x0)
        pygame.draw.line(screen, PANEL_EDGE, (x0, 560), (x1, 560), 3)
        for e in range(5, 9):
            xx = X(10 ** e); pygame.draw.line(screen, PANEL_EDGE, (xx, 548), (xx, 572), 2)
            text(screen, fmt_dist(10 ** e), (xx, 585), 20, DIM, anchor="midtop")
        cols = {"mission": ACCENT, "sat": BLUE, "moon": (200, 200, 205)}
        for i, (name, alt, kind) in enumerate(sorted(self.marks, key=lambda m: m[1])):
            xx = X(alt); up = i % 2 == 0
            yy = 440 - (i % 4) * 50 if up else 680 + (i % 4) * 40
            pygame.draw.line(screen, cols[kind], (xx, 560), (xx, yy + (30 if up else 0)), 2)
            pygame.draw.circle(screen, cols[kind], (xx, 560), 8)
            text(screen, name, (xx, yy), 24, cols[kind], True, anchor="midbottom" if up else "midtop")
            text(screen, fmt_dist(alt), (xx, yy + (26 if not up else 24)), 18, DIM, anchor="midtop" if not up else "midtop")
        mu = game.universe.earth.mu
        text(screen, "Circular orbit speed / period at selected altitudes", (120, 730), 22, TEXT, True)
        for k, alt in enumerate([200e3, 420e3, 2000e3, 35786e3]):
            r = R + alt; v = math.sqrt(mu / r); T = 2 * math.pi * math.sqrt(r ** 3 / mu)
            text(screen, f"{fmt_dist(alt):>10}  ->  {v/1000:.2f} km/s,  {T/60:,.0f} min", (130, 764 + k * 26), 20, DIM, mono=True)
        text(screen, f"Escape speed at the surface: {math.sqrt(2*mu/R)/1000:.2f} km/s   |   Moon: {384400:,} km away, orbits Earth every 27.3 days",
             (120, 880), 22, DIM)
        text(screen, "Rule of thumb: ~9.4 km/s of Δv gets you to LEO (7.8 km/s orbital speed + gravity & drag losses); the Moon needs ~3.1 km/s more.", (120, 915), 22, TEXT)
        self.back.render(screen)
