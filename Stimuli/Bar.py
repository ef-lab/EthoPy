from Stimulus import *
from utils.flat2curve import flat2curve
import pygame
from pygame.locals import *


class FancyBar(Stimulus):
    """ This class handles the presentation of Movies"""

    def __init__(self, logger, params, conditions, beh=False):
        super().__init__(logger, params, conditions, beh)
        self.cycles = None

    def get_cond_tables(self):
        return ['BarCond']

    def setup(self):
        # setup parameters
        ymonsize = self.params['monitor_size'] * 2.54 / np.sqrt(1 + self.params['monitor_aspect'] ** 2)  # cm Y monitor size
        monSize = [ymonsize * self.params['monitor_aspect'], ymonsize ]
        y_res = int(self.params['max_res'] / self.params['monitor_aspect'])
        self.monRes = [self.params['max_res'],int(y_res + np.ceil(y_res % 2))]
        self.FoV = np.arctan(np.array(monSize) / 2 / self.params['monitor_distance']) * 2 * 180 / np.pi  # in degrees
        self.FoV[1] = self.FoV[0]/ self.params['monitor_aspect']
        self.color = [0, 0, 0]
        self.fps = 30              # default presentation framerate

        # setup pygame
        pygame.init()
        self.clock = pygame.time.Clock()
        self.screen = pygame.display.set_mode((0, 0), HWSURFACE | DOUBLEBUF | NOFRAME) #---> this works but minimizes when clicking (Emina)
        self.unshow()
        pygame.mouse.set_visible(0)

    def prepare(self):
        self._get_new_cond()
        if not self.curr_cond:
            self.isrunning = False
            return
        self.isrunning = True
        self.timer.start()
        self.curr_frame = 1

        # initialize hor/ver gradients
        caxis = 1 if self.curr_cond['axis'] == 'vertical' else 0
        Yspace = np.linspace(-self.FoV[1], self.FoV[1], self.monRes[1]) * self.curr_cond['direction']
        Xspace = np.linspace(-self.FoV[0], self.FoV[0], self.monRes[0]) * self.curr_cond['direction']
        self.cycles = dict()
        [self.cycles[abs(caxis - 1)], self.cycles[caxis]] = np.meshgrid(-Yspace/2/self.curr_cond['bar_width'],
                                                                        -Xspace/2/self.curr_cond['bar_width'])
        if self.curr_cond['flatness_correction']:
            I_c, self.transform = flat2curve(self.cycles[0], self.params['monitor_distance'],
                                             self.params['monitor_size'], method='index',
                                             center_x=self.params['center_x'], center_y=self.params['center_y'])
            self.BarOffset = -np.max(I_c) - 0.5
            deg_range = (np.ptp(I_c)+1)*self.curr_cond['bar_width']
        else:
            deg_range = (self.FoV[caxis] + self.curr_cond['bar_width'])   # in degrees
            self.transform = lambda x: x
            self.BarOffset = np.min(self.cycles[0]) - 0.5
        self.nbFrames = np.ceil( deg_range / self.curr_cond['bar_speed'] * self.fps)
        self.BarOffsetCyclesPerFrame = deg_range / self.nbFrames / self.curr_cond['bar_width']

        # compute fill parameters
        if self.curr_cond['style'] == 'checkerboard':  # create grid
            [X, Y] = np.meshgrid(-Yspace / 2 / self.curr_cond['grid_width'], -Xspace / 2 / self.curr_cond['grid_width'])
            VG1 = np.cos(2 * np.pi * X) > 0  # vertical grading
            VG2 = np.cos((2 * np.pi * X) - np.pi) > 0  # vertical grading with pi offset
            HG = np.cos(2 * np.pi * Y) > 0  # horizontal grading
            Grid = VG1 * HG + VG2 * (1 - HG)  # combine all
            self.StimOffsetCyclesPerFrame = self.curr_cond['flash_speed'] / self.fps
            self.fill = lambda x: abs(Grid - (np.cos(2 * np.pi * x) > 0))
        elif self.curr_cond['style'] == 'grating':
            self.StimOffsetCyclesPerFrame = self.curr_cond['grat_freq'] / self.fps
            self.fill = lambda x: np.cos(2 * np.pi * (self.cycles[1]*self.curr_cond['bar_width']/self.curr_cond['grat_width'] + x)) > 0  # vertical grading
        elif self.curr_cond['style'] == 'none':
            self.StimOffsetCyclesPerFrame = 1
            self.fill = lambda x: 1
        self.StimOffset = 0  # intialize offsets

    def present(self):
        if self.curr_frame < self.nbFrames:
            offset_cycles = self.cycles[0] + self.BarOffset
            offset_cycles[np.logical_or(offset_cycles < -0.5, offset_cycles > .5)] = 0.5  # threshold grading to create a single bar
            texture = np.uint8((np.cos(offset_cycles * 2 * np.pi) > -1) * self.fill(self.StimOffset)*254)
            new_surface = pygame.surfarray.make_surface(self.transform(np.tile(texture[:,:,np.newaxis],(1,3))))
            screen_width = self.screen.get_width()
            screen_height = self.screen.get_height()
            pygame.transform.scale(new_surface, (screen_width, screen_height), self.screen)
            self.flip()
            self.curr_frame += 1
            self.StimOffset += self.StimOffsetCyclesPerFrame
            self.BarOffset += self.BarOffsetCyclesPerFrame
            self.clock.tick_busy_loop(self.fps)
        else:
            self.isrunning = False
            self.unshow()

    def stop(self):
        self.unshow()
        self.isrunning = False

    def unshow(self, color=False):
        if not color:
            color = self.color
        self.screen.fill(color)
        self.flip()

    def flip(self):
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
        self.flip_count += 1

    def close(self):
        pygame.mouse.set_visible(1)
        pygame.display.quit()
        pygame.quit()


