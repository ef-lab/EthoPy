from core.Behavior import *
from core.Interface import *
from utils.Timer import *
import pygame
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
        self.interface = RPProbe(exp=exp)
        super(MultiPort, self).setup(exp)
        self.interface.setup_touch_exit()

    def is_licking(self, since=0):
        licked_port, tmst = self.interface.get_last_lick()
        if tmst >= since and licked_port:
            self.licked_port = licked_port
            self.resp_timer.start()
        else:
            self.licked_port = 0
        return self.licked_port

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
        return np.any(np.equal(self.licked_port, self.curr_cond['response_port']))

    def reward(self):
        self.interface.give_liquid(self.licked_port)
        self.log_reward(self.reward_amount[self.licked_port])
        self.update_history(self.licked_port, self.reward_amount[self.licked_port])
        return True

    def exit(self):
        self.interface.cleanup()
        self.interface.ts.stop()

    def prepare(self, condition):
        self.curr_cond = condition
        self.reward_amount = self.interface.calc_pulse_dur(condition['reward_amount'])

    def punish(self):
        port = self.licked_port if self.licked_port > 0 else np.nan
        self.update_history(port)


class DummyPorts(MultiPort):
    def setup(self, exp):
        import pygame
        self.lick_timer = Timer()
        self.lick_timer.start()
        self.ready_timer = Timer()
        self.ready_timer.start()
        self.ready = False
        self.interface = 0
        pygame.init()
        #self.screen = pygame.display.set_mode((800, 480))
        self.params = exp.params
        self.resp_timer = Timer()
        self.resp_timer.start()
        self.logger = exp.logger
        self.exp = exp
        self.rew_port = 0
        self.choices = np.array(np.empty(0))
        self.choice_history = list()  # History term for bias calculation
        self.reward_history = list()  # History term for performance calculation
        self.licked_port = 0
        self.reward_amount = dict()
        self.curr_cond = []

    def is_ready(self, duration, since=0):
        if duration == 0: return True
        self.__get_events()
        elapsed_time = self.ready_timer.elapsed_time()
        return self.ready and elapsed_time >= duration

    def is_licking(self,since=0):
        port = self.__get_events()
        if port > 0: self.resp_timer.start()
        self.licked_port = port
        return port

    def get_response(self, since=0):
        port = self.is_licking(since)
        return port > 0

    def is_correct(self):
        return np.any(np.equal(self.licked_port, self.curr_cond['response_port']))

    def prepare(self, condition):
        self.curr_cond = condition
        self.reward_amount = condition['reward_amount']

    def reward(self):
        self.update_history(self.licked_port, self.reward_amount)
        self.log_reward(self.reward_amount)
        print('Giving Water at port:%1d' % self.licked_port)
        return True

    def punish(self):
        print('punishing')
        port = self.licked_port if self.licked_port > 0 else np.nan
        #self.log_activity('Punishment', dict(punishment_type=self.curr_cond['punishment_type']))
        self.update_history(port)

    def exit(self):
        pass

    def __get_events(self):
        port = 0
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.logger.log('Activity.Lick', dict(port=1), schema='behavior')
                    print('Probe 1 activated!')
                    port = 1
                    self.lick_timer.start()
                elif event.key == pygame.K_RIGHT:
                    self.logger.log('Activity.Lick', dict(port=2), schema='behavior')
                    print('Probe 2 activated!')
                    port = 2
                elif event.key == pygame.K_SPACE and not self.ready:
                    self.lick_timer.start()
                    self.ready = True
                    self.log_activity('Proximity', dict(port=3, in_position=self.ready))
                    print('in position')
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE and self.ready:
                    self.ready = False
                    self.log_activity('Proximity', dict(port=3, in_position=self.ready))
                    print('off position')
                    print(pygame.mouse.get_pos())
            elif event.type == pygame.MOUSEBUTTONDOWN:
                print(pygame.mouse.get_pos())
        return port
