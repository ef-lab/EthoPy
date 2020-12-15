from Stimulus import *
import os
import pigpio
import time,threading
from time import sleep
import pygame
from pygame.locals import *


class RPScreen(Stimulus):
    """ This class handles the presentation of Movies with an optimized library for Raspberry pi"""

    def get_cond_tables(self):
        return []

    def setup(self):
        # setup parameters
        self.size = (800, 480)     # window size
        self.color = [32, 32, 32]  # default background color
        self.loc = (0, 0)          # default starting location of stimulus surface
        self.fps = 30              # default presentation framerate
        self.phd_size = (50, 50)    # default photodiode signal size in pixels
        self.set_intensity(self.params['intensity'])
        self.sound_GPIO = 18
        self.sound_freq = 40000

        # setup pygame
        if not pygame.get_init():
            pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.unshow()
        pygame.mouse.set_visible(0)
        pygame.display.toggle_fullscreen()
        self.pi = pigpio.pi()
        #self.thread_runner = threading.Thread(target=self.give_sound)

    def prepare(self):
        self.unshow()
        self._get_new_cond()

    def init(self):
        self.isrunning = True
        self.timer.start()
        self.logger.log_stim()
        self.logger.log_stim()

    def ready_stim(self):
        self.unshow([64, 64, 64])
        # # #  this can go to reward stim for conditioning  # # #
        self.pi.hardware_PWM(self.sound_GPIO, self.sound_freq, 500000)
        time.sleep(.25)
        self.pi.hardware_PWM(self.sound_GPIO, 0, 0)

    def present(self):
        pass

    def reward_stim(self):
        self.unshow([255, 255, 255])

    def stop(self):
        self.isrunning = False

    def unshow(self, color=False):
        """update background color"""
        if not color:
            color = self.color
        self.screen.fill(color)
        self.flip()

    def flip(self):
        """ Main flip method"""
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()

        self.flip_count += 1

    def set_intensity(self, intensity=None):
        if intensity is None:
            intensity = self.params['intensity']
        cmd = 'echo %d > /sys/class/backlight/rpi_backlight/brightness' % intensity
        os.system(cmd)

    def close(self):
        """Close stuff"""
        pygame.mouse.set_visible(1)
        pygame.display.quit()
        pygame.quit()
        self.pi.stop()

