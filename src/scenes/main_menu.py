import pygame
import os
from .level_select import LevelSelect

class MainMenu:
    def __init__(self, screen):
        self.screen = screen
        assets_dir = os.path.join(os.path.dirname(__file__), "../../assets")
        self.bg = pygame.image.load(os.path.join(assets_dir, "main_menu.png")).convert()
        self.bg = pygame.transform.scale(self.bg, self.screen.get_size())

        self.font = pygame.font.SysFont("arial", 40)
        self.button_rect = pygame.Rect(510, 520, 245, 60)

        # Pre-make a semi-transparent white surface for hover
        self.hover_surface = pygame.Surface(self.button_rect.size, pygame.SRCALPHA)
        self.hover_surface.fill((255, 255, 255, 100))  # RGBA, alpha=100 ~ fairly transparent

    def run(self):
        while True:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.button_rect.collidepoint(event.pos):
                        return LevelSelect(self.screen)

            self.screen.blit(self.bg, (0, 0))

            # Draw transparent hover effect if mouse is over button
            if self.button_rect.collidepoint(mouse_pos):
                self.screen.blit(self.hover_surface, self.button_rect.topleft)

            pygame.display.flip()
