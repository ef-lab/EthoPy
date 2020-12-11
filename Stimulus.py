import numpy as np
from utils.Timer import *
import pygame
from pygame.locals import *


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
        self.iter = []
        self.curr_cond = []
        self.rew_probe = []
        self.un_choices = []
        self.curr_difficulty = 1
        resp_cond = params['resp_cond'] if 'resp_cond' in params else 'probe'
        if np.all([resp_cond in cond for cond in conditions]):
            self.raw_choices = np.array([d[resp_cond] for d in conditions])
        if np.all(['difficulty' in cond for cond in conditions]):
            self.difficulties = [cond['difficulty'] for cond in self.conditions]
        self.timer = Timer()

    def get_condition_tables(self):
        """return condition tables"""
        pass

    def setup(self):
        """setup stimulation for presentation before experiment starts"""
        pass

    def prepare(self, conditions=False):
        """prepares stuff for presentation before trial starts"""
        pass

    def init(self, cond=False):
        """initialize stuff for each trial"""
        pass

    def ready_stim(self):
        """Stim Cue for ready"""
        pass

    def reward_stim(self):
        """Stim Cue for reward"""
        pass

    def punish_stim(self):
        """Stim Cue for punishment"""
        pass

    def present(self):
        """trial presentation method"""
        pass

    def stop(self):
        """stop trial"""
        pass

    def _anti_bias(self, choice_h):
        self.un_choices, choices_idx, self.choices = np.unique(self.raw_choices, axis=0,
                                                              return_index=True, return_inverse=True)
        choice_h_idx = [list(choices_idx[(self.un_choices == c).all(1)])[0] for c in choice_h]
        if len(choice_h) < self.params['bias_window']: h = np.mean(self.choices)
        else: h = np.array(choice_h_idx[-self.params['bias_window']:])
        mn = np.min(self.choices); mx = np.max(self.choices)
        return np.random.binomial(1, 1 - np.nanmean((h - mn) / (mx - mn))) * (mx - mn) + mn

    def _get_new_cond(self):
        """Get curr condition & create random block of all conditions
        Should be called within init_trial
        """
        if self.params['trial_selection'] == 'fixed':
            if len(self.conditions) == 0:
                self.curr_cond = []
            else:
                self.curr_cond = self.conditions.pop()
        elif self.params['trial_selection'] == 'block':
            if np.size(self.iter) == 0:
                self.iter = np.random.permutation(np.size(self.conditions))
            cond = self.conditions[self.iter[0]]
            self.iter = self.iter[1:]
            self.curr_cond = cond
        elif self.params['trial_selection'] == 'random':
            self.curr_cond = np.random.choice(self.conditions)
        elif self.params['trial_selection'] == 'bias':
            idx = [~np.isnan(ch).any() for ch in self.beh.choice_history]
            choice_h = np.asarray(self.beh.choice_history, dtype=object)
            anti_bias = self._anti_bias(choice_h[idx])
            selected_conditions = [i for (i, v) in zip(self.conditions, self.choices == anti_bias) if v]
            self.curr_cond = np.random.choice(selected_conditions)
        elif self.params['trial_selection'] == 'staircase':
            idx = [~np.isnan(ch).any() for ch in self.beh.choice_history]
            rew_h = np.asarray(self.beh.reward_history, dtype=object)
            choice_h = np.asarray(self.beh.choice_history, dtype=object)
            rew_h = rew_h[idx]
            anti_bias = self._anti_bias(choice_h[idx])
            if self.iter == 1 or np.size(self.iter) == 0:
                self.iter = self.params['staircase_window']
                perf = np.nanmean(np.greater(rew_h[-self.params['staircase_window']:], 0))
                if perf > self.params['stair_up'] and self.curr_difficulty < max(self.difficulties):
                    self.curr_difficulty += 1
                elif perf < self.params['stair_down'] and self.curr_difficulty > min(self.difficulties):
                    self.curr_difficulty -= 1
                self.logger.update_difficulty(self.curr_difficulty)
            else:
                if self.beh.choice_history[-1:]:
                    self.iter -= 1
            selected_conditions = [i for (i, v) in zip(self.conditions, np.logical_and(self.choices == anti_bias,
                                                       np.array(self.difficulties) == self.curr_difficulty)) if v]
            self.curr_cond = np.random.choice(selected_conditions)
        elif self.params['trial_selection'] == 'water_stairs':
            rew_h = [np.greater(rw, 0).any() for rw in self.beh.reward_history]
            if self.iter == 1 or np.size(self.iter) == 0:
                self.iter = self.params['staircase_window']
                perf = np.nanmean(np.greater(rew_h[-self.params['staircase_window']:], 0))
                if perf > self.params['stair_up'] and self.curr_difficulty < max(self.difficulties):
                    self.curr_difficulty += 1
                elif perf < self.params['stair_down'] and self.curr_difficulty > min(self.difficulties):
                    self.curr_difficulty -= 1
                self.logger.update_difficulty(self.curr_difficulty)
            else:
                self.iter -= 1
            selected_conditions = [i for (i, v) in zip(self.conditions,
                                                       np.array(self.difficulties) == self.curr_difficulty) if v]
            self.curr_cond = np.random.choice(selected_conditions)

