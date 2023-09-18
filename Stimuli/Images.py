from core.Stimulus import *
from time import sleep
import io, os, imageio
import numpy as np
import cv2
from utils.Presenter import *


@stimulus.schema
class Images(Stimulus, dj.Manual):
    definition = """
    # images conditions
    -> StimCondition
    ---
    -> Image
    pre_blank_period     : int                        # (ms) off duration
    presentation_time    : int                        # (ms) image duration

    """

    default_key = dict(pre_blank_period=200, presentation_time=1000)
    required_fields = ['pre_blank_period', 'presentation_time']
    cond_tables = ['Images']

    def __init__(self):
        super().__init__()
        self.fill_colors.set({'background': (0, 0, 0)})

    def setup(self):
        # setup parameters
        self.path = os.path.dirname(os.path.abspath(__file__)) + '/images/'
        self.size = (self.monitor['resolution_x'], self.monitor['resolution_y'])     # window size
        self.color = [50, 50, 50]  # default background color
        self.phd_size = (50, 50)    # default photodiode signal size in pixels

        # setup pygame
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.fill()
        self.timer = Timer()
        pygame.mouse.set_visible(0)

    def prepare(self, curr_cond, stim_period=''):
        self.curr_cond = curr_cond
        self.clock = pygame.time.Clock()

        image_height, image_width = self.get_image_info(self.curr_cond, 'ImageClass.Info', 'image_height', 'image_width')
        self.imsize = (image_width, image_height)
        self.upscale = self.size[0] / self.imsize[0]
        self.y_pos = int((self.size[1] - self.imsize[1]*self.upscale)/2)
        
        self.isrunning = True
        self.timer.start()

    def present(self):
        if self.curr_cond['pre_blank_period'] > 0 and self.timer.elapsed_time() < self.curr_cond['pre_blank_period']:
            #blank the screen
            self.fill()
            self.clock.tick(self.curr_cond['pre_blank_period'])
        elif self.timer.elapsed_time() < (self.curr_cond['pre_blank_period'] + self.curr_cond['presentation_time']):
            #show image
            curr_img = self.get_image_info(self.curr_cond, 'Image', 'image')
            if self.upscale != 1:
                curr_img = cv2.resize(curr_img[0], dsize=(self.size), interpolation=cv2.INTER_CUBIC)
            img_rgb = curr_img[..., None].repeat(3, -1).astype(np.int32)
            py_image = img_rgb.swapaxes(0, 1)
            self.Presenter.render(py_image)
            self.clock.tick(self.curr_cond['presentation_time']) #this doesn't look correct.. having both the if and the tick with image duration
        else:
            self.isrunning = False
            self.fill()

    def stop(self):
        self.fill()
        self.log_stop()
        self.isrunning = False

    def fill(self, color=False):
        if not color:
            color = self.fill_colors.background
        if self.fill_colors.background: self.Presenter.fill(color)

    def exit(self):
        self.Presenter.quit()

    def _get_image_info(self, key, table, *fields):
        return self.exp.logger.get(schema='stimulus', table=table, key=key, fields=fields)



