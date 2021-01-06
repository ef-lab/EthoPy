from Stimuli.Movies import *


class SmellyMovies(RPMovies):
    """ This class handles the presentation of Visual (movies) and Olfactory (odors) stimuli"""

    def get_cond_tables(self):
        return ['MovieCond', 'OdorCond']

    def init(self):
        delivery_port = self.curr_cond['delivery_port']
        odor_id = self.curr_cond['odor_id']
        odor_dur = self.curr_cond['odor_duration']
        odor_dutycycle = self.curr_cond['dutycycle']
        super().init()
        self.beh.give_odor(delivery_port, odor_id, odor_dur, odor_dutycycle)
        self.timer.start()
