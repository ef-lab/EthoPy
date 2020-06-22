from Stimulus import *
import os


class RPMovies(Stimulus):
    """ This class handles the presentation of Movies with an optimized library for Raspberry pi"""

    def setup(self):
        # setup parameters
        self.path = 'stimuli/'     # default path to copy local stimuli
        self.size = (800, 480)     # window size
        self.color = [127, 127, 127]  # default background color
        self.loc = (0, 0)          # default starting location of stimulus surface
        self.fps = 30              # default presentation framerate
        self.phd_size = (50, 50)    # default photodiode signal size in pixels

        # setup pygame
        if not pygame.get_init():
            pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.unshow()
        pygame.mouse.set_visible(0)
        pygame.display.toggle_fullscreen()

    def prepare(self):
        self.probes = np.array([d['probe'] for d in self.conditions])
        from omxplayer import OMXPlayer
        self.player = OMXPlayer
        # store local copy of files
        if not os.path.isdir(self.path):  # create path if necessary
            os.makedirs(self.path)
        for cond in self.conditions:
            clip_info = self.logger.get_clip_info(cond)
            filename = self.path + clip_info['file_name']
            if not os.path.isfile(filename):
                print('Saving %s ...' % filename)
                clip_info['clip'].tofile(filename)

    def init(self):
        self.isrunning = True
        clip_info = self.logger.get_clip_info(self.curr_cond)
        filename = self.path + clip_info['file_name']
        self.vid = self.player(filename, args=['--win', '0 15 800 465', '--no-osd'],
                               dbus_name='org.mpris.MediaPlayer2.omxplayer0')  # start video
        self.timer.start()
        self.logger.log_stim()

    def present(self):
        if self.timer.elapsed_time() > self.curr_cond['movie_duration']:
            self.isrunning = False
            self.vid.quit()

    def stop(self):
        try:
            self.vid.quit()
        except:
            pass
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

    def close(self):
        """Close stuff"""
        pygame.mouse.set_visible(1)
        pygame.display.quit()
        pygame.quit()

