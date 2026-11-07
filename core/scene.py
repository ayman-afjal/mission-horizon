import pygame

class SceneBase:
    def __init__(self):
        self.next_scene = self

    def process_input(self, events, keys):
        pass

    def update(self, dt=0.0):
        pass

    def render(self, screen):
        pass

    def switch_to(self, next_scene):
        self.next_scene = next_scene
