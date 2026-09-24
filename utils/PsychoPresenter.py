import psychopy.visual
import psychopy.event
import psychopy.core
from psychopy.visual.windowwarp import Warper
import numpy as np
import pygame


class Presenter():

    def __init__(self, logger, monitor, background_color=(0, 0, 0), photodiode=False, rec_fliptimes=False):
        self.logger = logger
        self.monitor = monitor
        self.clock = pygame.time.Clock()

        # define the window
        self.win = psychopy.visual.Window(
            size=[monitor.resolution_x, monitor.resolution_y],
            monitor='testMonitor', screen=monitor.screen_idx-1,
            fullscr=monitor.fullscreen, useFBO=True, waitBlanking=True)

        # compensate for monitor flatness
        if monitor.flatness_correction:
            self.warper = Warper(self.win,
                                 warp='spherical',
                                 warpGridsize=64,
                                 flipHorizontal=False,
                                 flipVertical=False)
            self.warper.dist_cm = 5 #self.monitor.distance
            self.warper.warpGridsize = 64
            self.warper.changeProjection('spherical', eyepoint=(monitor.center_x+0.5, monitor.center_y+0.5))

        # record fliptimes for syncing
        self.rec_fliptimes = rec_fliptimes
        if self.rec_fliptimes:
            self.fliptimes_dataset = self.logger.createDataset(dataset_name='fliptimes',
                                                               dataset_type=np.dtype([("flip_idx", np.double),
                                                                                      ("tmst", np.double)]))
        # initialize variables
        self.flip_count = 0
        self.photodiode = photodiode
        self.phd_size = 0.1  # default photodiode signal size in ratio of the X screen size
        self.window_ratio = self.monitor.resolution_x / self.monitor.resolution_y
        self._setup_photodiode(photodiode)
        self.background_color = background_color
        self.fill()

    def _setup_photodiode(self, photodiode=True):
        if photodiode:
            self.photodiode_rect = psychopy.visual.Rect(self.win,
                                                        units='norm',
                                                        width=self.phd_size,
                                                        height=self.phd_size * float(self.window_ratio),
                                                        pos=[-1 + self.phd_size / 2,
                                                             1 - self.phd_size * float(self.window_ratio) / 2])
            if photodiode == 'parity':
                # Encodes the flip even / dot in the flip amplitude
                self.phd_f = lambda x: float(float(x // 2) == x / 2)
            elif photodiode == 'flipcount':
                # Encodes the flip count (n) in the flip amplitude.
                # Every 32 sequential flips encode 32 21-bit flip numbers.
                # Thus each n is a 21-bit flip number: FFFFFFFFFFFFFFFFCCCCP
                # C = the position within F
                # F = the current block of 32 flips
                self.phd_f = lambda x: 0.5 * float(((x+1) & 1) * (2 - ((x+1) & (1 << (((np.int64(np.floor((x+1) / 2)) & 15) + 6) - 1)) != 0)))
            else:
                print(photodiode, ' method not implemented! Available methods: parity, flipcount')

    def render_image(self, image):
        curr_image = psychopy.visual.ImageStim(self.win, image)
        curr_image.draw()
        self.flip()

    def set_background_color(self, color):
        self.background_color = color
        self.fill(color=color)

    def fill(self, color=False):
        """stimulus hiding method"""
        if not color:
            color = self.background_color
        if color:
            self.win.color = color
            self.flip()

    def flip(self):
        self.flip_count += 1
        self._encode_photodiode()
        self.win.flip()
        if self.rec_fliptimes:
            self.fliptimes_dataset.append('fliptimes', [self.flip_count, self.logger.logger_timer.elapsed_time()])
        self.tick()

    def tick(self):
        self.clock.tick(self.monitor.fps)

    def _encode_photodiode(self):
        """ Encodes the flip parity or flip number in the flip amplitude.
        """
        if self.photodiode:
            amp = self.phd_f(self.flip_count)
            #self.warper.changeProjection(None)
            self.photodiode_rect.color = [amp, amp, amp]
            self.photodiode_rect.draw()
            #self.warper.changeProjection('spherical', eyepoint=(self.monitor.center_x+0.5, self.monitor.center_y+0.5))

    def quit(self):
        self.win.close()
