from Stimulus import *
import os


class VO(Stimulus):
    """ This class handles the presentation of Visual (movies) and Olfactory (odors) stimuli"""

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
                
        conditions = self.conditions
        for icond, cond in enumerate(conditions):
            values = list(cond.values())
            names = list(cond.keys())
            for ivalue, value in enumerate(values):
                if type(value) is list:
                    value = tuple(value)
                cond.update({names[ivalue]: value})
            conditions[icond] = cond
        self.logger.log_conditions(['OdorCond', 'MovieCond'], conditions)

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
  
    def init(self):
        delivery_idx = self.curr_cond['delivery_idx']
        odor_idx = self.curr_cond['odor_idx']
        odor_dur = self.curr_cond['odor_duration']
        odor_dutycycle = self.curr_cond['dutycycle']
        self.isrunning = True
        clip_info = self.logger.get_clip_info(dict((k, self.curr_cond[k]) for k in ('movie_name', 'clip_number')))
        filename = self.path + clip_info['file_name']
        self.vid = self.player(filename, args=['--win', '0 15 800 465', '--no-osd'],
                               dbus_name='org.mpris.MediaPlayer2.omxplayer0')  # start video
        self.beh.give_odor(delivery_idx, odor_idx, odor_dur, odor_dutycycle)
        self.timer.start()
        self.logger.log_stim()

    def present(self):
        if self.timer.elapsed_time() > self.conditions['movie_duration']:
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


