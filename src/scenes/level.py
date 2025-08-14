import pygame
import sqlite3
import os
from .text_scene import TextScene
from .sql_text_box import SQLTextBox  # new import

class Level(TextScene):
    def __init__(self, screen, level_id):
        self.screen = screen
        self.font = pygame.font.SysFont("arial", 22)

        self.level_id = level_id
        db_path = os.path.join(os.path.dirname(__file__), "../../data/level_meta.sqlite")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, title, pretext, solution_sql FROM Level WHERE id = ?", (level_id,))
        row = cur.fetchone()
        conn.close()

        self.meta = {
            "id": row[0],
            "title": row[1],
            "pretext": row[2],
            "solution_sql": row[3]
        }

        # SQL input box instance
        self.sql_box = SQLTextBox(100, 300, 800, 200)

        # Buttons
        self.button_rect = pygame.Rect(100, 600, 120, 40)
        self.back_rect = pygame.Rect(240, 600, 120, 40)
        self.result_text = ""

    def run(self):
        while True:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.button_rect.collidepoint(event.pos):
                        self.check_sql()
                    elif self.back_rect.collidepoint(event.pos):
                        from .level_select import LevelSelect
                        return LevelSelect(self.screen)
                else:
                    self.sql_box.handle_event(event)

            self.screen.fill((20, 20, 40))

            # Title & pretext
            self.screen.blit(
                self.font.render(f"{self.meta['id']}: {self.meta['title']}", True, (255, 255, 255)),
                (100, 20)
            )
            self.draw_multiline(self.meta["pretext"], (255, 255, 200), 100, 60)

            # SQL input box
            self.sql_box.draw(self.screen, self.screen)

            # --- Buttons with hover ---
            if self.button_rect.collidepoint(mouse_pos):
                pygame.draw.rect(self.screen, (0, 200, 0), self.button_rect)
            else:
                pygame.draw.rect(self.screen, (0, 150, 0), self.button_rect)
            self.screen.blit(
                self.font.render("TEST", True, (255, 255, 255)),
                (self.button_rect.x + 20, self.button_rect.y + 8)
            )

            if self.back_rect.collidepoint(mouse_pos):
                pygame.draw.rect(self.screen, (200, 0, 0), self.back_rect)
            else:
                pygame.draw.rect(self.screen, (150, 0, 0), self.back_rect)
            self.screen.blit(
                self.font.render("BACK", True, (255, 255, 255)),
                (self.back_rect.x + 20, self.back_rect.y + 8)
            )

            # Result area
            self.draw_multiline(self.result_text, (255, 200, 200), 100, 660)

            pygame.display.flip()

    def check_sql(self):
        base_path = os.path.dirname(__file__)
        example_db = os.path.join(base_path, f"../../data/level{self.level_id}_example.sqlite")
        conn = sqlite3.connect(example_db)
        cur = conn.cursor()
        try:
            cur.execute(self.sql_box.get_text().strip())
            player_result = cur.fetchall()

            solution_sql = self.meta["solution_sql"]
            cur.execute(solution_sql)
            expected_result = cur.fetchall()

            if player_result == expected_result:
                self.result_text = "✅ Correct!"
            else:
                self.result_text = f"❌ Incorrect.\nExpected: {expected_result}\nGot: {player_result}"
        except Exception as e:
            self.result_text = f"Error: {e}"
        finally:
            conn.close()
