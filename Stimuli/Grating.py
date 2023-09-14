from core.Stimulus import *
import pygame, io, imageio
from utils.helper_functions import flat2curve
from pygame.locals import *


@stimulus.schema
class Grating(Stimulus, dj.Manual):
    definition = """
    # This class handles the presentation orientation
    -> StimCondition
    ---
    theta                  : smallint   # in degrees (0-360)
    spatial_freq           : float      # cycles/deg
    phase                  : float      # initial phase in rad
    contrast               : tinyint    # 0-100 Michelson contrast
    square                 : tinyint(1) # square flag
    temporal_freq          : float      # cycles/sec
    flatness_correction    : tinyint(1) # 1 correct for flatness of monitor, 0 do not
    duration               : smallint   # grating duration
    """

    cond_tables = ['Grating']
    default_key = {'theta'               : 0,
                   'spatial_freq'        : .05,
                   'phase'               : 0,
                   'contrast'            : 100,
                   'square'              : 0,
                   'temporal_freq'       : 1,
                   'flatness_correction' : 1,
                   'duration'            : 3000,
                   }

    class Movie(dj.Part):
        definition = """
        # object conditions
        -> Grating
        file_name                : varchar(256)
        ---
        clip                     : longblob     
        """

    def init(self, exp):
        super().init(exp)
        self.size = (self.monitor['resolution_x'], self.monitor['resolution_y'])    # window size
        self.color = [i*256 for i in self.monitor['background_color']]
        self.fps = self.monitor['fps']

        # setup pygame
        pygame.init()
        self.clock = pygame.time.Clock()
        #self.screen = pygame.display.set_mode((0, 0), HWSURFACE | DOUBLEBUF | NOFRAME, display=self.screen_idx-1) #---> this works but minimizes when clicking (Emina)
        #self.screen = pygame.display.set_mode(self.size)
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.FULLSCREEN)
        self.unshow()
        pygame.mouse.set_visible(0)
        ymonsize = self.monitor['monitor_size'] * 2.54 / np.sqrt(1 + self.monitor['monitor_aspect'] ** 2)  # cm Y monitor size
        fov = np.arctan(ymonsize / 2 / self.monitor['monitor_distance']) * 2 * 180 / np.pi  # Y FOV degrees
        self.px_per_deg = self.size[1]/fov

    def setup(self):
        super().setup()

    def prepare(self, curr_cond):
        self.curr_cond = curr_cond
        self.curr_frame = 1
        self.clock = pygame.time.Clock()
        self.curr_cond.update(dict(filename=self._get_filename(curr_cond)))
        clip = self.exp.logger.get(schema='stimulus', table='Grating.Movie', key=self.curr_cond, fields=['clip'])
        self.vid = imageio.get_reader(io.BytesIO(clip[0].tobytes()), 'mov')
        self.vsize = self.vid.get_meta_data()['size']
        self.vfps = self.vid.get_meta_data()['fps']
        self.isrunning = True
        self.timer.start()

    def present(self):
        if self.timer.elapsed_time() < self.curr_cond['duration']:
            py_image = pygame.image.frombuffer(self.vid.get_next_data(),  self.vsize, "RGB")
            self.screen.blit(py_image, (0, 0))
            self.flip()
            self.curr_frame += 1
            self.clock.tick_busy_loop(self.vfps)
        else:
            self.isrunning = False
            self.vid.close()
            #self.unshow()

    def ready_stim(self):
        self.unshow([i*256 for i in self.monitor['ready_color']])

    def reward_stim(self):
        self.unshow([i*256 for i in self.monitor['reward_color']])

    def punish_stim(self):
        self.unshow([i*256 for i in self.monitor['punish_color']])

    def start_stim(self):
        self.unshow([i*256 for i in self.monitor['start_color']])

    def stop(self):
        self.unshow([i*256 for i in self.monitor['background_color']])
        self.log_stop()
        self.isrunning = False

    def flip(self):
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == QUIT: pygame.quit()
        self.flip_count += 1

    def unshow(self, color=False):
        if not color:
            color = self.color
        self.screen.fill(color)
        self.flip()

    def exit(self):
        pygame.mouse.set_visible(1)
        pygame.display.quit()
        pygame.quit()

    def _gray2rgb(self, im, c=1):
        return np.transpose(np.tile(im, [c, 1, 1]), (1, 2, 0))

    def _get_filename(self, cond):
        basename = ''.join([c for c in cond['stim_hash'] if c.isalpha()])
        pname = '_'.join('{}'.format(p) for p in self.monitor.values())
        return basename + '-' + pname + '.mov'

    def _im2mov(self, fn, images):
        w = imageio.get_writer(fn, fps=self.fps)
        for frame in images:
            w.append_data(frame)
        w.close()

    def _make_grating(self, lamda=50, theta=0, phase=0, contrast=100, square=False, **kwargs):
        """ Makes an oriented grating
        lamda: wavelength (number of pixels per cycle)
        theta: grating orientation in degrees
        phase: phase of the grating
        """
        w = np.max(self.size) + 2 * lamda
        freq = w/lamda  # compute frequency from wavelength
        # make linear ramp
        x0 = np.linspace(0, 1, w) - 0.5
        xm, ym = np.meshgrid(x0, x0)
        # Change orientation by adding Xm and Ym together in different proportions
        theta_rad = (theta/180) * np.pi
        xt = xm * np.cos(theta_rad)
        yt = ym * np.sin(theta_rad)
        im = (np.sin(((xt + yt) * freq * 2 * np.pi) + phase)+1)/2
        if square > 0:
            im = np.double(im > 0.5)
        return np.uint8(np.floor((im*contrast/100 + (100-contrast)/200)*255))


class GratingRP(Grating):
    """ This class handles the presentation of Gratings with an optimized library for Raspberry pi"""

    def make_conditions(self, conditions=[]):
        self.path = os.path.dirname(os.path.abspath(__file__)) + '/movies/'
        if not os.path.isdir(self.path):  # create path if necessary
            os.makedirs(self.path)
        super().make_conditions(conditions)
        for cond in conditions:
            filename = self._get_filename(cond)
            tuple = self.exp.logger.get(schema='stimulus', table='Grating.Movie',
                                        key={**cond, 'file_name': filename}, fields=['stim_hash'])
            if not tuple:
                print('Making movie %s', filename)
                cond['lamda'] = int(self.px_per_deg/cond['spatial_freq'])
                theta_frame_step = (cond['temporal_freq'] / self.fps) * np.pi * 2
                image = self._make_grating(**cond)
                images = image[:self.monitor['resolution_x'], :self.monitor['resolution_y']]
                if cond['flatness_correction']:
                    images, transform = flat2curve(images, self.monitor['monitor_distance'],
                                                self.monitor['monitor_size'], method='index',
                                                center_x=self.monitor['monitor_center_x'],
                                                   center_y=self.monitor['monitor_center_y'])
                    images = self._gray2rgb(images)
                else:
                    transform = lambda x: x
                for iframe in range(0, int(cond['duration']*self.fps/1000 + 10)):
                    print('\r' + ('frame %d/%d' % (iframe, int(cond['duration']*self.fps/1000 + 10))), end='')
                    cond['phase'] += theta_frame_step
                    image = self._make_grating(**cond)
                    images = np.dstack((images, self._gray2rgb(transform(image[:self.monitor['resolution_x'],
                                                                               :self.monitor['resolution_y']]))))
                print('\r' + 'done!')
                images = np.transpose(images[:, :, :], [2, 1, 0])
                self._im2mov(self.path + filename, images)
                self.logger.log('Grating.Movie', {**cond, 'file_name': filename,
                                                  'clip': np.fromfile(self.path + filename, dtype=np.int8)},
                                schema='stimulus', priority=2, block=True, validate=True)
        return conditions

    def setup(self):
        # setup parameters
        self.path = os.path.dirname(os.path.abspath(__file__)) + '/movies/'
        self.size = (self.monitor['resolution_x'], self.monitor['resolution_y'])     # window size
        self.color = [i*256 for i in self.monitor['background_color']]  # default background color
        self.phd_size = (50, 50)    # default photodiode signal size in pixels

        # setup pygame
        if not pygame.get_init():
            pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.unshow() 
        pygame.mouse.set_visible(0)
        pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

        # setup movies
        from omxplayer import OMXPlayer
        self.player = OMXPlayer
        # store local copy of files
        if not os.path.isdir(self.path):  # create path if necessary
            os.makedirs(self.path)
        for cond in self.conditions:
            file = self.get_clip_info(cond, 'Grating.Movie', 'file_name')
            filename = self.path + file[0]
            if not os.path.isfile(filename):
                print('Saving %s ...' % filename)
                clip = self.get_clip_info(cond, 'Grating.Movie', 'clip')
                clip[0].tofile(filename)
        # initialize player
        self.vid = self.player(filename, args=['--aspect-mode', 'stretch', '--no-osd'],
                    dbus_name='org.mpris.MediaPlayer2.omxplayer1')
        self.vid.stop()

    def prepare(self, curr_cond, stim_period=''):
        self.curr_cond = curr_cond
        self.unshow([i*256 for i in self.monitor['start_color']])
        self._init_player()
        self.isrunning = True
        self.timer.start() 

    def present(self):
        if self.timer.elapsed_time() < self.curr_cond['duration']:
            try:
                self.vid.play()
            except:
                self._init_player()
                self.vid.play()
        else: 
            self.isrunning = False
            self.vid.quit()

    def stop(self):
        try:
            self.vid.quit()
        except:
            self._init_player()
            self.vid.quit()
        self.unshow([i*256 for i in self.monitor['background_color']])
        self.log_stop()
        self.isrunning = False

    def _init_player(self):
        self.filename = self.path + self.get_clip_info(self.curr_cond, 'Grating.Movie', 'file_name')
        try:
            self.vid.load(self.filename[0])
        except:
            self.vid = self.player(self.filename[0], args=['--aspect-mode', 'stretch', '--no-osd'],
                        dbus_name='org.mpris.MediaPlayer2.omxplayer1')
        self.vid.pause()

    def get_clip_info(self, key, table, *fields):
        key['file_name'] = self._get_filename(key)
        return self.exp.logger.get(schema='stimulus', table=table, key=key, fields=fields)


class GratingOld(Grating):
    """ This class handles the presentation of Gratigs with shifting surfaces"""
    def prepare(self, curr_cond):
        curr_cond['lamda'] = int(self.px_per_deg / curr_cond['spatial_freq'])
        self.curr_cond = curr_cond
        self.isrunning = True
        self.frame_idx = 0
        self.clock = pygame.time.Clock()

        image = self._make_grating(**curr_cond)
        image = image[:self.monitor['resolution_x'], :self.monitor['resolution_y']]
        if curr_cond['flatness_correction']:
            image, transform = flat2curve(image, self.monitor['monitor_distance'],
                                      self.monitor['monitor_size'], method='index',
                                      center_x=self.monitor['monitor_center_x'],
                                      center_y=self.monitor['monitor_center_y'])
            image = image[:self.monitor['resolution_x'], :self.monitor['resolution_y']]
        self.grating = pygame.surfarray.make_surface(self._gray2rgb(image, 3))
        self.frame_step = self.curr_cond['lamda'] * (self.curr_cond['temporal_freq'] / self.fps)

        self.xt = np.cos((self.curr_cond['theta'] / 180) * np.pi)
        self.yt = np.sin((self.curr_cond['theta'] / 180) * np.pi)
        self.timer.start()

    def present(self):
        displacement = np.mod(self.frame_idx * self.frame_step, self.curr_cond['lamda'])
        self.screen.blit(self.grating,
                         (-self.curr_cond['lamda'] + self.yt * displacement,
                          -self.curr_cond['lamda'] + self.xt * displacement))
        self.clock.tick_busy_loop(self.fps)
        self.flip()
        self.frame_idx += 1
        if self.timer.elapsed_time() > self.curr_cond['duration']:
            self.isrunning = False
            self.unshow()


