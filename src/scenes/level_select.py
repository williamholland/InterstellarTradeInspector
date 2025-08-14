import pygame
import sqlite3
import os
from .level import Level

class LevelSelect:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("arial", 28)
        self.status_font = pygame.font.SysFont("arial", 20, italic=True)
        self.levels = []

        db_path = os.path.join(os.path.dirname(__file__), "../../data/level_meta.sqlite")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, title, solved FROM Level ORDER BY id;")
        self.levels = cur.fetchall()
        conn.close()

    def run(self):
        while True:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    y = 100
                    for level in self.levels:
                        rect = pygame.Rect(100, y, 600, 40)
                        if rect.collidepoint(event.pos):
                            return Level(self.screen, level[0])
                        y += 50

            self.screen.fill((10, 10, 30))
            y = 100
            for level in self.levels:
                rect = pygame.Rect(100, y, 600, 40)

                # Highlight glow on hover
                if rect.collidepoint(mouse_pos):
                    colour = (80, 80, 150)
                else:
                    colour = (50, 50, 100)

                pygame.draw.rect(self.screen, colour, rect)

                # Level title
                txt = self.font.render(f"{level[0]} - {level[1]}", True, (255, 255, 255))
                self.screen.blit(txt, (110, y + 8))

                # Solved/Unsolved status
                if level[2]:  # solved is truthy
                    status_text = self.status_font.render("Solved", True, (0, 255, 0))
                else:
                    status_text = self.status_font.render("Unsolved", True, (255, 100, 100))
                self.screen.blit(status_text, (650, y + 10))

                y += 50

            pygame.display.flip()
