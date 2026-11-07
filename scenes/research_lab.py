import pygame
from core.scene import SceneBase
from core.settings import *
from core.game import game
from ui.components import Btn, ListBox, text, paragraph
from ui.panels import draw_panel

class ResearchLabScene(SceneBase):
    """Part catalogue and unlock tree: finish missions to unlock hardware."""
    def __init__(self):
        super().__init__()
        self.parts = sorted(game.db.parts.values(), key=lambda p: (["pod", "payload", "tank", "engine", "decoupler"].index(p.category), p.mass))
        self.list = ListBox((80, 180, 640, 780), 58)
        for p in self.parts:
            ok = game.part_unlocked(p)
            sub = p.category.title() + ("" if ok else f"   - locked: complete {game.mission(p.unlock).name}")
            self.list.items.append(dict(label=p.name, sub=sub, enabled=ok, color=TEXT if ok else DIM))
        self.back = Btn("Back", 80, 985, 200, 60, 24)
        self.reset = Btn("Reset progress", 1560, 985, 280, 60, 22)
        self.confirm = False

    def process_input(self, events, keys):
        for e in events:
            i = self.list.handle(e)
            if i is not None: self.list.selected = i
            if self.back.is_clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                from scenes.space_center import SpaceCenterScene; self.switch_to(SpaceCenterScene())
            if self.reset.is_clicked(e):
                if self.confirm: game.reset(); from scenes.space_center import SpaceCenterScene; self.switch_to(SpaceCenterScene())
                else: self.confirm = True; self.reset.set_text("Click again to confirm")

    def update(self, dt=0.0):
        mp = pygame.mouse.get_pos(); self.back.update(mp); self.reset.update(mp)

    def render(self, screen):
        screen.fill(BG)
        text(screen, "RESEARCH LAB - PART CATALOGUE", (80, 70), 48, ACCENT, True)
        text(screen, "Complete missions to unlock better hardware.", (82, 130), 24, DIM)
        draw_panel(screen, (70, 170, 660, 800)); self.list.render(screen)
        p = self.parts[self.list.selected]
        draw_panel(screen, (760, 170, 1080, 800), p.name)
        y = 230
        text(screen, p.category.title() + (f"  |  role: {p.role}" if p.role else ""), (785, y), 24, DIM); y += 44
        y = paragraph(screen, p.description, (785, y), 1030, 26); y += 14
        rows = [("Dry mass", f"{p.mass:,.0f} kg"), ("Cost", f"${p.cost:.1f}M"), ("Size", f"{p.length} m x Ø{p.diameter} m")]
        if p.fuel: rows += [("Propellant", f"{p.fuel:,.0f} kg"), ("Full mass", f"{p.mass + p.fuel:,.0f} kg")]
        if p.category == "engine":
            rows += [("Thrust (vac)", f"{p.thrust_vac/1000:,.0f} kN"), ("Isp vac / sea level", f"{p.isp_vac:.0f} s / {p.isp_sl:.0f} s"),
                     ("Mass flow", f"{p.thrust_vac/(9.80665*p.isp_vac):.1f} kg/s")]
        for k, v in rows:
            text(screen, k, (785, y), 24, DIM); text(screen, v, (1150, y), 24, TEXT, True); y += 38
        ok = game.part_unlocked(p)
        text(screen, "Available" if ok else f"Locked - complete “{game.mission(p.unlock).name}”", (785, 900), 26, GOOD if ok else WARN, True)
        self.back.render(screen); self.reset.render(screen)
