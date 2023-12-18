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

    def __init__(self):
        super().__init__()
        self.fill_colors.set({'background': (0, 0, 0),
                              'start': (0.125, 0.125, 0.125),
                              'ready': [],
                              'reward': (0.5, 0.5, 0.5),
                              'punish': (0, 0, 0)})
        self.grating_isrunning = False
        self.sound_isrunning = False

    def start(self):
        self.sound_isrunning = True
        self.grating_isrunning = True
        tone_frequency = self.curr_cond['tone_frequency']
        tone_volume = self.curr_cond['tone_volume']
        tone_pulse_freq=self.curr_cond['tone_pulse_freq']
        if 0 < self.curr_cond['tone_pulse_freq'] < 10:
            raise ValueError('Tone pulse frequency cannot be between zero and 10Hz (not including)')
        self.exp.interface.give_sound(tone_frequency, tone_volume, tone_pulse_freq)
        super().start()
    
    def present(self):
        if self.timer.elapsed_time() > self.curr_cond['tone_duration'] and self.sound_isrunning:
            self.stop_sound()
            self.sound_isrunning = False
        if self.timer.elapsed_time() > self.curr_cond['duration'] and self.grating_isrunning:
            super().stop()
            self.grating_isrunning = False

        if self.timer.elapsed_time() > self.curr_cond['duration'] and self.timer.elapsed_time() > self.curr_cond['tone_duration']:
            self.log_stop()
            self.isrunning = False
        elif self.movie and self.grating_isrunning:
            grating = pygame.image.frombuffer(self.vid.get_next_data(), self.vsize, "RGB")
            self.Presenter.render(grating)
            self.Presenter.tick(self.vfps)
        elif self.frame_idx == 0:
            self.Presenter.render(self.grating)
        self.frame_idx += 1

    def stop_sound(self):
        self.exp.interface.stop_sound()
