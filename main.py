# main.py
import sys
import pygame
from core.settings import WIDTH, HEIGHT, FPS, TITLE
from scenes.menu_scene import MenuScene

def main():
    pygame.init()
    # SCALED keeps the 1920x1080 coordinate system but fits any monitor
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.RESIZABLE)
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    active_scene = MenuScene()
    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.1)
        events = pygame.event.get()
        keys = pygame.key.get_pressed()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

        active_scene.process_input(events, keys)
        active_scene.update(dt)
        active_scene.render(screen)
        pygame.display.flip()

        if active_scene != active_scene.next_scene:
            active_scene = active_scene.next_scene

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
