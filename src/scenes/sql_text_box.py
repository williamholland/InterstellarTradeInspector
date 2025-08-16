import pygame
import time

class SQLTextBox:
    """
    A multi-line text input box for entering SQL queries.
    Handles rendering, text input, backspace, newlines, and a blinking caret.
    """

    CARET_BLINK_INTERVAL = 500  # ms

    def draw_multiline(self, text, color, x, y, max_width=800, font=None):
        if font is None:
            font = self.font

        paragraphs = text.split("\n")  # keep manual breaks
        offset = 0
        caret_pos = None  # store caret position

        # We'll build lines fully so we can know where caret goes
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

            if current_line:
                rendered = font.render(current_line, True, color)
                self.screen.blit(rendered, (x, y + offset))
                offset += rendered.get_height() + 2

            offset += font.get_height() // 2  # extra gap for manual newline

        return offset  # total drawn height, though not used yet

    def __init__(self, x, y, width, height, font=None,
                 text_color=(200, 255, 200), bg_color=(30, 30, 30)):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font or pygame.font.SysFont("consolas", 20)
        self.text_color = text_color
        self.bg_color = bg_color
        self.text = ""
        self.caret_visible = True
        self.last_blink = pygame.time.get_ticks()

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

        # Draw the text
        paragraphs = self.text.split("\n")
        x, y = self.rect.x + 10, self.rect.y + 10
        caret_x, caret_y = x, y
        line_height = self.font.get_height() + 2

        for paragraph in paragraphs:
            words = paragraph.split(" ")
            current_line = ""
            for word in words:
                test_line = current_line + ("" if current_line == "" else " ") + word
                if self.font.size(test_line)[0] <= (self.rect.width - 20):
                    current_line = test_line
                else:
                    surface.blit(self.font.render(current_line, True, self.text_color), (x, y))
                    y += line_height
                    current_line = word
            surface.blit(self.font.render(current_line, True, self.text_color), (x, y))
            # Update caret position to end of last rendered line
            caret_x = x + self.font.size(current_line)[0]
            caret_y = y
            y += line_height

        # Blinking caret logic
        now = pygame.time.get_ticks()
        if now - self.last_blink >= self.CARET_BLINK_INTERVAL:
            self.caret_visible = not self.caret_visible
            self.last_blink = now

        if self.caret_visible:
            caret_height = self.font.get_height()
            pygame.draw.line(surface, self.text_color,
                             (caret_x, caret_y),
                             (caret_x, caret_y + caret_height), 2)

    def get_text(self):
        return self.text

    def set_text(self, new_text):
        self.text = new_text
