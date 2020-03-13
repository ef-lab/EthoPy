from Stimulus import *
import os
from utils.Timer import *


class RPMovies(Stimulus):
    """ This class handles the presentation of Movies with an optimized library for Raspberry pi"""
    def prepare(self, conditions):
        from omxplayer import OMXPlayer
        self.player = OMXPlayer
        # store local copy of files
        if not os.path.isdir(self.path):  # create path if necessary
            os.makedirs(self.path)
        for cond_idx in conditions:
            filename = self.path + \
                       (Movie.Clip() * MovieClipCond() & dict(cond_idx=cond_idx) & self.logger.session_key).fetch1(
                           'file_name')
            if not os.path.isfile(filename):
                (Movie.Clip() * MovieClipCond() & dict(cond_idx=cond_idx) & self.logger.session_key).fetch1(
                    'clip').tofile(filename)

    def init_stim(self, cond):
        self.isrunning = True
        filename = self.path + (Movie.Clip() * MovieClipCond() & dict(cond_idx=cond) &
                                     self.logger.session_key).fetch1('file_name')
        self.vid = self.player(filename, args=['--win', '0 15 800 465', '--no-osd'],
                               dbus_name='org.mpris.MediaPlayer2.omxplayer0')  # start video

        self.logger.start_trial(cond)  # log start trial
        self.timer.start()
        return cond

    def present(self):
        if self.timer.elapsed_time() > self.params['stim_duration']:
            self.isrunning = False
            self.vid.quit()

    def stop_stim(self):
        try:
            self.vid.quit()
        except:
            pass
        self.unshow()
        self.isrunning = False
