from Stimulus import *
import pygame

class Odors(Stimulus):
    """ This class handles the presentation of Odors"""

    def get_condition_tables(self):
        return ['OdorCond']

    def setup(self):
        # setup parameters
        self.size = (800, 480)     # window size
        self.color = [10, 10, 10]  # default background color

        # setup pygame
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.unshow()
        pygame.display.toggle_fullscreen()

    def init(self):
        delivery_port = self.curr_cond['delivery_port']
        odor_id = self.curr_cond['odor_id']
        odor_dur = self.curr_cond['odor_duration']
        odor_dutycycle = self.curr_cond['dutycycle']
        self.beh.give_odor(delivery_port, odor_id, odor_dur, odor_dutycycle)
        self.isrunning = True
        self.timer.start()

    def prepare(self):
        self._get_new_cond()

    def unshow(self, color=False):
        """update background color"""
        if not color:
            color = self.color
        self.screen.fill(color)
        
    def stop(self):
        self.isrunning = False

    def close(self):
        """Close stuff"""
        pygame.mouse.set_visible(1)
        pygame.display.quit()
        pygame.quit()
