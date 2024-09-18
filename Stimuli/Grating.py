from core.Stimulus import *
import io, imageio
from utils.helper_functions import flat2curve
from utils.Presenter import *


@stimulus.schema
class Grating(Stimulus, dj.Manual):
    definition = """
    # This class handles the presentation of static Gratings
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
        ymonsize = self.monitor.size * 2.54 / np.sqrt(1 + self.monitor.aspect ** 2)  # cm Y monitor size
        fov = np.arctan(ymonsize / 2 / self.monitor.distance) * 2 * 180 / np.pi  # Y FOV degrees
        self.px_per_deg = self.monitor.resolution_y/fov

    def make_conditions(self, conditions=[]):
        self.path = self.logger.source_path + '/movies/'
        if not os.path.isdir(self.path):  # create path if necessary
            os.makedirs(self.path)
        super().make_conditions(conditions)
        for cond in conditions:
            if cond['temporal_freq'] != 0:
                filename = self._get_filename(cond)
                tuple = self.exp.logger.get(schema='stimulus', table='Grating.Movie',
                                            key={**cond, 'file_name': filename}, fields=['stim_hash'])
                if not tuple:
                    print('Making movie %s', filename)
                    cond['lamda'] = int(self.px_per_deg/cond['spatial_freq'])
                    theta_frame_step = (cond['temporal_freq'] / self.monitor.fps) * np.pi * 2
                    image = self._make_grating(**cond)
                    images = image[:self.monitor.resolution_x, :self.monitor.resolution_y]
                    if cond['flatness_correction']:
                        images, transform = flat2curve(images, self.monitor.distance,
                                                    self.monitor.size, method='index',
                                                    center_x=self.monitor.center_x,
                                                       center_y=self.monitor.center_y)
                        images = self._gray2rgb(images)
                    else:
                        transform = lambda x: x
                    for iframe in range(0, int(cond['duration']*self.monitor.fps/1000 + 10)):
                        print('\r' + ('frame %d/%d' % (iframe, int(cond['duration']*self.monitor.fps/1000 + 10))), end='')
                        cond['phase'] += theta_frame_step
                        image = self._make_grating(**cond)
                        images = np.dstack((images, self._gray2rgb(transform(image[:self.monitor.resolution_x,
                                                                                   :self.monitor.resolution_y]))))
                    print('\r' + 'done!')
                    images = np.transpose(images[:, :, :], [2, 1, 0])
                    self._im2mov(self.path + filename, images)
                    self.logger.log('Grating.Movie', {**cond, 'file_name': filename,
                                                      'clip': np.fromfile(self.path + filename, dtype=np.int8)},
                                    schema='stimulus', priority=2, block=True, validate=True)
        return conditions

    def prepare(self, curr_cond):
        self.in_operation = True
        self.movie = False
        self.frame_idx = 0
        curr_cond['lamda'] = int(self.px_per_deg / curr_cond['spatial_freq'])
        self.curr_cond = curr_cond
        if curr_cond['temporal_freq'] == 0:
            image = self._make_grating(**curr_cond)
            image = image[:self.monitor.resolution_x, :self.monitor.resolution_y]
            if curr_cond['flatness_correction']:
                image, transform = flat2curve(image, self.monitor.distance,
                                          self.monitor.size, method='index',
                                          center_x=self.monitor.center_x,
                                          center_y=self.monitor.center_y)
                image = image[:self.monitor.resolution_x, :self.monitor.resolution_y]
            self.grating = self.Presenter.make_surface(self._gray2rgb(image, 3))
        else:
            self.movie = True
            self.curr_cond.update(dict(filename=self._get_filename(curr_cond)))
            clip = self.exp.logger.get(schema='stimulus', table='Grating.Movie', key=self.curr_cond, fields=['clip'])
            self.vid = imageio.get_reader(io.BytesIO(clip[0].tobytes()), 'mov')
            self.vsize = self.vid.get_meta_data()['size']
            self.vfps = self.vid.get_meta_data()['fps']

        self.timer.start()

    def present(self):
        if self.timer.elapsed_time() > self.curr_cond['duration']:
            self.in_operation = False
        elif self.movie:
            grating = pygame.image.frombuffer(self.vid.get_next_data(), self.vsize, "RGB")
            self.Presenter.render(grating)
            self.Presenter.tick(self.vfps)
        elif self.frame_idx == 0:
            self.Presenter.render(self.grating)
        self.frame_idx += 1

    def fill(self, color=False):
        if not color:
            color = self.fill_colors.background
        if self.fill_colors.background: self.Presenter.fill(color)

    def stop(self):
        super().stop()
        if self.movie: self.vid.close()

    def exit(self):
        self.Presenter.quit()

    def _gray2rgb(self, im, c=1):
        return np.transpose(np.tile(im, [c, 1, 1]), (1, 2, 0))

    def _get_filename(self, cond):
        basename = ''.join([c for c in cond['stim_hash'] if c.isalpha()])
        pname = '_'.join('{}'.format(p) for p in self.monitor.values())
        return basename + '-' + pname + '.mov'

    def _make_grating(self, lamda=50, theta=0, phase=0, contrast=100, square=False, **kwargs):
        """ Makes an oriented grating
        lamda: wavelength (number of pixels per cycle)
        theta: grating orientation in degrees
        phase: phase of the grating
        """
        w = np.max((self.monitor.resolution_x, self.monitor.resolution_y)) + 2 * lamda
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

    def _im2mov(self, fn, images):
        w = imageio.get_writer(fn, fps=self.monitor.fps)
        for frame in images:
            w.append_data(frame)
        w.close()
