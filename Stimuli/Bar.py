from core.Stimulus import *
from utils.helper_functions import flat2curve
from utils.Presenter import *

@stimulus.schema
class Bar(Stimulus, dj.Manual):
    definition = """
    # This class handles the presentation of area mapping Bar stimulus
    -> StimCondition
    ---
    axis                  : enum('vertical','horizontal')
    bar_width             : float  # degrees
    bar_speed             : float  # degrees/sec
    flash_speed           : float  # cycles/sec
    grat_width            : float  # degrees
    grat_freq             : float
    grid_width            : float
    grit_freq             : float
    style                 : enum('checkerboard', 'grating','none')
    direction             : float             # 1 for UD LR, -1 for DU RL
    flatness_correction   : tinyint(1)        # 1 correct for flatness of monitor, 0 do not
    intertrial_duration   : int
    max_res               : smallint
    """

    cond_tables = ['Bar']
    default_key =  {'max_res'               : 1000,
                    'bar_width'             : 4,  # degrees
                    'bar_speed'             : 2,  # degrees/sec
                    'flash_speed'           : 2,
                    'grat_width'            : 10,  # degrees
                    'grat_freq'             : 1,
                    'grid_width'            : 10,
                    'grit_freq'             : .1,
                    'style'                 : 'checkerboard', # checkerboard, grating
                    'direction'             : 1,             # 1 for UD LR, -1 for DU RL
                    'flatness_correction'   : 1,
                    'intertrial_duration'   : 0}

    def setup(self):
        super().setup()
        ymonsize = self.monitor.size * 2.54 / np.sqrt(1 + self.monitor.aspect ** 2)  # cm Y monitor size
        monSize = [ymonsize * self.monitor.aspect, ymonsize]
        y_res = int(self.exp.params['max_res'] / self.monitor.aspect)
        self.monRes = [self.exp.params['max_res'], int(y_res + np.ceil(y_res % 2))]
        self.FoV = np.arctan(np.array(monSize) / 2 / self.monitor.distance) * 2 * 180 / np.pi  # in degrees
        self.FoV[1] = self.FoV[0] / self.monitor.aspect

    def prepare(self, curr_cond):
        self.curr_cond = curr_cond
        self.in_operation = True
        self.curr_frame = 1

        # initialize hor/ver gradients
        caxis = 1 if self.curr_cond['axis'] == 'vertical' else 0
        Yspace = np.linspace(-self.FoV[1], self.FoV[1], self.monRes[1]) * self.curr_cond['direction']
        Xspace = np.linspace(-self.FoV[0], self.FoV[0], self.monRes[0]) * self.curr_cond['direction']
        self.cycles = dict()
        [self.cycles[abs(caxis - 1)], self.cycles[caxis]] = np.meshgrid(-Yspace/2/self.curr_cond['bar_width'],
                                                                        -Xspace/2/self.curr_cond['bar_width'])
        if self.curr_cond['flatness_correction']:
            I_c, self.transform = flat2curve(self.cycles[0], self.monitor.distance,
                                             self.monitor.size, method='index',
                                             center_x=self.monitor.center_x,
                                             center_y=self.monitor.center_y)
            self.BarOffset = -np.max(I_c) - 0.5
            deg_range = (np.ptp(I_c)+1)*self.curr_cond['bar_width']
        else:
            deg_range = (self.FoV[caxis] + self.curr_cond['bar_width'])   # in degrees
            self.transform = lambda x: x
            self.BarOffset = np.min(self.cycles[0]) - 0.5
        self.nbFrames = np.ceil( deg_range / self.curr_cond['bar_speed'] * self.monitor.fps)
        self.BarOffsetCyclesPerFrame = deg_range / self.nbFrames / self.curr_cond['bar_width']

        # compute fill parameters
        if self.curr_cond['style'] == 'checkerboard':  # create grid
            [X, Y] = np.meshgrid(-Yspace / 2 / self.curr_cond['grid_width'], -Xspace / 2 / self.curr_cond['grid_width'])
            VG1 = np.cos(2 * np.pi * X) > 0  # vertical grading
            VG2 = np.cos((2 * np.pi * X) - np.pi) > 0  # vertical grading with pi offset
            HG = np.cos(2 * np.pi * Y) > 0  # horizontal grading
            Grid = VG1 * HG + VG2 * (1 - HG)  # combine all
            self.StimOffsetCyclesPerFrame = self.curr_cond['flash_speed'] / self.monitor.fps
            self.generate = lambda x: abs(Grid - (np.cos(2 * np.pi * x) > 0))
        elif self.curr_cond['style'] == 'grating':
            self.StimOffsetCyclesPerFrame = self.curr_cond['grat_freq'] / self.monitor.fps
            self.generate = lambda x: np.cos(2 * np.pi * (self.cycles[1]*self.curr_cond['bar_width']/self.curr_cond['grat_width'] + x)) > 0  # vertical grading
        elif self.curr_cond['style'] == 'none':
            self.StimOffsetCyclesPerFrame = 1
            self.generate = lambda x: 1
        self.StimOffset = 0  # intialize offsets

    def present(self):
        if self.curr_frame < self.nbFrames:
            offset_cycles = self.cycles[0] + self.BarOffset
            offset_cycles[np.logical_or(offset_cycles < -0.5, offset_cycles > .5)] = 0.5  # threshold grading to create a single bar
            texture = np.uint8((np.cos(offset_cycles * 2 * np.pi) > -1) * self.generate(self.StimOffset)*254)
            new_surface = pygame.surfarray.make_surface(self.transform(np.tile(texture[:, :, np.newaxis], (1, 3))))
            self.Presenter.render(new_surface)
            self.curr_frame += 1
            self.StimOffset += self.StimOffsetCyclesPerFrame
            self.BarOffset += self.BarOffsetCyclesPerFrame
            self.Presenter.tick(self.monitor.fps)
        else:
            self.in_operation = False
            self.fill()

