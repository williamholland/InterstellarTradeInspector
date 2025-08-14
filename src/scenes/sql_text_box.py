import pygame

class SQLTextBox:
    """
    A multi-line text input box for entering SQL queries.
    Handles rendering, text input, backspace, and newlines.
    """

    def draw_multiline(self, text, color, x, y, max_width=800, font=None):
        if font is None:
            font = self.font

        paragraphs = text.split("\n")  # keep manual breaks
        offset = 0

        for paragraph in paragraphs:
            words = paragraph.split(" ")
            current_line = ""

            for word in words:
                test_line = current_line + ("" if current_line == "" else " ") + word
                if font.size(test_line)[0] <= max_width:
                    current_line = test_line
                else:
                    rendered = font.render(current_line, True, color)
                    self.screen.blit(rendered, (x, y + offset))
                    offset += rendered.get_height() + 2
                    current_line = word

            if current_line:  # render leftover words
                rendered = font.render(current_line, True, color)
                self.screen.blit(rendered, (x, y + offset))
                offset += rendered.get_height() + 2

            offset += font.get_height() // 2  # extra gap for manual newline


    def __init__(self, x, y, width, height, font=None, text_color=(200, 255, 200), bg_color=(30, 30, 30)):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font or pygame.font.SysFont("consolas", 20)
        self.text_color = text_color
        self.bg_color = bg_color
        self.text = ""

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.text += "\n"
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode

    def draw(self, screen, surface):
        self.screen = screen
        pygame.draw.rect(surface, self.bg_color, self.rect)
        self.draw_multiline(self.text, self.text_color, self.rect.x + 10, self.rect.y + 10, font=self.font)

    def get_text(self):
        return self.text

    def set_text(self, new_text):
        self.text = new_text
