from Stimulus import *


class Odors(Stimulus):
    """ This class handles the presentation of Odors"""

    def init(self):
        delivery_idx = self.curr_cond['delivery_idx']
        odor_idx = self.curr_cond['odor_idx']
        odor_dur = self.curr_cond['duration']
        odor_dutycycle = self.curr_cond['dutycycle']
        self.beh.give_odor(delivery_idx, odor_idx, odor_dur, odor_dutycycle)
        self.isrunning = True
        self.timer.start()
        self.logger.log_stim()

    def stop(self):
        self.isrunning = False
