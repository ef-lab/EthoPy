from core.Behavior import *
from core.Interface import *
from utils.Timer import *
import pygame
import numpy as np


@behavior.schema
class Response(dj.Manual):
    definition = """
    # Mouse behavioral response
    -> Session  
    """

    class Proximity(dj.Part):
        definition = """
        # Center port information
        -> Response
        port                 : tinyint          # port id
        time	     	  	 : int           	# time from session start (ms)
        ---
        in_position          : tinyint
        """

    class Lick(dj.Part):
        definition = """
        # Lick timestamps
        -> Response
        port                 : tinyint          # port id
        time	     	  	 : int           	# time from session start (ms)
        """


@behavior.schema
class MultiPort(Behavior, dj.Manual):
    definition = """
    # This class handles the behavior variables for RP
    ->BehCondition
    """

    class Lick(dj.Part):
        definition = """
        # Lick timestamps
        -> MultiPort
        response_port              : tinyint          # response port id
        """

    class Reward(dj.Part):
        definition = """
        # reward probe conditions
        -> MultiPort
        ---
        reward_port               : tinyint          # reward port id
        reward_amount=0        : float            # reward amount
        -> Rewards
        """

    cond_tables = ['MultiPort', 'MultiPort.Lick', 'MultiPort.Reward']
    required_fields = ['response_port', 'reward_port', 'reward_amount']
    default_key = {'reward_type': 'water'}

    def setup(self, logger, params):
        self.interface = RPProbe(logger)
        super(MultiPort, self).setup(logger, params)

    def is_licking(self, since=0):
        licked_probe, tmst = self.interface.get_last_lick()
        if tmst >= since and licked_probe:
            self.licked_probe = licked_probe
            self.resp_timer.start()
        else:
            self.licked_probe = 0
        return self.licked_probe

    def get_response(self, since=0):
        return self.is_licking(since) > 0

    def is_ready(self, duration, since=False):
        ready, ready_time, tmst = self.interface.in_position()
        if duration == 0:
            return True
        elif not since:
            return ready and ready_time > duration # in position for specified duration
        elif tmst >= since:
            return ready_time > duration  # has been in position for specified duration since timepoint
        else:
            return (ready_time + tmst - since) > duration  # has been in position for specified duration since timepoint

    def is_correct(self):
        return np.any(np.equal(self.licked_probe, self.curr_cond['probe']))

    def reward(self):
        self.interface.give_liquid(self.licked_probe)
        self.logger.log('Reward.Trial', dict(probe=self.licked_probe,
                                               reward_amount=self.reward_amount[self.licked_probe]))
        self.update_history(self.licked_probe, self.reward_amount[self.licked_probe])
        return True

    def inactivity_time(self):  # in minutes
        return np.minimum(self.interface.timer_probe1.elapsed_time(),
                          self.interface.timer_probe2.elapsed_time()) / 1000 / 60

    def cleanup(self):
        self.interface.cleanup()

    def prepare(self, condition):
        self.curr_cond = condition
        self.reward_amount = self.interface.calc_pulse_dur(condition['reward_amount'])

    def punish(self):
        probe = self.licked_probe if self.licked_probe > 0 else np.nan
        self.update_history(probe)


class DummyPorts(MultiPort):
    def setup(self, logger, params):
        import pygame
        self.lick_timer = Timer()
        self.lick_timer.start()
        self.ready_timer = Timer()
        self.ready_timer.start()
        self.ready = False
        self.interface = 0
        pygame.init()
        self.screen = pygame.display.set_mode((800, 480))
        self.params = params
        self.resp_timer = Timer()
        self.resp_timer.start()
        self.logger = logger
        self.rew_probe = 0
        self.choices = np.array(np.empty(0))
        self.choice_history = list()  # History term for bias calculation
        self.reward_history = list()  # History term for performance calculation
        self.licked_probe = 0
        self.reward_amount = dict()
        self.curr_cond = []

    def is_ready(self, duration, since=0):
        if duration == 0: return True
        self.__get_events()
        elapsed_time = self.ready_timer.elapsed_time()
        return self.ready and elapsed_time >= duration

    def is_licking(self,since=0):
        probe = self.__get_events()
        if probe > 0: self.resp_timer.start()
        self.licked_probe = probe
        return probe

    def get_response(self, since=0):
        probe = self.is_licking(since)
        return probe > 0

    def is_correct(self):
        return np.any(np.equal(self.licked_probe, self.curr_cond['probe']))

    def prepare(self, condition):
        self.curr_cond = condition
        self.reward_amount = condition['reward_amount']

    def reward(self):
        self.update_history(self.licked_probe, self.reward_amount)
        self.logger.log('LiquidDelivery', dict(probe=self.licked_probe,
                                               reward_amount=self.reward_amount))
        print('Giving Water at probe:%1d' % self.licked_probe)
        return True

    def punish(self):
        print('punishing')
        probe = self.licked_probe if self.licked_probe > 0 else np.nan
        self.update_history(probe)

    def __get_events(self):
        probe = 0
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.logger.log('Lick', dict(probe=1))
                    print('Probe 1 activated!')
                    probe = 1
                    self.lick_timer.start()
                elif event.key == pygame.K_RIGHT:
                    self.logger.log('Lick', dict(probe=2))
                    print('Probe 2 activated!')
                    probe = 2
                elif event.key == pygame.K_SPACE and not self.ready:
                    self.lick_timer.start()
                    self.ready = True
                    print('in position')
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE and self.ready:
                    self.ready = False
                    print('off position')
                    print(pygame.mouse.get_pos())
            elif event.type == pygame.MOUSEBUTTONDOWN:
                print(pygame.mouse.get_pos())
        return probe
