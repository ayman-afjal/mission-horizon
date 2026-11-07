import pygame
from core.settings import *

def draw_panel(screen, rect, title=None, alpha=235):
    rect = pygame.Rect(rect)
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(s, (*PANEL, alpha), s.get_rect(), border_radius=10)
    screen.blit(s, rect.topleft)
    pygame.draw.rect(screen, PANEL_EDGE, rect, 2, border_radius=10)
    if title:
        t = font(22, True).render(title.upper(), True, ACCENT)
        screen.blit(t, (rect.x + 14, rect.y + 8))
        pygame.draw.line(screen, PANEL_EDGE, (rect.x + 10, rect.y + 38), (rect.right - 10, rect.y + 38))

def fmt_dist(m):
    if m == float("inf"): return "--"
    a = abs(m)
    if a >= 1e8: return f"{m/1e6:,.0f} Mm"
    if a >= 1e6: return f"{m/1e6:.2f} Mm"
    if a >= 1e4: return f"{m/1e3:,.1f} km"
    if a >= 1e3: return f"{m/1e3:.2f} km"
    return f"{m:.0f} m"

def fmt_time(s):
    if s == float("inf"): return "--"
    s = int(s); d, s = divmod(s, 86400); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    if d: return f"{d}d {h:02d}:{m:02d}:{s:02d}"
    return f"{h:02d}:{m:02d}:{s:02d}"
