from core.Stimulus import *

@stimulus.schema
class Opto(Stimulus, dj.Manual):
    definition = """
    # This class handles the presentation of Opto pulses for optogenetic activity control
    -> StimCondition
    ---
    duration             : int                     # duration (ms)
    dutycycle            : int                     #  dutycycle
    """

    cond_tables = ['Opto']
    required_fields = ['duration']
    default_key = {'dutycycle': 50}

    def start(self):
        self.exp.interface.opto_stim(self.curr_cond['duration'], self.curr_cond['dutycycle'])
        super().start()

    def present(self):
        if self.timer.elapsed_time() > self.curr_cond['duration'] and self.isrunning:
            self.isrunning = False
            self.log_stop()

    def stop(self):
        self.fill()