from Stimulus import *


class Odors(Stimulus):
    """ This class handles the presentation of Odors"""

    def setup(self):
        # setup parameters
        self.path = 'stimuli/'     # default path to copy local stimuli
        self.size = (800, 480)     # window size
        self.color = [10, 10, 10]  # default background color
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
        self.logger.log_conditions('OdorCond', conditions)

    def init(self):
        delivery_idx = self.curr_cond['delivery_idx']
        odor_idx = self.curr_cond['odor_idx']
        odor_dur = self.curr_cond['duration']
        odor_dutycycle = self.curr_cond['dutycycle']
        self.beh.give_odor(delivery_idx, odor_idx, odor_dur, odor_dutycycle)
        self.isrunning = True
        self.timer.start()
        
    def unshow(self, color=False):
        """update background color"""
        if not color:
            color = self.color
        self.screen.fill(color)
        self.flip()

    def stop(self):
        self.isrunning = False
