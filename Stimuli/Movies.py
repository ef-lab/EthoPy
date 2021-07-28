from core.Stimulus import *
from time import sleep
import pygame
from pygame.locals import *
import io, os, imageio
stimuli2 = dj.create_virtual_module('stim2', 'lab_stimuli')


@stimuli2.schema


@stimulus.schema
class Movies(Stimulus, dj.Manual):
    definition = """
    # movie clip conditions
    -> StimCondition
    ---
    movie_name            : char(8)                      # short movie title
    clip_number           : int                          # clip index
    movie_duration       : smallint                     # movie duration
    skip_time            : smallint                     # start time in clip
    static_frame         : smallint                     # static frame presentation
    """

    default_key = dict(movie_duration=10, skip_time=0, static_frame=False)
    required_fields = ['movie_name', 'clip_number', 'movie_duration', 'skip_time', 'static_frame']
    cond_tables = ['Movies']

    def setup(self):
        # setup parameters
        self.path = 'stimuli/'     # default path to copy local  stimuli
        self.size = (400, 240)     # window size
        self.color = [127, 127, 127]  # default background color
        self.loc = (0, 0)          # default starting location of stimulus surface
        self.fps = 30              # default presentation framerate
        self.phd_size = (50, 50)    # default photodiode signal size in pixels
        self.flip_count = 0

        # setup pygame
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.unshow()
        self.timer = Timer()
        pygame.mouse.set_visible(0)

    def prepare(self, curr_cond, stim_period=''):
        self.curr_cond = curr_cond
        self.curr_frame = 1
        self.clock = pygame.time.Clock()
        clip = self.get_clip_info(self.curr_cond, 'Movie.Clip', 'clip')
        frame_height, frame_width = self.get_clip_info(self.curr_cond, 'Movie', 'frame_height', 'frame_width')
        self.vid = imageio.get_reader( io.BytesIO(clip[0].tobytes()), 'mov')
        self.vsize = (frame_width[0], frame_height[0])
        self.pos = np.divide(self.size, 2) - np.divide(self.vsize, 2)
        self.isrunning = True
        self.timer.start()
        self.logger.log('StimCondition.Trial', dict(period=stim_period, stim_hash=self.curr_cond['stim_hash']),
                        schema='stimulus')

    def present(self):
        if self.timer.elapsed_time() < self.curr_cond['movie_duration']:
            py_image = pygame.image.frombuffer(self.vid.get_next_data(), self.vsize, "RGB")
            self.screen.blit(py_image, self.pos)
            self.flip()
            self.curr_frame += 1
            self.clock.tick_busy_loop(self.fps)
        else:
            self.isrunning = False
            self.vid.close()
            self.unshow()

    def stop(self):
        self.vid.close()
        self.unshow()
        self.isrunning = False

    def punish_stim(self):
        self.unshow((0, 0, 0))

    def unshow(self, color=False):
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


class RPMovies(Movies):
    """ This class handles the presentation of Movies with an optimized library for Raspberry pi"""

    def setup(self):
        # setup parameters
        self.path = 'stimuli/'     # default path to copy local stimuli
        self.size = (800, 480)     # window size
        self.color = [127, 127, 127]  # default background color
        self.loc = (0, 0)          # default starting location of stimulus surface
        self.fps = 30              # default presentation framerate
        self.phd_size = (50, 50)    # default photodiode signal size in pixels
        self.flip_count = 0

        # setup pygame
        if not pygame.get_init():
            pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.unshow()
        pygame.mouse.set_visible(0)
        pygame.display.toggle_fullscreen()

        # setup movies
        from omxplayer import OMXPlayer
        self.player = OMXPlayer
        # store local copy of files
        if not os.path.isdir(self.path):  # create path if necessary
            os.makedirs(self.path)
        for cond in self.conditions:
            file = self.get_clip_info(cond, 'Movie.Clip', 'file_name')
            filename = self.path + file[0]
            if not os.path.isfile(filename):
                print('Saving %s ...' % filename)
                clip = self.get_clip_info(cond, 'Movie.Clip', 'clip')
                clip[0].tofile(filename)
        # initialize player
        self.vid = self.player(filename, args=['--aspect-mode', 'stretch', '--no-osd'],
                    dbus_name='org.mpris.MediaPlayer2.omxplayer1')
        self.vid.stop()

    def prepare(self, curr_cond, stim_period=''):
        self.curr_cond = curr_cond
        self.logger.log('StimCondition.Trial', dict(period=stim_period, stim_hash=self.curr_cond['stim_hash']),
                        schema='stimulus')
        self._init_player()
        self.isrunning = True
        try:
            self.vid.play()
        except:
            self._init_player()
            self.vid.play()
        if self.curr_cond['static_frame']:
            sleep(0.2)
            self.vid.pause()
        self.timer.start()

    def present(self):
        if self.timer.elapsed_time() > self.curr_cond['movie_duration']:
            self.isrunning = False
            self.vid.quit()

    def stop(self):
        try:
            self.vid.stop()
        except:
            self._init_player()
            self.vid.stop()
        self.unshow()
        self.isrunning = False

    def _init_player(self):
        self.filename = self.path + self.get_clip_info(self.curr_cond, 'Movie.Clip', 'file_name')
        try:
            self.vid.load(self.filename[0])
        except:
            self.vid = self.player(self.filename[0], args=['--aspect-mode', 'stretch', '--no-osd'],
                        dbus_name='org.mpris.MediaPlayer2.omxplayer1')
        self.vid.pause()
        self.vid.set_position(self.curr_cond['skip_time'])


