import pygame

WIDTH, HEIGHT = 1920, 1080
FPS = 60
TITLE = "Mission Horizon"

BG = (14, 16, 24)
PANEL = (26, 30, 42)
PANEL_EDGE = (70, 78, 104)
TEXT = (230, 233, 240)
DIM = (140, 148, 168)
ACCENT = (255, 200, 60)
GOOD = (90, 220, 130)
BAD = (240, 90, 90)
WARN = (255, 170, 60)
BLUE = (90, 160, 255)

_fonts = {}
def font(size=24, bold=False, mono=False):
    key = (size, bold, mono)
    if key not in _fonts:
        if mono: _fonts[key] = pygame.font.SysFont("dejavusansmono,consolas,menlo,couriernew,monospace", size, bold=bold)
        else: _fonts[key] = pygame.font.SysFont("arial,dejavusans,helvetica", size, bold=bold)
    return _fonts[key]
