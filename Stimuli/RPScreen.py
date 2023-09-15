from core.Stimulus import *
import pygame
from pygame.locals import *


class RPScreen(Stimulus):

    def setup(self):
        self.fill_colors.set({'background': (0, 0, 0),
                              'start': (32, 32, 32),
                              'ready': (64, 64, 64),
                              'reward': (128, 128, 128),
                              'punish': (0, 0, 0)})

        # setup pygame
        if not pygame.get_init():
            pygame.init()
        self.screen = pygame.display.set_mode((800, 480))
        self.fill()
        pygame.mouse.set_visible(0)
        pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.fill()

    def fill(self, color=False):
        """update background color"""
        if not color: color = self.fill_colors.background_color
        if color:
            self.screen.fill(color)
            self.flip()

    def flip(self):
        """ Main flip method"""
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()

    def exit(self):
        """Close stuff"""
        pygame.mouse.set_visible(1)
        pygame.display.quit()
        pygame.quit()

