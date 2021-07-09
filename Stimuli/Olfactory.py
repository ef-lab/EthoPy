from core.Stimulus import *
import pygame


@stimulus.schema
class Odorants(dj.Lookup):
    definition = """
    # Odor identity information
    odorant_id           : int                          # odor index
    ---
    odorant_name=null    : varchar(128)                 # odor name
    concentration=100    : int                          # odor concentration in prc
    solvent=null         : varchar(255)                 
    description=null     : varchar(256)   
    """


@stimulus.schema
class Olfactory(Stimulus, dj.Manual):
    definition = """
    # This class handles the presentation of Odors
    -> StimCondition
    ---
    odor_duration             : int                     # odor duration (ms)
    """

    class Channel(dj.Part):
        definition = """
        # odor conditions
        -> Olfactory
        -> Odorants
        ---
        delivery_port        : int                      # delivery idx for channel mapping
        dutycycle            : int                      # odor dutycycle
        """

    cond_tables = ['Olfactory', 'Olfactory.Channel']
    required_fields = ['odor_duration', 'odorant_id', 'delivery_port']
    default_key = {'dutycycle': 50}

    def setup(self):
        # setup parameters
        self.size = (800, 480)     # window size
        self.color = [10, 10, 10]  # default background color

        # setup pygame
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.unshow()
        pygame.display.toggle_fullscreen()

    def start(self):
        delivery_port = self.curr_cond['delivery_port']
        odor_id = self.curr_cond['odor_id']
        odor_dur = self.curr_cond['odor_duration']
        odor_dutycycle = self.curr_cond['dutycycle']
        self.interface.give_odor(delivery_port, odor_id, odor_dur, odor_dutycycle)
        self.logger.log('StimOnset')
        self.isrunning = True
        self.timer.start()

    def unshow(self, color=False):
        """update background color"""
        if not color:
            color = self.color
        self.screen.fill(color)
        
    def stop(self):
        self.isrunning = False

    def exit(self):
        """Close stuff"""
        pygame.mouse.set_visible(1)
        pygame.display.quit()
        pygame.quit()
