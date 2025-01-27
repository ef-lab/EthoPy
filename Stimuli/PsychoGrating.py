from core.Stimulus import *
from utils.PsychoPresenter import *
from utils.helper_functions import iterable


@stimulus.schema
class PsychoGrating(Stimulus, dj.Manual):
    definition = """
    # Definition of grating stimulus conditions
    -> StimCondition
    pos_x           : float                          # relative to the origin at the center
    ---
    pos_y           : float                          # relative to the origin at the center
    tex="sin"       : enum('sin','sqr','saw','tri')  # Texture to use for the primary carrier
    units="deg"     : enum('deg','pix','cm')         # Units to use when drawing
    size            : float                          # Size of the grating
    mask="sqr"      : enum('circle','sqr','gauss')     # mask to control the shape of the grating
    ori             : float                          # Initial orientation of the shape in degrees about its origin
    sf              : float                          # cycles/deg
    tf              : float                          # cycles/sec
    phase           : float                          # initial phase in 0-1
    contrast        : tinyint                        # 0-1
    warper          : tinyint(1)                     # 1 correct for flatness of monitor, 0 do not
    duration        : smallint                       # grating duration (seconds)
    """

    cond_tables = ["PsychoGrating"]
    required_fields = ['ori', 'sf', 'duration']
    default_key = {
        "pos_x": 0,
        "pos_y": 0,
        "tex": "sin",
        "units": "deg",
        "size": 100,
        "mask": "gauss",
        "tf": 0.5,
        "phase": 0,
        "contrast": 1,
        "warper": 1}

    def setup(self):
        """setup stimulation for presentation before experiment starts"""
        self.Presenter = Presenter(self.logger, self.monitor, background_color=self.fill_colors.background,
                                   photodiode='parity', rec_fliptimes=self.rec_fliptimes)

    def prepare(self, curr_cond, stim_period=''):
        self.gratings = dict()
        self.conds = dict()
        self.curr_cond = curr_cond
        for idx, pos_x in enumerate(iterable(self.curr_cond['pos_x'])):
            # Create GratingStim object
            cond = self._get_cond(idx)
            self.conds[idx] = cond
            self.gratings[idx] = psychopy.visual.GratingStim(self.Presenter.win,
                                                             pos=[cond['pos_x'], cond['pos_y']],
                                                             ori=cond['ori'],
                                                             sf=cond['sf'],
                                                             tex=cond['tex'],
                                                             units=cond['units'],
                                                             size=[cond['size'], cond['size']],
                                                             mask=cond['mask'],
                                                             phase=cond['phase'],
                                                             contrast=cond['contrast'])

    def present(self):
        if self.timer.elapsed_time() > self.curr_cond['duration']:
            self.in_operation = False
            return
        # Stimulus presentation (
        for idx, grat in enumerate(iterable(self.curr_cond['pos_x'])):
            self.gratings[idx].phase += self.conds[idx]['tf'] / self.monitor.fps # assuming 60 Hz refresh rate
            self.gratings[idx].draw()
        self.Presenter.flip()

    def _get_cond(self, idx=0):
        return {k: v if type(v) is int or type(v) is float or type(v) is str or type(v) is bool else v[idx]
                for k, v in self.curr_cond.items()}

    def exit(self):
        """exit stimulus stuff"""
        self.Presenter.win.close()