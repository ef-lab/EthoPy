from Stimuli.Grating import *

@stimulus.schema
class Tones_Grating(Grating, dj.Manual):
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
        'temporal_freq'       : 0,
        'flatness_correction' : 1,
        'duration'            : 3000,
        }
  
        
    def start(self):
        tone_frequency = self.curr_cond['tone_frequency']
        tone_volume = self.curr_cond['tone_volume']
        tone_pulse_freq=self.curr_cond['tone_pulse_freq']
        if 0< self.curr_cond['tone_pulse_freq']<10 :
            raise ValueError('Tone pulse frequency cannot be between zero and 10Hz (not including)')
        self.exp.interface.give_sound(tone_frequency, tone_volume, tone_pulse_freq)
        super().start()
    
    def present(self):
        super().present()
        if self.timer.elapsed_time() > self.curr_cond['tone_duration'] and self.isrunning:
            self.isrunning = False
            self.stop()

    def stop(self):
        try:
            self.vid.quit()
        except:
            self._init_player()
            self.vid.quit()
        self.log_stop()
        self.isrunning = False
        self.exp.interface.stop_sound()