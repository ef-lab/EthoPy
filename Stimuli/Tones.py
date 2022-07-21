from Stimuli.RPScreen import *


@stimulus.schema
class Tones(RPScreen, dj.Manual):
    definition = """
    # This class handles the presentation of Odors
    -> StimCondition
    ---
    tone_duration             : int                     # tone duration (ms)
    tone_frequency            : int                     # tone frequency (hz)
    tone_volume               : int                     # tone volume (percent)
    """

    cond_tables = ['Tones','RPScreen']
    required_fields = ['tone_duration', 'tone_frequency']
    default_key = {'dutycycle'         : 50,
                    'reward_color'     : [128, 128, 128],
                    'punish_color'     : [0, 0, 0],
                    'ready_color'      : [64, 64, 64],
                    'background_color' : [32, 32, 32]
                    } 

    def start(self):
        tone_duration = self.curr_cond['tone_duration']
        tone_frequency = self.curr_cond['tone_frequency']
        tone_volume = self.curr_cond['tone_volume']
        self.exp.interface.give_sound(tone_frequency, tone_duration, tone_volume)
        print('Sound volume: ', tone_volume)
        super().start()