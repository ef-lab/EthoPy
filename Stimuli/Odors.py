from Stimulus import *


class Odors(Stimulus):
    """ This class handles the presentation of Odors"""

    def prepare(self, conditions):
        self.clock = pygame.time.Clock()
        self.stim_conditions = dict()
        for cond in conditions:
            params = (OdorCond() & dict(cond_idx=cond) & self.logger.session_key).fetch1()
            self.stim_conditions[cond] = params

    def init_stim(self, cond):
        delivery_idx = self.stim_conditions[cond]['delivery_idx']
        odor_idx = self.stim_conditions[cond]['odor_idx']
        odor_dur = self.stim_conditions[cond]['duration']
        odor_dutycycle = self.stim_conditions[cond]['dutycycle']
        self.beh.give_odor(delivery_idx, odor_idx, odor_dur, odor_dutycycle)
        self.isrunning = True
        self.logger.start_trial(cond)  # log start trial
        return cond

    def stop_stim(self):
        self.isrunning = False
        self.logger.log_trial(self.flip_count)  # log trial
