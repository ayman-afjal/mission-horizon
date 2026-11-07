import math

class Vec2:
    __slots__ = ("x", "y")
    def __init__(self, x=0.0, y=0.0):
        self.x = x; self.y = y
    @staticmethod
    def from_angle(a, r=1.0): return Vec2(r * math.cos(a), r * math.sin(a))
    def __add__(s, o): return Vec2(s.x + o.x, s.y + o.y)
    def __sub__(s, o): return Vec2(s.x - o.x, s.y - o.y)
    def __mul__(s, k): return Vec2(s.x * k, s.y * k)
    __rmul__ = __mul__
    def __truediv__(s, k): return Vec2(s.x / k, s.y / k)
    def __neg__(s): return Vec2(-s.x, -s.y)
    def dot(s, o): return s.x * o.x + s.y * o.y
    def cross(s, o): return s.x * o.y - s.y * o.x
    def length(s): return math.hypot(s.x, s.y)
    def normalized(s):
        l = s.length()
        return Vec2(s.x / l, s.y / l) if l > 0 else Vec2(0, 0)
    def angle(s): return math.atan2(s.y, s.x)
    def rotated(s, a):
        c, sn = math.cos(a), math.sin(a)
        return Vec2(s.x * c - s.y * sn, s.x * sn + s.y * c)
    def tuple(s): return (s.x, s.y)
    def __repr__(s): return f"Vec2({s.x:.3f}, {s.y:.3f})"
