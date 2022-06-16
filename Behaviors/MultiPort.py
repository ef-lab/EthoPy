from core.Behavior import *
from utils.Timer import *
import numpy as np


@behavior.schema
class MultiPort(Behavior, dj.Manual):
    definition = """
    # This class handles the behavior variables for RP
    ->BehCondition
    """

    class Response(dj.Part):
        definition = """
        # Lick response condition
        -> MultiPort
        response_port              : tinyint          # response port id
        """

    class Reward(dj.Part):
        definition = """
        # reward port conditions
        -> MultiPort
        ---
        reward_port               : tinyint          # reward port id
        reward_amount=0           : float            # reward amount
        reward_type               : varchar(16)      # reward type
        """

    cond_tables = ['MultiPort', 'MultiPort.Response', 'MultiPort.Reward']
    required_fields = ['response_port', 'reward_port', 'reward_amount']
    default_key = {'reward_type': 'water'}

    def setup(self, exp):
        super(MultiPort, self).setup(exp)

    def is_ready(self, duration, since=False):
        position, ready_time, tmst = self.interface.in_position()
        if duration == 0:
            return True
        elif not since:
            return position.ready and ready_time > duration # in position for specified duration
        elif tmst >= since:
            return ready_time > duration  # has been in position for specified duration since timepoint
        else:
            return (ready_time + tmst - since) > duration  # has been in position for specified duration since timepoint

    def is_correct(self):
        return self.curr_cond['response_port'] == -1 or \
               np.any(np.equal(self.response.port, self.curr_cond['response_port']))

    def is_off_proximity(self):
        return self.interface.off_proximity()

    def reward(self, tmst=0):
        if self.response.reward: tmst=0 # if response and reward ports are the same no need of tmst 
        licked_port = self.is_licking(since=tmst, reward=True)
        if licked_port:
            self.interface.give_liquid(licked_port)
            self.log_reward(self.reward_amount[self.licked_port])
            self.update_history(self.response.port, self.reward_amount[self.licked_port])
            return True
        return False

    def exit(self):
        super().exit()
        self.interface.cleanup()

    def punish(self):
        port = self.response.port if self.response.port > 0 else np.nan
        self.update_history(port, punish=True)

