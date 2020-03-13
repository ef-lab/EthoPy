import pygame
from pygame.locals import *
import numpy as np
from utils.Timer import *


class Stimulus:
    """ This class handles the stimulus presentation
    use function overrides for each stimulus class
    """

    def setup(self):
        """setup stimulation"""
        pass

    def prepare(self, conditions=False):
        """prepares stuff for presentation before experiment starts"""
        pass

    def init(self, cond=False):
        """initialize stuff for each trial"""
        pass

    def present(self):
        """trial presentation method"""
        pass

    def stop(self):
        """stop trial"""
        pass
