import pygame
import sqlite3
import os

class Level:
    def __init__(self, screen, level_id):
        self.screen = screen
        self.font = pygame.font.SysFont("arial", 22)
        self.input_font = pygame.font.SysFont("consolas", 20)
        self.sql_text = ""
        self.result_text = ""
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

        self.button_rect = pygame.Rect(100, 600, 120, 40)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.sql_text += "\n"
                    elif event.key == pygame.K_BACKSPACE:
                        self.sql_text = self.sql_text[:-1]
                    else:
                        self.sql_text += event.unicode
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.button_rect.collidepoint(event.pos):
                        self.check_sql()

            self.screen.fill((20, 20, 40))
            # Title & pretext
            self.screen.blit(self.font.render(f"{self.meta['id']}: {self.meta['title']}", True, (255, 255, 255)), (100, 20))
            self.draw_multiline(self.meta["pretext"], (255, 255, 200), 100, 60, 600)

            # SQL input box
            pygame.draw.rect(self.screen, (30, 30, 30), (100, 300, 800, 200))
            self.draw_multiline(self.sql_text, (200, 255, 200), 110, 310, 780, font=self.input_font)

            # Test button
            pygame.draw.rect(self.screen, (0, 150, 0), self.button_rect)
            self.screen.blit(self.font.render("TEST", True, (255, 255, 255)), (self.button_rect.x + 20, self.button_rect.y + 8))

            # Result area
            self.draw_multiline(self.result_text, (255, 200, 200), 100, 660, 800)

            pygame.display.flip()

    def draw_multiline(self, text, color, x, y, max_width=800, font=None):
        if font is None:
            font = self.font
        lines = text.split("\n")
        offset = 0
        for line in lines:
            rendered = font.render(line, True, color)
            self.screen.blit(rendered, (x, y + offset))
            offset += rendered.get_height() + 2

    def check_sql(self):
        base_path = os.path.dirname(__file__)
        example_db = os.path.join(base_path, f"../../data/level{self.level_id}_example.sqlite")
        conn = sqlite3.connect(example_db)
        cur = conn.cursor()
        try:
            cur.execute(self.sql_text.strip())
            player_result = cur.fetchall()

            # Get expected
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
