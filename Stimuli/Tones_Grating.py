from Stimuli.Grating import *


class Tones_Grating(Grating):
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
        self.grating_in_operation = False
        self.sound_in_operation = False

    def start(self):
        self.sound_in_operation = True
        self.grating_in_operation = True
        self.ready_flag = False
        tone_frequency = self.curr_cond['tone_frequency']
        tone_volume = self.curr_cond['tone_volume']
        tone_pulse_freq=self.curr_cond['tone_pulse_freq']
        if 0 < self.curr_cond['tone_pulse_freq'] < 10:
            raise ValueError('Tone pulse frequency cannot be between zero and 10Hz (not including)')
        self.exp.interface.give_sound(tone_frequency, tone_volume, tone_pulse_freq)
        super().start()
    
    def present(self):
        """
        This method is responsible for presenting media (sounds and gratings) based on 
        the elapsed time. It stops the sound after its duration, closes the gratings and 
        fills color if ready after the grating duration. It also renders the grating or 
        the movie frame based on the conditions.
        """
        elapsed_time = self.timer.elapsed_time()
        grating_duration = self.curr_cond["duration"]
        tone_duration = self.curr_cond["tone_duration"]

        if elapsed_time > tone_duration and self.sound_in_operation:
            self.exp.interface.stop_sound()
            self.sound_in_operation = False
        if elapsed_time > grating_duration and self.grating_in_operation:
            if self.movie: self.vid.close()
            if self.ready_flag:
                if self.fill_colors.ready: self.fill(self.fill_colors.ready)
            self.grating_in_operation = False
        if elapsed_time > grating_duration and self.timer.elapsed_time() > tone_duration and self.in_operation:
            self.in_operation = False
        elif self.movie and self.grating_in_operation:
            grating = pygame.image.frombuffer(self.vid.get_next_data(), self.vsize, "RGB")
            self.Presenter.render(grating)
            self.Presenter.tick(self.vfps)
        elif self.frame_idx == 0:
            self.Presenter.render(self.grating)
        self.frame_idx += 1

    # Stop sound stimulus when mooving ot the next state
    def stop(self):
        self.log_stop()
        self.in_operation=False
        self.exp.interface.stop_sound()

    def ready_stim(self):
        self.ready_flag = True
        if not self.grating_in_operation:
            super().ready_stim()

