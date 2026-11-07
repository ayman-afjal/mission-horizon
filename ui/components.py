import pygame
from core.settings import *
from ui.buttons import Button

def text(screen, s, pos, size=22, color=TEXT, bold=False, mono=False, anchor="topleft", maxw=None, shadow=False):
    f = font(size, bold, mono)
    if shadow: text(screen, s, (pos[0] + 2, pos[1] + 2), size, (0, 0, 0), bold, mono, anchor, maxw)
    surf = f.render(str(s), True, color)
    if maxw and surf.get_width() > maxw:
        surf = pygame.transform.smoothscale(surf, (maxw, surf.get_height()))
    r = surf.get_rect(**{anchor: pos}); screen.blit(surf, r); return r

def wrap(s, size, maxw, mono=False):
    f = font(size, mono=mono); lines = []
    for para in str(s).split("\n"):
        cur = ""
        for w in para.split(" "):
            t = (cur + " " + w).strip()
            if f.size(t)[0] <= maxw: cur = t
            else: lines.append(cur); cur = w
        lines.append(cur)
    return lines

def paragraph(screen, s, pos, maxw, size=20, color=TEXT, spacing=4):
    y = pos[1]
    for ln in wrap(s, size, maxw):
        text(screen, ln, (pos[0], y), size, color); y += size + spacing
    return y

class Btn(Button):
    """Button with enabled flag, relabel and accent colours."""
    def __init__(self, label, x, y, w, h, size=24, accent=False):
        super().__init__(label, x, y, w, h, font(size, True),
                         normal_color=(90, 70, 20) if accent else (50, 50, 60),
                         hover_color=(140, 110, 30) if accent else (80, 80, 100))
        self.enabled = True
    def set_text(self, label):
        self.text = label
        self.text_surf = self.font.render(label, True, self.text_color)
        self.text_rect = self.text_surf.get_rect(center=self.rect.center)
    def update(self, mouse_pos):
        self.is_hovered = self.enabled and self.rect.collidepoint(mouse_pos)
    def is_clicked(self, event):
        return self.enabled and super().is_clicked(event)
    def render(self, screen):
        if self.enabled: super().render(screen); return
        pygame.draw.rect(screen, (34, 34, 40), self.rect, border_radius=8)
        pygame.draw.rect(screen, (70, 70, 80), self.rect, 2, border_radius=8)
        s = self.font.render(self.text, True, (110, 110, 120)); screen.blit(s, s.get_rect(center=self.rect.center))

class ListBox:
    """Scrollable selectable list. items: dicts with label, sub, color, enabled."""
    def __init__(self, rect, row_h=54):
        self.rect = pygame.Rect(rect); self.row_h = row_h
        self.items = []; self.selected = 0; self.scroll = 0
    def handle(self, event):
        """Returns index clicked (or None)."""
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            self.scroll = max(0, min(self.scroll - event.y, max(0, len(self.items) - self.rect.h // self.row_h)))
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            i = (event.pos[1] - self.rect.y) // self.row_h + self.scroll
            if 0 <= i < len(self.items): return i
        return None
    def render(self, screen):
        old = screen.get_clip(); screen.set_clip(self.rect)
        mouse = pygame.mouse.get_pos()
        n = self.rect.h // self.row_h + 1
        for k in range(n):
            i = self.scroll + k
            if i >= len(self.items): break
            it = self.items[i]; r = pygame.Rect(self.rect.x, self.rect.y + k * self.row_h, self.rect.w, self.row_h - 4)
            col = (70, 80, 120) if i == self.selected else ((46, 52, 70) if r.collidepoint(mouse) else (34, 38, 52))
            pygame.draw.rect(screen, col, r, border_radius=6)
            c = it.get("color", TEXT) if it.get("enabled", True) else (110, 110, 120)
            text(screen, it["label"], (r.x + 10, r.y + 4), 22, c, True, maxw=r.w - 20)
            if it.get("sub"): text(screen, it["sub"], (r.x + 10, r.y + 28), 17, DIM, maxw=r.w - 20)
        screen.set_clip(old)

class ProgressBar:
    @staticmethod
    def draw(screen, rect, frac, color=GOOD):
        rect = pygame.Rect(rect)
        pygame.draw.rect(screen, (40, 44, 58), rect, border_radius=4)
        w = int(rect.w * max(0.0, min(1.0, frac)))
        if w: pygame.draw.rect(screen, color, (rect.x, rect.y, w, rect.h), border_radius=4)
        pygame.draw.rect(screen, PANEL_EDGE, rect, 1, border_radius=4)

class TextEditor:
    """Minimal multi-line code editor with cursor, scrolling and error highlighting."""
    def __init__(self, rect, size=20):
        self.rect = pygame.Rect(rect); self.size = size
        self.lines = [""]; self.cx = 0; self.cy = 0; self.scroll = 0
        self.focus = False; self.errors = {}; self.active_line = None; self.dirty = False
    def set_text(self, s):
        self.lines = s.split("\n") or [""]; self.cx = self.cy = 0; self.scroll = 0
    def get_text(self): return "\n".join(self.lines)
    @property
    def lh(self): return self.size + 6
    @property
    def visible(self): return (self.rect.h - 12) // self.lh
    def _clamp(self):
        self.cy = max(0, min(self.cy, len(self.lines) - 1)); self.cx = max(0, min(self.cx, len(self.lines[self.cy])))
        if self.cy < self.scroll: self.scroll = self.cy
        if self.cy >= self.scroll + self.visible: self.scroll = self.cy - self.visible + 1
    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.focus = self.rect.collidepoint(event.pos)
            if self.focus:
                self.cy = (event.pos[1] - self.rect.y - 6) // self.lh + self.scroll
                self.cy = max(0, min(self.cy, len(self.lines) - 1))
                cw = font(self.size, mono=True).size("M")[0]
                self.cx = max(0, min(len(self.lines[self.cy]), (event.pos[0] - self.rect.x - 50 + cw // 2) // cw))
            return self.focus
        if not self.focus: return False
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            self.scroll = max(0, min(self.scroll - event.y * 2, max(0, len(self.lines) - self.visible))); return True
        if event.type == pygame.TEXTINPUT:
            t = "".join(c for c in event.text if c.isprintable())
            ln = self.lines[self.cy]; self.lines[self.cy] = ln[:self.cx] + t + ln[self.cx:]
            self.cx += len(t); self.dirty = True; return True
        if event.type == pygame.KEYDOWN:
            k = event.key; ln = self.lines[self.cy]
            if k == pygame.K_RETURN:
                self.lines[self.cy] = ln[:self.cx]; self.lines.insert(self.cy + 1, ln[self.cx:]); self.cy += 1; self.cx = 0; self.dirty = True
            elif k == pygame.K_BACKSPACE:
                if self.cx > 0: self.lines[self.cy] = ln[:self.cx - 1] + ln[self.cx:]; self.cx -= 1
                elif self.cy > 0:
                    prev = self.lines[self.cy - 1]; self.cx = len(prev); self.lines[self.cy - 1] = prev + ln; del self.lines[self.cy]; self.cy -= 1
                self.dirty = True
            elif k == pygame.K_DELETE:
                if self.cx < len(ln): self.lines[self.cy] = ln[:self.cx] + ln[self.cx + 1:]
                elif self.cy + 1 < len(self.lines): self.lines[self.cy] = ln + self.lines[self.cy + 1]; del self.lines[self.cy + 1]
                self.dirty = True
            elif k == pygame.K_LEFT: self.cx -= 1; (self.cy > 0 and self.cx < 0) and (setattr(self, "cy", self.cy - 1), setattr(self, "cx", len(self.lines[self.cy])))
            elif k == pygame.K_RIGHT:
                self.cx += 1
                if self.cx > len(ln) and self.cy + 1 < len(self.lines): self.cy += 1; self.cx = 0
            elif k == pygame.K_UP: self.cy -= 1
            elif k == pygame.K_DOWN: self.cy += 1
            elif k == pygame.K_HOME: self.cx = 0
            elif k == pygame.K_END: self.cx = len(ln)
            elif k == pygame.K_TAB: self.lines[self.cy] = ln[:self.cx] + "  " + ln[self.cx:]; self.cx += 2; self.dirty = True
            else: return False
            self._clamp(); return True
        return False
    def render(self, screen):
        pygame.draw.rect(screen, (16, 18, 26), self.rect, border_radius=6)
        pygame.draw.rect(screen, ACCENT if self.focus else PANEL_EDGE, self.rect, 2, border_radius=6)
        old = screen.get_clip(); screen.set_clip(self.rect.inflate(-4, -4))
        f = font(self.size, mono=True); cw = f.size("M")[0]
        for k in range(self.visible + 1):
            i = self.scroll + k
            if i >= len(self.lines): break
            y = self.rect.y + 6 + k * self.lh
            if i + 1 == self.active_line: pygame.draw.rect(screen, (50, 70, 40), (self.rect.x + 4, y - 1, self.rect.w - 8, self.lh))
            if i + 1 in self.errors: pygame.draw.rect(screen, (90, 30, 30), (self.rect.x + 4, y - 1, self.rect.w - 8, self.lh))
            text(screen, f"{i+1:3d}", (self.rect.x + 8, y), self.size, (90, 96, 120), mono=True)
            src = self.lines[i]; code, _, com = src.partition("#")
            x = self.rect.x + 50
            screen.blit(f.render(code, True, TEXT), (x, y))
            if _: screen.blit(f.render("#" + com, True, (110, 160, 110)), (x + len(code) * cw, y))
        if self.focus and (pygame.time.get_ticks() // 500) % 2 == 0:
            y = self.rect.y + 6 + (self.cy - self.scroll) * self.lh
            pygame.draw.rect(screen, ACCENT, (self.rect.x + 50 + self.cx * cw, y, 2, self.size + 2))
        screen.set_clip(old)
