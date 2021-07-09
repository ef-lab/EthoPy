from Stimuli.RPScreen import *
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
class Olfactory(RPScreen, dj.Manual):
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

    def start(self):
        delivery_port = self.curr_cond['delivery_port']
        odor_id = self.curr_cond['odorant_id']
        odor_dur = self.curr_cond['odor_duration']
        odor_dutycycle = self.curr_cond['dutycycle']
        self.exp.interface.give_odor(delivery_port, odor_id, odor_dur, odor_dutycycle)
        super().start()

