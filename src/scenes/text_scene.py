import pygame
import sqlite3
import os

class TextScene(object):

    def draw_multiline(self, text, default_color, x, y, max_width=1100, font=None, bold_color=(255, 255, 255)):
        '''
            Render multi-line text with word wrapping, manual newline support, and inline bold styling.

            This function draws a block of text onto the screen, wrapping words to fit
            within a specified maximum width, while also respecting explicit newline
            characters ("\n"). Segments of text enclosed in asterisks (*) are rendered in
            bold with a specified highlight colour, allowing inline emphasis (e.g.,
            *table_name*). Bold mode can span multiple words and will toggle on or off
            whenever an asterisk is encountered.
        '''

        if font is None:
            font = self.font

        bold_font = pygame.font.SysFont("consolas", font.get_height(), bold=True)

        paragraphs = text.split("\n")
        offset = 0

        for paragraph in paragraphs:
            words = paragraph.split(" ")
            current_line_parts = []
            line_width = 0
            bold_mode = False

            for word in words:
                # Detect asterisks for bold toggling
                if word.startswith("*") and word.endswith("*") and len(word) > 1:
                    # Fully wrapped in asterisks
                    parts = [(word.strip("*"), bold_color, bold_font)]
                elif word.startswith("*"):
                    bold_mode = True
                    parts = [(word.lstrip("*"), bold_color, bold_font)]
                elif word.endswith("*"):
                    parts = [(word.rstrip("*"), bold_color, bold_font)]
                    bold_mode = False
                else:
                    parts = [(word, bold_color, bold_font)] if bold_mode else [(word, default_color, font)]

                for text_part, color, use_font in parts:
                    test_width = line_width + use_font.size(text_part + " ")[0]
                    if test_width > max_width and line_width > 0:
                        # Render current line before wrapping
                        x_offset = x
                        for t, c, fnt in current_line_parts:
                            rendered = fnt.render(t, True, c)
                            self.screen.blit(rendered, (x_offset, y + offset))
                            x_offset += rendered.get_width() + fnt.size(" ")[0]
                        offset += font.get_height() + 2
                        current_line_parts = []
                        line_width = 0

                    current_line_parts.append((text_part, color, use_font))
                    line_width += use_font.size(text_part + " ")[0]

            # Render last line of paragraph
            if current_line_parts:
                x_offset = x
                for t, c, fnt in current_line_parts:
                    rendered = fnt.render(t, True, c)
                    self.screen.blit(rendered, (x_offset, y + offset))
                    x_offset += rendered.get_width() + fnt.size(" ")[0]
                offset += font.get_height() + 2

            offset += font.get_height() // 2  # extra gap for manual newline
