from Stimuli.Grating import *

@stimulus.schema
class Tones_Grating(GratingRP, dj.Manual):
    """ This class handles the presentation of Grating and Tone stimuli"""
    
    cond_tables = ['Tones', 'Grating']
    required_fields = ['tone_duration', 'tone_frequency']
    default_key = {
        'tone_volume'         : 50,
        'tone_pulse_freq'     : 0,
        'theta'               : 0,
        'spatial_freq'        : .05,
        'phase'               : 0,
        'contrast'            : 100,
        'square'              : 0,
        'temporal_freq'       : 1,
        'flatness_correction' : 1,
        'duration'            : 3000,
        }

    def stop(self):
        super(Tones_Grating, self).stop()
        self.exp.interface.stop_sound()
        
    def start(self):
        tone_duration = self.curr_cond['tone_duration']
        tone_frequency = self.curr_cond['tone_frequency']
        tone_volume = self.curr_cond['tone_volume']
        tone_pulse_freq=self.curr_cond['tone_pulse_freq']
        self.exp.interface.give_sound(tone_frequency, tone_duration, tone_volume, tone_pulse_freq)
        super().start()