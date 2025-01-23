from core.Stimulus import *
from utils.PsychoPresenter import *

@stimulus.schema
class Dot(Stimulus, dj.Manual):
    definition = """
    # This class handles the presentation of area mapping Bar stimulus
    -> StimCondition
    ---
    bg_level              : tinyblob  # 0-255 
    dot_level             : tinyblob  # 0-255 
    dot_x                 : float  # (fraction of monitor width, 0 for center, from -0.5 to 0.5) position of dot on x axis
    dot_y                 : float  # (fraction of monitor width, 0 for center) position of dot on y axis
    dot_xsize             : float  # fraction of monitor width, width of dots
    dot_ysize             : float # fraction of monitor width, height of dots
    dot_shape             : enum('rect','oval') # shape of the dot
    dot_time              : float # (sec) time of each dot persists
    """

    cond_tables = ['Dot']
    required_fields = ['dot_x', 'dot_y', 'dot_xsize', 'dot_ysize', 'dot_time']
    default_key =  {'bg_level'              : 1,
                    'dot_level'             : 0,  # degrees
                    'dot_shape'             : 'rect'}

    def setup(self):
        self.Presenter = Presenter(self.logger, self.monitor, background_color=self.fill_colors.background,
                                   photodiode='parity', rec_fliptimes=self.rec_fliptimes)

    def prepare(self, curr_cond):
        self.curr_cond = curr_cond
        self.fill_colors.background = self.curr_cond['bg_level']
        self.Presenter.fill(self.curr_cond['bg_level'])
        self.rect = psychopy.visual.Rect(self.Presenter.win,
                                    width=self.curr_cond['dot_xsize'],
                                    height=self.curr_cond['dot_ysize'] * float(self.Presenter.window_ratio),
                                    pos=[self.curr_cond['dot_x'],
                                         self.curr_cond['dot_y'] * float(self.Presenter.window_ratio) ])

    def start(self):
        super().start()
        self.rect.color = self.curr_cond['dot_level']
        self.rect.draw()

    def stop(self):
        self.log_stop()
        self.in_operation = False

    def present(self):
        if self.timer.elapsed_time() > self.curr_cond['dot_time']*1000:
            self.in_operation = False

    def exit(self):
        self.Presenter.fill(self.fill_colors.background)
        super().exit()




