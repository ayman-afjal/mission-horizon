import pygame
from core.scene import SceneBase
from core.settings import *
from core.game import game
from scripting.parser import parse
from ui.components import Btn, ListBox, TextEditor, text, paragraph
from ui.panels import draw_panel

class MissionControlScene(SceneBase):
    def __init__(self):
        super().__init__()
        self.list = ListBox((60, 130, 480, 560), 76)
        for m in game.missions:
            ok = game.mission_available(m); s = game.completed.get(m.id, 0)
            sub = f"complete - {s}/3 stars" if s else ("Available" if ok else ("Coming soon" if not m.available else "Locked"))
            self.list.items.append(dict(label=f"{m.order}. {m.name}", sub=sub, enabled=ok, color=TEXT))
        self.list.selected = next(i for i, m in enumerate(game.missions) if m.id == game.selected)
        self.editor = TextEditor((580, 640, 1280, 340), 20)
        self.editor.set_text(game.script())
        self.select_btn = Btn("Select mission", 60, 710, 480, 60, 24, accent=True)
        self.reset_btn = Btn("Load template script", 60, 790, 480, 56, 22)
        self.back = Btn("Back", 60, 985, 200, 60, 24)
        self.errors = []
        self._check()

    def _cur(self): return game.missions[self.list.selected]

    def _check(self):
        _, errs = parse(self.editor.get_text())
        self.editor.errors = {l: m for l, m in errs}; self.errors = errs

    def _store(self):
        game.scripts[game.selected] = self.editor.get_text(); game.save()

    def process_input(self, events, keys):
        for e in events:
            if self.editor.handle(e):
                if self.editor.dirty: self._check(); self.editor.dirty = False
                continue
            i = self.list.handle(e)
            if i is not None:
                self._store(); self.list.selected = i
                m = self._cur()
                if game.mission_available(m): game.selected = m.id; self.editor.set_text(game.script()); self._check()
            if self.select_btn.is_clicked(e):
                m = self._cur()
                if game.mission_available(m): self._store(); game.selected = m.id; game.save()
            if self.reset_btn.is_clicked(e):
                self.editor.set_text(game.mission(game.selected).script_template); self._check(); self._store()
            if self.back.is_clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE and not self.editor.focus):
                self._store()
                from scenes.space_center import SpaceCenterScene; self.switch_to(SpaceCenterScene())
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE and self.editor.focus: self.editor.focus = False

    def update(self, dt=0.0):
        mp = pygame.mouse.get_pos()
        m = self._cur(); self.select_btn.enabled = game.mission_available(m)
        self.reset_btn.enabled = game.mission_available(m) and m.id == game.selected
        for b in (self.select_btn, self.reset_btn, self.back): b.update(mp)

    def render(self, screen):
        screen.fill(BG)
        text(screen, "MISSION CONTROL", (60, 50), 44, ACCENT, True)
        draw_panel(screen, (50, 120, 500, 580)); self.list.render(screen)
        m = self._cur()
        draw_panel(screen, (580, 120, 1280, 478), m.name)
        y = paragraph(screen, m.brief, (600, 170), 1240, 24, TEXT) + 8
        for o in m.objectives: text(screen, "> " + o.label, (600, y), 24, ACCENT, True); y += 34
        y += 6
        text(screen, f"Limits:  budget ${m.budget:.1f}M | {m.max_parts} parts | {m.max_mass/1000:.0f} t at liftoff"
             + (f" | requires: {', '.join(m.required_roles)}" if m.required_roles else ""), (600, y), 22, DIM); y += 34
        if m.unlocks:
            names = ", ".join(game.db.get(u).name for u in m.unlocks)
            y = paragraph(screen, "Unlocks on success: " + names, (600, y), 1240, 21, GOOD)
        if m.hint: paragraph(screen, "Hint: " + m.hint, (600, y + 6), 1240, 21, WARN)
        text(screen, "MISSION SCRIPT  (click to edit, saved automatically)", (580, 612), 20, DIM, True)
        self.editor.render(screen)
        for b in (self.select_btn, self.reset_btn, self.back): b.render(screen)
        if self.errors:
            l, msg = self.errors[0]
            text(screen, f"Script error - line {l}: {msg}", (580, 985), 22, BAD, True, maxw=1280)
        else:
            text(screen, "Script OK - it runs in flight (press P to toggle autopilot).  Reference: README / PLAN.", (580, 985), 22, GOOD)
        text(screen, "Selected: " + game.mission().name, (60, 880), 22, ACCENT)
