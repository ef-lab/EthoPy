import pygame
from pygame.locals import *
import numpy as np
from utils.Timer import *


class Stimulus:
    """ This class handles the stimulus presentation
    use function overrides for each stimulus class
    """

    def __init__(self, logger, params, conditions, beh=False):
        # initilize parameters
        self.params = params
        self.logger = logger
        self.conditions = conditions
        self.beh = beh
        self.isrunning = False
        self.flip_count = 0
        self.indexes = []
        self.curr_cond = []
        self.rew_probe = []
        self.probes = []
        self.timer = Timer()

    def setup(self):
        # setup parameters
        self.path = 'stimuli/'     # default path to copy local stimuli
        self.size = (800, 480)     # window size
        self.color = [127, 127, 127]  # default background color
        self.loc = (0, 0)          # default starting location of stimulus surface
        self.fps = 30              # default presentation framerate
        self.phd_size = (50, 50)    # default photodiode signal size in pixels

        # setup pygame
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.unshow()
        pygame.mouse.set_visible(0)
        pygame.display.toggle_fullscreen()

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

    def unshow(self, color=False):
        """update background color"""
        if not color:
            color = self.color
        self.screen.fill(color)
        self.flip()

    def encode_photodiode(self):
        """Encodes the flip number n in the flip amplitude.
        Every 32 sequential flips encode 32 21-bit flip numbers.
        Thus each n is a 21-bit flip number:
        FFFFFFFFFFFFFFFFCCCCP
        P = parity, only P=1 encode bits
        C = the position within F
        F = the current block of 32 flips
        """
        n = self.flip_count + 1
        amp = 127 * (n & 1) * (2 - (n & (1 << (((np.int64(np.floor(n / 2)) & 15) + 6) - 1)) != 0))
        surf = pygame.Surface(self.phd_size)
        surf.fill((amp, amp, amp))
        self.screen.blit(surf, (0, 0))

    def flip(self):
        """ Main flip method"""
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()

        self.flip_count += 1

    def close(self):
        """Close stuff"""
        pygame.mouse.set_visible(1)
        pygame.display.quit()
        pygame.quit()


    def get_new_cond(self):
        """Get curr condition & create random block of all conditions
        Should be called within init_trial
        """
        if self.params['randomization'] == 'block':
            if np.size(self.indexes) == 0:
                self.indexes = np.random.permutation(np.size(self.conditions))
            cond = self.conditions[self.indexes[0]]
            self.indexes = self.indexes[1:]
            self.curr_cond = cond
        elif self.params['randomization'] == 'random':
            self.curr_cond = np.random.choice(self.conditions)
        elif self.params['randomization'] == 'bias':
            if len(self.beh.probe_bias) == 0 or np.all(np.isnan(self.beh.probe_bias)):
                self.beh.probe_bias = np.random.choice(self.probes, 5)
                self.curr_cond = np.random.choice(self.conditions)
            else:
                mn = np.min(self.probes)
                mx = np.max(self.probes)
                bias_probe = np.random.binomial(1, 1 - np.nanmean((self.beh.probe_bias - mn)/(mx-mn)))*(mx-mn) + mn
                biased_conditions = [i for (i, v) in zip(self.conditions, self.probes == bias_probe) if v]
                self.curr_cond = np.random.choice(biased_conditions)







