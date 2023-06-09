from core.Stimulus import *
import pygame
from pygame.locals import *


class RPScreen(Stimulus):

    def setup(self):
        self.color = [i*256 for i in self.monitor['background_color']]  # default background color

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
        self.unshow([i*256 for i in self.monitor['ready_color']])

    def reward_stim(self):
        self.unshow([i*256 for i in self.monitor['reward_color']])

    def punish_stim(self):
        self.unshow([i*256 for i in self.monitor['punish_color']])

    def start_stim(self):
        self.unshow([i*256 for i in self.monitor['start_color']])

    def stop(self):
        self.unshow([i*256 for i in self.monitor['background_color']])
        self.log_stop()
        self.isrunning = False

    def unshow(self, color=False):
        """update background color"""
        if not color: color = self.color
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

