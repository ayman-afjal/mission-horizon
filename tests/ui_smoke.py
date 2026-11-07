"""Headless UI smoke test: walks through every scene with synthetic input and saves screenshots to /tmp/shots."""
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["MISSION_HORIZON_SAVE"] = "/tmp/mh_smoke_save.json"
if os.path.exists("/tmp/mh_smoke_save.json"): os.remove("/tmp/mh_smoke_save.json")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame
pygame.init(); screen = pygame.display.set_mode((1920, 1080))
os.makedirs("/tmp/shots", exist_ok=True)
from core.game import game
from scenes.menu_scene import MenuScene

class Keys:
    def __getitem__(self, k): return False
KEYS = Keys()
def shot(scene, name, frames=2):
    for _ in range(frames): scene.update(1 / 60); scene.render(screen)
    pygame.image.save(screen, f"/tmp/shots/{name}.png")
def click(scene, btn):
    btn.update(btn.rect.center); scene.process_input([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=btn.rect.center)], KEYS)
def key(scene, k, text=""):
    ev = [pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=text)]
    if text: ev.append(pygame.event.Event(pygame.TEXTINPUT, text=text))
    scene.process_input(ev, KEYS)

s = MenuScene(); shot(s, "01_menu")
click(s, s.space_center_btn); s.update(0); s = s.next_scene
assert s.__class__.__name__ == "SpaceCenterScene"; shot(s, "02_space_center")
click(s, s.buttons["mission"]); s = s.next_scene; assert s.__class__.__name__ == "MissionControlScene"
# type into the script editor: click inside it, add a bad line
s.process_input([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(900, 800))], KEYS)
key(s, pygame.K_END); key(s, pygame.K_RETURN)
for ch in "foo 3": key(s, 0, ch)
s.update(0); assert s.errors, "editor should flag the bad line"
shot(s, "03_mission_control")
for _ in range(6): key(s, pygame.K_BACKSPACE)
s.update(0); assert not s.errors, s.errors
s.process_input([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="")], KEYS)  # unfocus
s.process_input([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="")], KEYS)
s = s.next_scene; assert s.__class__.__name__ == "SpaceCenterScene"
click(s, s.buttons["research"]); r = s.next_scene; shot(r, "04_research")
r.process_input([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="")], KEYS); s = r.next_scene
click(s, s.buttons["tracking"]); t = s.next_scene; shot(t, "05_tracking")
t.process_input([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="")], KEYS); s = t.next_scene
# VAB interaction: clear, add parts by clicking the list, remove
click(s, s.buttons["vab"]); v = s.next_scene
click(v, v.b_clear); assert v.design == []; v.update(0)
v.cat = "pod"; v._fill(); v.process_input([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(100, 140))], KEYS)
v.cat = "tank"; v._fill(); v.process_input([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(100, 140))], KEYS)
v.cat = "engine"; v._fill()
v.process_input([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(100, 140))], KEYS)   # locked Lander Engine: must be refused
assert v.design == ["guidance_unit", "tank_s"], v.design
v.process_input([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(100, 202))], KEYS)   # Ember
assert v.design == ["guidance_unit", "tank_s", "engine_ember"], v.design
shot(v, "06_vab_small")
# Launch: manual flight for a few seconds
click(v, v.b_launch); f = v.next_scene; assert f.__class__.__name__ == "FlightScene"
shot(f, "07_pad")
key(f, pygame.K_z)
for _ in range(60 * 6): f.update(1 / 60)
shot(f, "08_ascent")
f.process_input([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="")], KEYS); shot(f, "09_pause")
print("UI smoke OK; max alt", round(f.sim.max_alt))
