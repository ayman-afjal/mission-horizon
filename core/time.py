"""Time-warp controller (levels shared by flight scene and scripts)."""
WARP_LEVELS = [1, 2, 4, 10, 50, 100, 1000, 10000, 100000]

class TimeWarp:
    def __init__(self): self.index = 0
    @property
    def factor(self): return WARP_LEVELS[self.index]
    def set_factor(self, f):
        self.index = min(range(len(WARP_LEVELS)), key=lambda i: abs(WARP_LEVELS[i] - f))
    def up(self, cap=100000):
        if self.index + 1 < len(WARP_LEVELS) and WARP_LEVELS[self.index + 1] <= cap: self.index += 1
    def down(self): self.index = max(0, self.index - 1)
    def clamp(self, cap):
        while self.index > 0 and WARP_LEVELS[self.index] > cap: self.index -= 1
    def reset(self): self.index = 0
