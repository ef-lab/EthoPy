from Stimulus import *
import io, os, imageio
from time import sleep
import pygame
from pygame.locals import *
import datajoint as dj
stimuli = dj.create_virtual_module('stimuli.py', 'lab_stimuli', create_tables=True)
exp = dj.create_virtual_module('exp.py', 'lab_behavior', create_tables=True)


@stimuli.schema
class Movies(Stimulus, dj.Manual):
    definition = """
    # movie clip conditions
    cond_hash            : char(24)                     # unique condition hash
    ---
    movie_name           : char(8)                      # short movie title
    clip_number          : int                          # clip index
    movie_duration       : smallint                     # movie duration
    skip_time            : smallint                     # start time in clip
    static_frame         : smallint                     # static frame presentation
    """

    class Trial(dj.Part):
        definition = """
        # Stimulus onset timestamps
        -> exp.Trial
        -> Movies
        ---
        start_time           : int                          # start time from session start (ms)
        end_time             : int                          # end time from session start (ms)
        """

    default_key = dict(movie_duration=10, skip_time=0, static_frame=False)
    required_fields = ['movie_name', 'clip_number', 'movie_duration', 'skip_time', 'static_frame']

    def get_cond_tables(self):
        return ['MovieCond']

    def setup(self, logger, params, conditions, beh=False):
        super().setup(logger, params, conditions, beh)

        # setup parameters
        self.path = 'stimuli/'     # default path to copy local  stimuli
        self.size = (400, 240)     # window size
        self.color = [127, 127, 127]  # default background color
        self.loc = (0, 0)          # default starting location of stimulus surface
        self.fps = 30              # default presentation framerate
        self.phd_size = (50, 50)    # default photodiode signal size in pixels

        # setup pygame
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.unshow()
        pygame.mouse.set_visible(0)

        self.hash_dict = dict()
        for condition in conditions:
            cond = {**self.default_key, **condition}
            key = {sel_key: cond[sel_key] for sel_key in self.required_fields}
            self.hash_dict[condition['cond_hash']] = self.logger.log_condition(key, 'Movies', 'stim')

    def prepare(self):
        self._get_new_cond()
        self.curr_frame = 1
        self.clock = pygame.time.Clock()
        clip_info = self.get_clip_info(self.curr_cond)
        self.vid = imageio.get_reader(io.BytesIO(clip_info['clip'].tobytes()), 'ffmpeg')
        self.vsize = (clip_info['frame_width'], clip_info['frame_height'])
        self.pos = np.divide(self.size, 2) - np.divide(self.vsize, 2)

    def start(self):
        self.isrunning = True
        self.timer.start()
        self.stim_start = self.logger.session_timer.elapsed_time()

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
        stim_stop = self.logger.session_timer.elapsed_time()
        self.isrunning = False
        key = dict(self.logger.session_key, trial_idx=self.logger.curr_trial,
                   cond_hash=self.hash_dict[self.curr_cond['cond_hash']],
                   start_time=self.stim_start, end_time=stim_stop)
        self.logger.put(table='Movies.Trial', tuple=key, schema='stim')

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
    def close():
        pygame.mouse.set_visible(1)
        pygame.display.quit()
        pygame.quit()

    @staticmethod
    def get_clip_info(key):
        return (stimuli.Movie() * stimuli.Movie.Clip() & key).fetch1()

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
        self.set_intensity(self.params['intensity'])

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
            clip_info = self.get_clip_info(cond)
            filename = self.path + clip_info['file_name']
            if not os.path.isfile(filename):
                print('Saving %s ...' % filename)
                clip_info['clip'].tofile(filename)
        # initialize player
        self.vid = self.player(filename, args=['--aspect-mode', 'stretch', '--no-osd'],
                    dbus_name='org.mpris.MediaPlayer2.omxplayer1')
        self.vid.stop()

    def prepare(self):
        self._get_new_cond()
        self._init_player()

    def start(self):
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
        self.logger.log('StimOnset')

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

    def set_intensity(self, intensity=None):
        if intensity is None:
            intensity = self.params['intensity']
        cmd = 'echo %d > /sys/class/backlight/rpi_backlight/brightness' % intensity
        os.system(cmd)

    def _init_player(self):
        clip_info = self.logger.get_clip_info(self.curr_cond)
        self.filename = self.path + clip_info['file_name']
        try:
            self.vid.load(self.filename)
        except:
            self.vid = self.player(self.filename, args=['--aspect-mode', 'stretch', '--no-osd'],
                        dbus_name='org.mpris.MediaPlayer2.omxplayer1')
        self.vid.pause()
        self.vid.set_position(self.curr_cond['skip_time'])


