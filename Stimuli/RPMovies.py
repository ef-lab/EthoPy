from Stimulus import *
import os


class RPMovies(Stimulus):
    """ This class handles the presentation of Movies with an optimized library for Raspberry pi"""

    def prepare(self):
        self.probes = np.array([d['probe'] for d in self.conditions])
        self.logger.log_conditions('MovieCond', self.conditions)

        from omxplayer import OMXPlayer
        self.player = OMXPlayer
        # store local copy of files
        if not os.path.isdir(self.path):  # create path if necessary
            os.makedirs(self.path)
        for cond in self.conditions:
            clip_info = self.logger.get_clip_info(cond)
            filename = self.path + clip_info['file_name']
            if not os.path.isfile(filename):
                clip_info['clip'].tofile(filename)

    def init_stim(self):
        self.isrunning = True
        clip_info = self.logger.get_clip_info(self.curr_cond)
        filename = self.path + clip_info['file_name']
        self.vid = self.player(filename, args=['--win', '0 15 800 465', '--no-osd'],
                               dbus_name='org.mpris.MediaPlayer2.omxplayer0')  # start video
        self.timer.start()

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
