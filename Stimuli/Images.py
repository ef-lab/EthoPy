from core.Stimulus import *
from time import sleep
import pygame
from pygame.locals import *
import io, os, imageio
import numpy as np
import cv2


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
    
    # instead of Image in line 14, should it be the following?
    # image_id             : int                          # image index
    # image_class          : char(8)                      # image class
        
    print('inside class Images')
    default_key = dict(pre_blank_period=200, presentation_time=1000)
    required_fields = ['pre_blank_period', 'presentation_time']
    cond_tables = ['Images']
    
    def init(self, exp):
        super().init(exp)
        print('inside init')
    #def setup(self):
        # setup parameters
        self.path = os.path.dirname(os.path.abspath(__file__)) + '/images/'
        self.size = (self.monitor['resolution_x'], self.monitor['resolution_y'])     # window size
        #print(self.size)
        self.color = [50, 50, 50]  # default background color
        self.phd_size = (50, 50)    # default photodiode signal size in pixels

        # setup pygame
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.unshow()
        self.timer = Timer()
        pygame.mouse.set_visible(0)

    def prepare(self, curr_cond, stim_period=''):
        print('inside prepare')
        self.curr_cond = curr_cond
        self.clock = pygame.time.Clock()

        image_height, image_width = self.get_image_info(self.curr_cond, 'ImageClass.Info', 'image_height', 'image_width')
        #print(image_height, image_width)
        self.imsize = (image_width, image_height)
        self.upscale = self.size[0] / self.imsize[0]
        #print(self.size[0], self.imsize[0])
        #print(self.upscale)
        self.y_pos = int((self.size[1] - self.imsize[1]*self.upscale)/2)
        #print(self.y_pos)
        
        self.isrunning = True
        self.timer.start()

    def present(self):
        print('inside present')
        print(self.curr_cond['pre_blank_period'])
        print(self.timer.elapsed_time())
        if self.curr_cond['pre_blank_period'] > 0 and self.timer.elapsed_time() < self.curr_cond['pre_blank_period']:
            print('inside pre-blank')
            #blank the screen
            self.unshow((0, 0, 0))
            self.clock.tick(self.curr_cond['pre_blank_period'])
            print(self.timer.elapsed_time())
        elif self.timer.elapsed_time() < (self.curr_cond['pre_blank_period'] + self.curr_cond['presentation_time']):
            print('inside presentation')
            #print(self.timer.elapsed_time())
            #show image
            curr_img = self.get_image_info(self.curr_cond, 'Image', 'image')
            print(np.shape(curr_img[0]))
            if self.upscale != 1:
                curr_img = cv2.resize(curr_img[0], dsize=(self.size), interpolation=cv2.INTER_CUBIC)
                #py_image = pygame.transform.smoothscale(py_image, (self.size[0], int(self.imsize[1]*self.upscale)))
            img_rgb = curr_img[..., None].repeat(3, -1).astype(np.int32)
            print(np.shape(img_rgb))
            py_image = img_rgb.swapaxes(0, 1)
            print(np.shape(py_image))
            #py_image = pygame.image.load(curr_img) #correct path
            #py_image = pygame.pixelcopy.make_surface(curr_img)
            #py_image = pygame.image.frombuffer(self.vid.get_next_data(), self.vsize, "RGB")

            print('before blit')
            #print(self.screen.get_size())
            #print(np.shape(curr_img))
            #print(curr_img.swapaxes(0, 1))
            #print(np.shape(curr_img.swapaxes(0, 1)))
            pygame.surfarray.blit_array(self.screen, py_image)
            print('after blit array')
            #self.screen.blit(py_image, (0, self.y_pos)) #self.y_pos
            self.flip()
            #self.curr_frame += 1
            #self.clock.tick_busy_loop(self.vfps)
            self.clock.tick(self.curr_cond['presentation_time']) #this doesn't look correct.. having both the if and the tick with image duration
        else:
            print('inside else')
            print(self.timer.elapsed_time())
            self.isrunning = False
            #self.vid.close()
            self.unshow()

    def stop(self):
        print('inside stop')
        #self.vid.close()
        self.unshow()
        self.log_stop()
        self.isrunning = False

    def punish_stim(self):
        self.unshow((0, 0, 0))

    def unshow(self, color=False):
        print('inside unshow')
        if not color:
            color = self.color
        self.screen.fill(color)
        self.flip()

    def flip(self):
        print('inside flip')
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == QUIT: pygame.quit()
        self.flip_count += 1

    @staticmethod
    def exit():
        print('inside exit')
        pygame.mouse.set_visible(1)
        pygame.display.quit()
        pygame.quit()

    def get_image_info(self, key, table, *fields):
        print('inside image info')
        return self.exp.logger.get(schema='stimulus', table=table, key=key, fields=fields)

    def encode_photodiode(self):
        """Encodes the flip number n in the flip amplitude.
        Every 32 sequential flips encode 32 21-bit flip numbers.
        Thus each n is a 21-bit flip number:
        FFFFFFFFFFFFFFFFCCCCP
        P = parity, only P=1 encode bits
        C = the position within F
        F = the current block of 32 flips
        """
        n = self.flip_count + 1
        amp = 127 * (n & 1) * (2 - (n & (1 << (((np.int64(np.floor(n / 2)) & 15) + 6) - 1)) != 0))
        surf = pygame.Surface(self.phd_size)
        surf.fill((amp, amp, amp))
        self.screen.blit(surf, (0, 0))


