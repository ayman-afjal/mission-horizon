import pygame
from core.scene import SceneBase 
from ui.buttons import Button  # Import your button class

class MenuScene(SceneBase):
    def __init__(self):
        super().__init__()
        self.font = pygame.font.SysFont("Arial", 48)
        self.btn_font = pygame.font.SysFont("Arial", 28)

        # Create two navigation buttons centered horizontally on a 1920x1080 canvas
        screen_center_x = 1920 // 2
        
        self.space_center_btn = Button(
            text="Start Game", 
            x=screen_center_x - 150, 
            y=500, 
            width=300, 
            height=60, 
            font=self.btn_font
        )
        
        self.about_btn = Button(
            text="About", 
            x=screen_center_x - 150, 
            y=600, 
            width=300, 
            height=60, 
            font=self.btn_font
        )

    def process_input(self, events, keys):
        for event in events:
            # Check button click events
            if self.space_center_btn.is_clicked(event):
                from scenes.space_center import SpaceCenterScene
                self.switch_to(SpaceCenterScene())
                
            elif self.about_btn.is_clicked(event):
                from scenes.about import AboutScene
                self.switch_to(AboutScene())

    def update(self, dt=0.0):
        # Pass the current mouse cursor position to update hover animations
        mouse_pos = pygame.mouse.get_pos()
        self.space_center_btn.update(mouse_pos)
        self.about_btn.update(mouse_pos)

    def render(self, screen):
        screen.fill((20, 20, 25))
        
        # Draw main title text
        text = self.font.render("MISSION HORIZON", True, (255, 255, 255))
        screen.blit(text, (1920 // 2 - text.get_width() // 2, 350))
        
        # Render the interactive UI buttons
        self.space_center_btn.render(screen)
        self.about_btn.render(screen)
