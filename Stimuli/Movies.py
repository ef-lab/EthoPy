from core.Stimulus import *
from time import sleep
import pygame
from pygame.locals import *
import io, os, imageio


@stimulus.schema
class Movies(Stimulus, dj.Manual):
    definition = """
    # movie clip conditions
    -> StimCondition
    ---
    movie_name           : char(8)                      # short movie title
    clip_number          : int                          # clip index
    movie_duration       : smallint                     # movie duration
    skip_time            : smallint                     # start time in clip
    static_frame         : smallint                     # static frame presentation
    """

    default_key = dict(movie_duration=10, skip_time=0, static_frame=False)
    required_fields = ['movie_name', 'clip_number', 'movie_duration', 'skip_time', 'static_frame']
    cond_tables = ['Movies']

    def setup(self):
        # setup parameters
        self.path = os.path.dirname(os.path.abspath(__file__)) + '/movies/'
        self.size = (self.monitor['resolution_x'], self.monitor['resolution_y'])     # window size
        self.color = [127, 127, 127]  # default background color
        self.phd_size = (50, 50)    # default photodiode signal size in pixels

        # setup pygame
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.fill()
        self.timer = Timer()
        pygame.mouse.set_visible(0)

    def prepare(self, curr_cond, stim_period=''):
        self.curr_cond = curr_cond
        self.curr_frame = 1
        self.clock = pygame.time.Clock()
        clip = self.get_clip_info(self.curr_cond, 'Movie.Clip', 'clip')
        frame_height, frame_width = self.get_clip_info(self.curr_cond, 'Movie', 'frame_height', 'frame_width')
        self.vid = imageio.get_reader(io.BytesIO(clip[0].tobytes()), 'mov')
        self.vsize = (frame_width[0], frame_height[0])
        self.vfps = self.vid.get_meta_data()['fps']
        self.upscale = self.size[0] / self.vsize[0]
        self.y_pos = int((self.size[1] - self.vsize[1]*self.upscale)/2)
        self.isrunning = True
        self.timer.start()

    def present(self):
        if self.timer.elapsed_time() < self.curr_cond['movie_duration']:
            py_image = pygame.image.frombuffer(self.vid.get_next_data(), self.vsize, "RGB")
            if self.upscale != 1:
                py_image = pygame.transform.smoothscale(py_image, (self.size[0], int(self.vsize[1]*self.upscale)))
            self.screen.blit(py_image, (0, self.y_pos))
            self.flip()
            self.curr_frame += 1
            self.clock.tick_busy_loop(self.vfps)
        else:
            self.isrunning = False
            self.vid.close()
            self.fill()

    def stop(self):
        self.vid.close()
        self.fill()
        self.log_stop()
        self.isrunning = False

    def punish_stim(self):
        self.fill((0, 0, 0))

    def fill(self, color=False):
        if not color:
            color = self.color
        self.screen.fill(color)
        self.flip()

    def flip(self):
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == QUIT: pygame.quit()
        self.flip_count += 1

    @staticmethod
    def exit():
        pygame.mouse.set_visible(1)
        pygame.display.quit()
        pygame.quit()

    def get_clip_info(self, key, table, *fields):
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

