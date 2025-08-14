import pygame
import sys
from src.scenes.main_menu import MainMenu

#TODO redo with argparse (does it work on windows?)

pygame.init()
SCREEN = pygame.display.set_mode((1280, 720))
pygame.display.set_caption("Interstellar Trade Inspector")
CLOCK = pygame.time.Clock()

def main():
    current_scene = MainMenu(SCREEN)

    while True:
        next_scene = current_scene.run()
        if next_scene is None:
            pygame.quit()
            sys.exit()
        current_scene = next_scene

if __name__ == "__main__":
    main()
