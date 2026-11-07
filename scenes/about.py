# scenes/about.py
import pygame
from core.scene import SceneBase
from ui.buttons import Button

class AboutScene(SceneBase):
    def __init__(self):
        super().__init__()
        # Initialize fonts
        self.title_font = pygame.font.SysFont("Arial", 64)
        self.credits_font = pygame.font.SysFont("Arial", 36)
        self.btn_font = pygame.font.SysFont("Arial", 28)

        # Content list of developers and roles
        self.credits_list = [
            "SAYED HUZAIFA MUMIT",
            "ALMAN SIKDER",
            "AYMAN AFJAL",
            "AADRITO MAITRA",
            "PRITOM NONDI",
            "MD. TAHMID BIN SHADH"
        ]

        # Interactive back button positioned near the bottom center
        screen_center_x = 1920 // 2
        self.back_btn = Button(
            text="Back to Menu",
            x=screen_center_x - 150,
            y=850,
            width=300,
            height=60,
            font=self.btn_font
        )

    def process_input(self, events, keys):
        for event in events:
            # Route back via mouse click
            if self.back_btn.is_clicked(event):
                from scenes.menu_scene import MenuScene
                self.switch_to(MenuScene())
            
            # Or route back smoothly via Escape key press
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                from scenes.menu_scene import MenuScene
                self.switch_to(MenuScene())

    def update(self, dt=0.0):
        # Update button hover physics
        mouse_pos = pygame.mouse.get_pos()
        self.back_btn.update(mouse_pos)

    def render(self, screen):
        # Clean cosmic slate-black background look
        screen.fill((15, 15, 20))

        # 1. Render Title Header
        title_surf = self.title_font.render("MISSION HORIZON - CREDITS", True, (255, 215, 0)) # Gold text
        title_x = 1920 // 2 - title_surf.get_width() // 2
        screen.blit(title_surf, (title_x, 200))

        # 2. Render Team List Line by Line
        start_y = 380
        line_spacing = 70
        for i, entry in enumerate(self.credits_list):
            text_surf = self.credits_font.render(entry, True, (220, 220, 220))
            text_x = 1920 // 2 - text_surf.get_width() // 2
            screen.blit(text_surf, (text_x, start_y + (i * line_spacing)))

        # 3. Render Button Graphic Layer
        self.back_btn.render(screen)
