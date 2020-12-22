import numpy as np
from utils.Timer import *
from utils.Generator import make_hash


class Stimulus:
    """ This class handles the stimulus presentation
    use function overrides for each stimulus class
    """

    def __init__(self, logger, params, conditions, beh=False):
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
            self.choices = np.array([make_hash(d[resp_cond]) for d in conditions])
            self.un_choices, un_idx = np.unique(self.choices, axis=0, return_index=True)
        if np.all(['difficulty' in cond for cond in conditions]):
            self.difficulties = np.array([cond['difficulty'] for cond in self.conditions])
            if np.all([resp_cond in cond for cond in conditions]):
                self.un_difficulties = self.difficulties[un_idx]
        self.timer = Timer()

    def get_cond_tables(self):
        """return condition tables"""
        return []

    def setup(self):
        """setup stimulation for presentation before experiment starts"""
        pass

    def prepare(self, conditions=False):
        """prepares stuff for presentation before trial starts"""
        self._get_new_cond()

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

    def _anti_bias(self, choice_h, un_choices):
        choice_h = np.array([make_hash(c) for c in choice_h[-self.params['bias_window']:]])
        if len(choice_h) < self.params['bias_window']: choice_h = self.choices
        fixed_p = 1 - np.array([np.mean(choice_h == un) for un in un_choices])
        if sum(fixed_p) == 0:  fixed_p = np.ones(np.shape(fixed_p))
        return np.random.choice(un_choices, 1, p=fixed_p/sum(fixed_p))

    def _get_new_cond(self):
        """Get curr condition & create random block of all conditions
        Should be called within init_trial
        """
        if self.params['trial_selection'] == 'fixed':
            self.curr_cond = [] if len(self.conditions) == 0 else self.conditions.pop()
        elif self.params['trial_selection'] == 'block':
            if np.size(self.iter) == 0: self.iter = np.random.permutation(np.size(self.conditions))
            cond = self.conditions[self.iter[0]]
            self.iter = self.iter[1:]
            self.curr_cond = cond
        elif self.params['trial_selection'] == 'random':
            self.curr_cond = np.random.choice(self.conditions)
        elif self.params['trial_selection'] == 'bias':
            idx = [~np.isnan(ch).any() for ch in self.beh.choice_history]
            choice_h = np.asarray(self.beh.choice_history, dtype=object)
            anti_bias = self._anti_bias(choice_h[idx], self.un_choices)
            selected_conditions = [i for (i, v) in zip(self.conditions, self.choices == anti_bias) if v]
            self.curr_cond = np.random.choice(selected_conditions)
        elif self.params['trial_selection'] == 'staircase':
            idx = [~np.isnan(ch).any() for ch in self.beh.choice_history]
            rew_h = np.asarray(self.beh.reward_history, dtype=object); rew_h = rew_h[idx]
            choice_h = np.asarray(self.beh.choice_history, dtype=object)
            if self.iter == 1 or np.size(self.iter) == 0:
                self.iter = self.params['staircase_window']
                perf = np.nanmean(np.greater(rew_h[-self.params['staircase_window']:], 0))
                if perf > self.params['stair_up'] and self.curr_difficulty < max(self.difficulties):
                    self.curr_difficulty += 1
                elif perf < self.params['stair_down'] and self.curr_difficulty > min(self.difficulties):
                    self.curr_difficulty -= 1
                self.logger.update_setup_info('difficulty', self.curr_difficulty)
            elif self.beh.choice_history[-1:]: self.iter -= 1
            anti_bias = self._anti_bias(choice_h[idx], self.un_choices[self.un_difficulties == self.curr_difficulty])
            selected_conditions = [i for (i, v) in zip(self.conditions, np.logical_and(self.choices == anti_bias,
                                                       self.difficulties == self.curr_difficulty)) if v]
            self.curr_cond = np.random.choice(selected_conditions)

