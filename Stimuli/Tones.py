from Stimuli.RPScreen import *


@stimulus.schema
class Tones(RPScreen, dj.Manual):
    definition = """
    # This class handles the presentation of Odors
    -> StimCondition
    ---
    tone_duration             : int                     # tone duration (ms)
    tone_frequency            : int                     # tone frequency (hz)
    tone_volume               : int                     # tone volume (%)
    """

    cond_tables = ['Tones']
    required_fields = ['tone_duration', 'tone_frequency', 'tone_volume']
    default_key = {'dutycycle': 50}

    def start(self):
        tone_duration = self.curr_cond['tone_duration']
        tone_frequency = self.curr_cond['tone_frequency']
        tone_volume = self.curr_cond['tone_volume']
        self.exp.interface.give_sound(tone_frequency, tone_duration, tone_volume)
        super().start()