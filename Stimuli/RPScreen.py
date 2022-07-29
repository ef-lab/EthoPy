from core.Stimulus import *
import pygame
from pygame.locals import *


class RPScreen(Stimulus):

    def setup(self):
        self.color = [32, 32, 32]  # default background color

        # setup pygame
        if not pygame.get_init():
            pygame.init()
        self.screen = pygame.display.set_mode((800, 480))
        self.unshow()
        pygame.mouse.set_visible(0)
        pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.screen.fill(self.color)
        self.flip()
        
    def ready_stim(self):
        self.unshow([64, 64, 64])

    def reward_stim(self):
        self.unshow([128, 128, 128])

    def start_stim(self):
        self.unshow([32,32,32])

    def stop(self):
        self.screen.fill([0, 0, 0])
        self.flip()
        self.log_stop()
        self.isrunning = False

    def unshow(self, color=False):
        """update background color"""
        if not color:
            color = self.color
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

