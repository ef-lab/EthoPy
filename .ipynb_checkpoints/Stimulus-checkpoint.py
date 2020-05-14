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
