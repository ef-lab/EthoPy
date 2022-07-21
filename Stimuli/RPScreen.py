from core.Stimulus import *
import pygame
from pygame.locals import *


@stimulus.schema
class RPScreen(Stimulus, dj.Manual):
    definition = """
    # This class handles the presentation of Odors
    -> StimCondition
    ---
    reward_color            : tinyblob
    punish_color            : tinyblob
    ready_color             : tinyblob
    background_color        : tinyblob
    """
    cond_tables = ['RPScreen']
    default_key = {'reward_color'      : [255, 255, 255],
                    'punish_color'     : [0, 0, 0],
                    'ready_color'      : [64, 64, 64],
                    'background_color' : [32, 32, 32]
                    } 

    def setup(self):
        self.color = self.curr_cond['background_color']  # default background color

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
        self.unshow(self.curr_cond['ready_color'])

    def reward_stim(self):
        self.unshow(self.curr_cond['reward_color'])

    def stop(self):
        self.screen.fill(self.curr_cond['punish_color'])
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

