from core.Stimulus import *
import pygame
from pygame.locals import *


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
    default_key =  {'bg_level'              : 255,
                    'dot_level'             : 0,  # degrees
                    'dot_shape'             : 'rect'}

    def init(self, exp):
        super().init(exp)
        self.size = (self.monitor['resolution_x'], self.monitor['resolution_y'])
        self.color = [0, 0, 0]
        self.fps = self.monitor['fps']

        # setup pygame
        pygame.init()
        self.clock = pygame.time.Clock()
        #self.screen = pygame.display.set_mode(self.size)
        self.screen = pygame.display.set_mode((0, 0), HWSURFACE | DOUBLEBUF | NOFRAME,
                                              display=self.monitor['screen_idx']-1) #---> this works but minimizes when clicking (Emina)
        self.unshow()
        pygame.mouse.set_visible(0)

    def prepare(self, curr_cond):
        self.curr_cond = curr_cond
        self.color = self.curr_cond['bg_level']
        self.unshow()
        width = self.monitor['resolution_x']
        height = self.monitor['resolution_y']
        x_pos = self.curr_cond['dot_x'] + 0.5
        y_pos = self.curr_cond['dot_y'] + 0.5 * height / width
        self.rect = ((x_pos - self.curr_cond['dot_xsize'] / 2)*width,
                     (y_pos - self.curr_cond['dot_ysize'] / 2)*width,
                     self.curr_cond['dot_xsize']*width,
                     self.curr_cond['dot_ysize']*width)

    def start(self):
        super().start()
        pygame.draw.rect(self.screen, self.curr_cond['dot_level'], self.rect)
        self.flip()

    def present(self):
        if self.timer.elapsed_time() > self.curr_cond['dot_time']*1000:
            self.isrunning = False

    def stop(self):
        self.unshow()
        self.log_stop()
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

    def exit(self):
        pygame.mouse.set_visible(1)
        pygame.display.quit()
        pygame.quit()


