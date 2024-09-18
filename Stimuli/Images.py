from core.Stimulus import *
import os
import numpy as np
from utils.Presenter import *


@stimulus.schema
class Image(dj.Lookup):
    definition = """
    # images conditions
    image_class              : char(24)                   # 1 for test image, else 0
    image_id                 : int                        # image index
    ---
    image                    : longblob                   # actual image
    """

@stimulus.schema
class Images(Stimulus, dj.Manual):
    definition ="""
    # images conditions
    -> StimCondition
    ---
    -> Image
    pre_blank_period     : int                        # (ms) off duration
    presentation_time    : int                        # (ms) image duration
    stimulus_class='Images'  : char(24)
    """

    default_key = dict(pre_blank_period=200, presentation_time=1000)
    required_fields = ['pre_blank_period', 'presentation_time']
    cond_tables = ['Images']

    def setup(self):
        super().setup()
        # setup parameters
        self.path = os.path.dirname(os.path.abspath(__file__)) + '/images/'

    def prepare(self, curr_cond, stim_period=''):
        self.frame_idx = 0
        self.curr_cond = curr_cond
        self.clock = pygame.time.Clock()
        curr_img = self._get_image_info(self.curr_cond, 'Image', 'image')
        image_height, image_width = self._get_image_info(self.curr_cond, 'ImageClass.Info', 'image_height',
                                                         'image_width')
        self.imsize = (image_width, image_height)
        curr_img = curr_img[0]
        img_rgb = curr_img[..., None].repeat(3, -1).astype(np.int32)
        self.curr_img = self.Presenter.make_surface(img_rgb.swapaxes(0, 1))

        self.in_operation = True
        self.timer.start()

    def present(self):
        if self.curr_cond['pre_blank_period'] > 0 and self.timer.elapsed_time() < self.curr_cond['pre_blank_period']:
            #blank the screen
            self.fill()
            self.clock.tick(self.curr_cond['pre_blank_period'])
        elif self.timer.elapsed_time() < (self.curr_cond['pre_blank_period'] + self.curr_cond['presentation_time']):
            #show image
            if self.frame_idx == 0:
                self.Presenter.render(self.curr_img)
            self.frame_idx += 1
        else:
            self.in_operation = False


    def _get_image_info(self, key, table, *fields):
        return self.exp.logger.get(schema='stimulus', table=table, key=key, fields=fields)
