import pygame
from core.scene import SceneBase
from core.settings import *
from core.game import game
from spacecraft.spacecraft import Spacecraft
from ui.components import Btn, ListBox, text, paragraph
from ui.panels import draw_panel, fmt_dist

CATS = [("pod", "Pods"), ("payload", "Payload"), ("tank", "Tanks"), ("engine", "Engines"), ("decoupler", "Stagers")]
COLORS = {"pod": (205, 205, 215), "payload": (110, 190, 230), "tank": (225, 175, 70),
          "engine": (170, 100, 70), "decoupler": (130, 130, 150)}

def part_sub(p):
    s = f"{p.mass:,.0f} kg | ${p.cost:.1f}M"
    if p.fuel: s += f" | fuel {p.fuel:,.0f} kg"
    if p.category == "engine": s += f" | {p.thrust_vac/1000:,.0f} kN | Isp {p.isp_vac:.0f}"
    return s

class VABScene(SceneBase):
    def __init__(self):
        super().__init__()
        self.mission = game.mission()
        self.design = game.design(self.mission.id)
        self.sel = len(self.design) - 1
        self.cat = "tank"
        self.cat_btns = [Btn(lab, 50 + i * 104, 60, 100, 44, 18) for i, (_, lab) in enumerate(CATS)]
        self.list = ListBox((50, 120, 520, 860), 62)
        self._fill()
        self.b_remove = Btn("Remove", 600, 985, 140, 50, 20)
        self.b_up = Btn("Move ^", 750, 985, 130, 50, 20)
        self.b_down = Btn("Move v", 890, 985, 130, 50, 20)
        self.b_clear = Btn("Clear", 1030, 985, 120, 50, 20)
        self.b_tmpl = Btn("Template", 1160, 985, 140, 50, 20)
        self.b_back = Btn("Back", 1340, 985, 230, 60, 24)
        self.b_launch = Btn("Launch >", 1600, 985, 270, 60, 26, accent=True)
        self.rects = []
        self.flash = ""

    def _fill(self):
        self.parts = [p for p in game.db.by_category(self.cat)]
        self.parts.sort(key=lambda p: p.mass)
        self.list.items = []; self.list.scroll = 0
        for p in self.parts:
            ok = game.part_unlocked(p)
            sub = part_sub(p) if ok else f"Locked - complete {game.mission(p.unlock).name}"
            self.list.items.append(dict(label=p.name, sub=sub, enabled=ok, color=TEXT if ok else DIM))

    def _save(self): game.designs[self.mission.id] = self.design; game.save()

    def process_input(self, events, keys):
        for e in events:
            for (cid, _), b in zip(CATS, self.cat_btns):
                if b.is_clicked(e): self.cat = cid; self._fill()
            i = self.list.handle(e)
            if i is not None:
                p = self.parts[i]
                if game.part_unlocked(p):
                    pos = min(self.sel + 1, len(self.design)); self.design.insert(pos, p.id); self.sel = pos; self._save()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for idx, r in enumerate(self.rects):
                    if r.collidepoint(e.pos): self.sel = idx
            if self.b_remove.is_clicked(e) and self.design:
                self.design.pop(self.sel); self.sel = min(self.sel, len(self.design) - 1); self._save()
            if self.b_up.is_clicked(e) and self.sel > 0:
                d = self.design; d[self.sel - 1], d[self.sel] = d[self.sel], d[self.sel - 1]; self.sel -= 1; self._save()
            if self.b_down.is_clicked(e) and self.sel < len(self.design) - 1:
                d = self.design; d[self.sel + 1], d[self.sel] = d[self.sel], d[self.sel + 1]; self.sel += 1; self._save()
            if self.b_clear.is_clicked(e): self.design.clear(); self.sel = -1; self._save()
            if self.b_tmpl.is_clicked(e):
                self.design[:] = list(self.mission.template); self.sel = len(self.design) - 1; self._save()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_DELETE and self.design:
                self.design.pop(self.sel); self.sel = min(self.sel, len(self.design) - 1); self._save()
            if self.b_back.is_clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                from scenes.space_center import SpaceCenterScene; self.switch_to(SpaceCenterScene())
            if self.b_launch.is_clicked(e):
                from scenes.space_center import launch_check
                ok, msgs = launch_check()
                if ok:
                    from scenes.flight import FlightScene; self.switch_to(FlightScene())
                else: self.flash = msgs[0]

    def update(self, dt=0.0):
        mp = pygame.mouse.get_pos()
        for b in self.cat_btns + [self.b_remove, self.b_up, self.b_down, self.b_clear, self.b_tmpl, self.b_back, self.b_launch]: b.update(mp)
        has = bool(self.design)
        self.b_remove.enabled = has; self.b_up.enabled = has and self.sel > 0
        self.b_down.enabled = has and self.sel < len(self.design) - 1; self.b_clear.enabled = has
        self.sc = Spacecraft(self.design) if self.design else None
        self.errs, self.warns = self.sc.validate(self.mission) if self.sc else (["Craft is empty."], [])
        self.b_launch.enabled = not self.errs

    # -------------------------------------------------------------- drawing
    def _draw_rocket(self, screen):
        draw_panel(screen, (590, 40, 700, 930), "Assembly  (top v bottom)")
        self.rects = []
        if not self.design: 
            text(screen, "Click parts on the left to build.", (940, 500), 24, DIM, anchor="center"); return
        parts = [game.db.get(i) for i in self.design]
        scale = 26.0
        for _ in range(3):
            tot = sum(max(p.length * scale, 20) for p in parts)
            if tot > 840: scale *= 840 / tot
        maxw = 360
        y = 70 + 8 + (840 - sum(max(p.length * scale, 20) for p in parts)) / 2 + 30
        cx = 940
        stage_no = 0
        # stages: count decouplers
        n_dec = sum(1 for p in parts if p.category == "decoupler")
        stage = 0
        for idx, p in enumerate(parts):
            h = max(p.length * scale, 20); w = min(maxw, max(30, p.diameter * scale * 1.6))
            r = pygame.Rect(cx - w / 2, y, w, h); self.rects.append(r)
            if p.category == "decoupler" and idx > 0:
                stage += 1
                pygame.draw.line(screen, BAD, (600, y), (1280, y), 1)
            col = COLORS[p.category]
            if p.category == "engine":
                pts = [(r.left + w * 0.15, r.top), (r.right - w * 0.15, r.top), (r.right, r.bottom), (r.left, r.bottom)]
                pygame.draw.polygon(screen, col, pts); pygame.draw.polygon(screen, (230, 200, 160), pts, 2)
            elif p.category == "pod":
                pygame.draw.rect(screen, col, r, border_top_left_radius=int(w / 2.5), border_top_right_radius=int(w / 2.5))
            else: pygame.draw.rect(screen, col, r, border_radius=3)
            if p.category == "tank": pygame.draw.rect(screen, (190, 140, 50), (r.x, r.centery - 2, r.w, 4))
            if idx == self.sel: pygame.draw.rect(screen, ACCENT, r.inflate(6, 6), 3, border_radius=4)
            if h >= 22: text(screen, p.name, r.center, 16, (20, 20, 25), True, anchor="center", maxw=int(w) - 6)
            elif idx == self.sel: text(screen, p.name, (r.right + 14, r.y - 4), 16, ACCENT)
            y += h
        # stage labels
        y = 70 + 8 + (840 - sum(max(p.length * scale, 20) for p in parts)) / 2 + 30
        # label per segment: place at segment start
        seg = 0; labels = []
        for idx, p in enumerate(parts):
            if idx == 0 or p.category == "decoupler": labels.append((self.rects[idx].y, seg)); seg += 1
        for ly, s in labels:
            sn = n_dec - s + 1 if s > 0 else 0
            lab = "PAYLOAD" if s == 0 else f"STAGE {sn}" + ("  (liftoff)" if s == n_dec else "")
            text(screen, lab, (612, ly + 4), 16, DIM, True)

    def _draw_stats(self, screen):
        draw_panel(screen, (1310, 40, 570, 930), "Flight data")
        m = self.mission; x = 1330; y = 92
        text(screen, m.name, (x, y), 28, TEXT, True); y += 40
        sc = self.sc
        if not sc: text(screen, "Craft is empty.", (x, y), 24, BAD); return
        def row(k, v, ok=True):
            nonlocal y
            text(screen, k, (x, y), 22, DIM); text(screen, v, (x + 540, y), 22, TEXT if ok else BAD, True, anchor="topright"); y += 30
        row("Cost", f"${sc.total_cost:.1f}M / ${m.budget:.1f}M", sc.total_cost <= m.budget)
        row("Parts", f"{len(sc.parts)} / {m.max_parts}", len(sc.parts) <= m.max_parts)
        row("Liftoff mass", f"{sc.mass/1000:,.1f} t / {m.max_mass/1000:,.0f} t", sc.mass <= m.max_mass)
        row("Height", f"{sc.height():.1f} m")
        row("Total Δv (vac)", f"{sc.total_dv_vac():,.0f} m/s")
        y += 8; pygame.draw.line(screen, PANEL_EDGE, (x, y), (x + 540, y)); y += 10
        text(screen, "STAGES (firing order)", (x, y), 20, ACCENT, True); y += 30
        text(screen, "stage    Δv vac    Δv SL      TWR*   mass", (x, y), 18, DIM, mono=True); y += 26
        rep = sc.stage_report(); n = len(sc.stages)
        for r in rep:
            if not r["has_engine"] and r["index"] == 0: continue
            sn = n - r["index"]
            col = TEXT if r["has_engine"] else BAD
            low = r["twr_sl"] < 1.0 and r["index"] == n - 1
            text(screen, f"{sn:>3}   {r['dv_vac']:>8,.0f}  {r['dv_sl']:>8,.0f}  {(r['twr_sl'] if r['index'] == n - 1 else r['twr_vac']):>8.2f}  {r['m0']/1000:>6.1f}t",
                 (x, y), 18, BAD if low else col, mono=True); y += 24
        text(screen, "*TWR: stage 1 at sea level, others in vacuum", (x, y), 16, DIM); y += 20
        y += 8
        text(screen, "MISSION REQUIREMENTS", (x, y), 20, ACCENT, True); y += 28
        for role in m.required_roles:
            ok = sc.has_role(role); text(screen, ("[OK] " if ok else "[X] ") + f"needs a '{role}' part", (x, y), 20, GOOD if ok else BAD); y += 26
        for o in m.objectives: text(screen, "> " + o.label, (x, y), 20, TEXT, maxw=540); y += 26
        y += 10
        msgs = [(e, BAD) for e in self.errs] + [(w, WARN) for w in self.warns]
        if not msgs: text(screen, "[OK] Ready to launch", (x, y), 24, GOOD, True)
        for t, c in msgs[:6]:
            y = paragraph(screen, ("[X] " if c == BAD else "! ") + t, (x, y), 540, 19, c, 2) + 2
        if self.flash and self.errs: pass

    def render(self, screen):
        screen.fill(BG)
        draw_panel(screen, (40, 40, 540, 950))
        for (cid, _), b in zip(CATS, self.cat_btns):
            if cid == self.cat: b.normal_color = (110, 90, 30); b.hover_color = (140, 110, 30)
            else: b.normal_color = (50, 50, 60); b.hover_color = (80, 80, 100)
            b.render(screen)
        self.list.render(screen)
        self._draw_rocket(screen); self._draw_stats(screen)
        for b in (self.b_remove, self.b_up, self.b_down, self.b_clear, self.b_tmpl, self.b_back, self.b_launch): b.render(screen)
