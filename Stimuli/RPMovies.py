from Stimulus import *
import os


class RPMovies(Stimulus):
    """ This class handles the presentation of Movies with an optimized library for Raspberry pi"""

    def __init__(self, logger, params, conditions, beh=False):
        # initilize parameters
        self.params = params
        self.logger = logger
        self.conditions = conditions
        self.beh = beh
        self.isrunning = False
        self.flip_count = 0
        self.indexes = []
        self.curr_cond = []
        self.rew_probe = []
        self.probes = []
        self.timer = Timer()

    def setup(self):
        # setup parameters
        self.path = 'stimuli/'     # default path to copy local stimuli
        self.size = (800, 480)     # window size
        self.color = [127, 127, 127]  # default background color
        self.loc = (0, 0)          # default starting location of stimulus surface
        self.fps = 30              # default presentation framerate
        self.phd_size = (50, 50)    # default photodiode signal size in pixels

        # setup pygame
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.unshow()
        pygame.mouse.set_visible(0)
        pygame.display.toggle_fullscreen()

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

    def init(self):
        self.isrunning = True
        clip_info = self.logger.get_clip_info(self.curr_cond)
        filename = self.path + clip_info['file_name']
        self.vid = self.player(filename, args=['--win', '0 15 800 465', '--no-osd'],
                               dbus_name='org.mpris.MediaPlayer2.omxplayer0')  # start video
        self.timer.start()
        self.logger.log_stim()

    def present(self):
        if self.timer.elapsed_time() > self.params['stim_duration']:
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

    def get_new_cond(self):
        """Get curr condition & create random block of all conditions
        Should be called within init_trial
        """
        if self.params['randomization'] == 'block':
            if np.size(self.indexes) == 0:
                self.indexes = np.random.permutation(np.size(self.conditions))
            cond = self.conditions[self.indexes[0]]
            self.indexes = self.indexes[1:]
            self.curr_cond = cond
        elif self.params['randomization'] == 'random':
            self.curr_cond = np.random.choice(self.conditions)
        elif self.params['randomization'] == 'bias':
            if len(self.beh.probe_bias) == 0 or np.all(np.isnan(self.beh.probe_bias)):
                self.beh.probe_bias = np.random.choice(self.probes, 5)
                self.curr_cond = np.random.choice(self.conditions)
            else:
                mn = np.min(self.probes)
                mx = np.max(self.probes)
                bias_probe = np.random.binomial(1, 1 - np.nanmean((self.beh.probe_bias - mn)/(mx-mn)))*(mx-mn) + mn
                biased_conditions = [i for (i, v) in zip(self.conditions, self.probes == bias_probe) if v]
                self.curr_cond = np.random.choice(biased_conditions)