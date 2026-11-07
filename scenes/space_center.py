import pygame
from core.scene import SceneBase
from core.settings import *
from core.game import game
from spacecraft.spacecraft import Spacecraft
from ui.components import Btn, text, paragraph
from ui.panels import draw_panel

def launch_check():
    """Returns (ok, [messages])."""
    m = game.mission()
    if not game.mission_available(m): return False, ["This mission is locked."]
    errs, _ = Spacecraft(game.design(m.id)).validate(m)
    return (not errs), errs

class SpaceCenterScene(SceneBase):
    def __init__(self):
        super().__init__()
        x, y, w, h, gap = 120, 250, 480, 90, 24
        self.buttons = {}
        labels = [("mission", "Mission Control"), ("vab", "Vehicle Assembly"), ("launch", "Launch Pad"),
                  ("research", "Research Lab"), ("tracking", "Tracking Station"), ("back", "Main Menu")]
        for i, (k, lab) in enumerate(labels):
            self.buttons[k] = Btn(lab, x, y + i * (h + gap) - 0, w, h, 30, accent=(k == "launch"))
        self.msg = []
        self.stars = 0

    def process_input(self, events, keys):
        b = self.buttons
        for e in events:
            if b["mission"].is_clicked(e):
                from scenes.mission_control import MissionControlScene; self.switch_to(MissionControlScene())
            elif b["vab"].is_clicked(e):
                from scenes.vab import VABScene; self.switch_to(VABScene())
            elif b["launch"].is_clicked(e):
                ok, msgs = launch_check(); self.msg = msgs
                if ok:
                    from scenes.flight import FlightScene; self.switch_to(FlightScene())
            elif b["research"].is_clicked(e):
                from scenes.research_lab import ResearchLabScene; self.switch_to(ResearchLabScene())
            elif b["tracking"].is_clicked(e):
                from scenes.tracking_station import TrackingStationScene; self.switch_to(TrackingStationScene())
            elif b["back"].is_clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                from scenes.menu_scene import MenuScene; self.switch_to(MenuScene())

    def update(self, dt=0.0):
        mp = pygame.mouse.get_pos()
        for b in self.buttons.values(): b.update(mp)

    def render(self, screen):
        screen.fill(BG)
        # simple backdrop: horizon glow
        for i in range(120):
            c = (14 + i // 8, 16 + i // 6, 24 + i // 3)
            pygame.draw.line(screen, c, (0, 960 + i), (WIDTH, 960 + i))
        text(screen, "SPACE CENTER", (120, 100), 64, ACCENT, True)
        text(screen, "Design it. Script it. Fly it.", (124, 176), 28, DIM)
        for b in self.buttons.values(): b.render(screen)
        m = game.mission()
        draw_panel(screen, (720, 250, 1080, 420), "Active mission")
        text(screen, f"{m.name}", (745, 305), 40, TEXT, True)
        y = paragraph(screen, m.brief, (745, 360), 1030, 24, DIM)
        y += 10
        for o in m.objectives: text(screen, "- " + o.label, (745, y), 24, ACCENT); y += 32
        text(screen, f"Budget ${m.budget:.1f}M   Parts {m.max_parts}   Max mass {m.max_mass/1000:.0f} t", (745, y + 14), 22, TEXT)
        s = game.completed.get(m.id, 0)
        text(screen, f"Completed - {s}/3 stars" if s else "Not yet completed", (745, 610), 24, GOOD if s else DIM)
        draw_panel(screen, (720, 700, 1080, 300), "Launch readiness")
        ok, msgs = launch_check()
        design = Spacecraft(game.design(m.id))
        text(screen, f"Craft: {len(design.parts)} parts, {design.mass/1000:.1f} t, ${design.total_cost:.1f}M", (745, 755), 24)
        if not self.msg and ok: text(screen, "Ready for launch.", (745, 795), 26, GOOD, True)
        yy = 795
        for t in (self.msg or msgs)[:5]:
            text(screen, "[X] " + t, (745, yy), 22, BAD, maxw=1020); yy += 30
        done = [k for k in game.completed]
        text(screen, f"Missions completed: {len(done)}/{len([m for m in game.missions if m.available])}", (745, 960), 20, DIM)
