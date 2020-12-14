from Stimulus import *
import os
from time import sleep
import pygame
from pygame.locals import *


class SmellyMovies(Stimulus):
    """ This class handles the presentation of Visual (movies) and Olfactory (odors) stimuli"""

    def get_cond_tables(self):
        return ['MovieCond', 'OdorCond']

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
        for condm in self.conditions:
            clip_info = self.logger.get_clip_info(dict((k, condm[k]) for k in ('movie_name', 'clip_number')))
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
  
    def init(self):
        delivery_port = self.curr_cond['delivery_port']
        odor_id = self.curr_cond['odor_id']
        odor_dur = self.curr_cond['odor_duration']
        odor_dutycycle = self.curr_cond['dutycycle']
        self.isrunning = True
        self.vid.play()
        if self.curr_cond['static_frame']:
            sleep(0.2)
            self.vid.pause()
        self.beh.give_odor(delivery_port, odor_id, odor_dur, odor_dutycycle)
        self.timer.start()
        self.logger.log_stim()

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

    def close(self):
        """Close stuff"""
        pygame.mouse.set_visible(1)
        pygame.display.quit()
        pygame.quit()


