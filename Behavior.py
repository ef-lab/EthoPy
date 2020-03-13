from Probe import *
from utils.Timer import *
import pygame
import numpy as np


class Behavior:
    """ This class handles the behavior variables """
    def __init__(self, logger, params):
        self.params = params
        self.resp_timer = Timer()
        self.resp_timer.start()
        self.logger = logger
        self.rew_probe = 0
        self.probes = np.array(np.empty(0))
        self.probe_bias = np.repeat(np.nan, 1)  # History term for bias calculation

    def is_licking(self):
        return False, False

    def is_ready(self, elapsed_time=False):
        return False, 0

    def reward(self):
        print('Giving Water at probe:%1d' % self.rew_probe)

    def punish_with_air(self, probe, air_dur=200):
        print('Punishing with Air at probe:%1d' % probe)

    def give_odor(self, delivery_idx, odor_idx, odor_dur, odor_dutycycle):
        print('Odor %1d presentation for %d' % (odor_idx, odor_dur))

    def inactivity_time(self):  # in minutes
        return 0

    def cleanup(self):
        pass

    def get_in_position(self):
        pass

    def get_off_position(self):
        pass

    def update_bias(self):
        pass

class RPBehavior(Behavior):
    """ This class handles the behavior variables for RP """
    def __init__(self, logger, params):
        self.probe = RPProbe(logger)
        super(RPBehavior, self).__init__(logger, params)

    def is_licking(self):
        probe = self.probe.lick()
        time_since_last_lick = self.resp_timer.elapsed_time()
        if time_since_last_lick < self.params['response_interval']:
            probe = 0
        # reset lick timer if licking is detected &
        if probe > 0:
            self.resp_timer.start()
            rew_probe = probe == self.rew_probe
        else:
            rew_probe = False

        return probe, rew_probe

    def update_bias(self, probe):
        self.probe_bias = np.concatenate((self.probe_bias[1:], [probe]))

    def is_ready(self):
        ready, ready_time = self.probe.in_position()
        return ready, ready_time

    def water_reward(self):
        self.probe.give_liquid(self.rew_probe)

    def punish_with_air(self, probe, air_dur=200):
        self.probe.give_air(probe, air_dur)

    def give_odor(self, delivery_idx, odor_idx, odor_dur, odor_dutycycle):
        self.probe.give_odor(delivery_idx, odor_idx, odor_dur, odor_dutycycle)

    def inactivity_time(self):  # in minutes
        return numpy.minimum(self.probe.timer_probe1.elapsed_time(),
                             self.probe.timer_probe2.elapsed_time()) / 1000 / 60

    def cleanup(self):
        self.probe.cleanup()


class DummyProbe(Behavior):
    def __init__(self, logger, params):
        self.lick_timer = Timer()
        self.lick_timer.start()
        self.ready_timer = Timer()
        self.ready_timer.start()
        self.ready = False
        self.licked_probe = 0

        super(DummyProbe, self).__init__(logger, params)

    def is_ready(self, init_duration):
        self.__get_events()
        elapsed_time = self.ready_timer.elapsed_time()
        return self.ready and elapsed_time > init_duration

    def inactivity_time(self):  # in minutes
        return self.lick_timer.elapsed_time() / 1000 / 60

    def is_licking(self):
        self.__get_events()
        time_since_last_lick = self.resp_timer.elapsed_time()

        if time_since_last_lick < self.params['response_interval'] and self.licked_probe > 0:
            self.licked_probe = 0

        # reset lick timer if licking is detected &
        if self.licked_probe > 0:
            self.resp_timer.start()
        return self.licked_probe

    def __get_events(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.logger.log_lick(1)
                    print('Probe 1 activated!')
                    self.licked_probe = 1
                    self.lick_timer.start()
                elif event.key == pygame.K_RIGHT:
                    self.logger.log_lick(2)
                    print('Probe 2 activated!')
                    self.licked_probe = 2
                elif event.key == pygame.K_SPACE and self.ready:
                    self.ready = False
                    print('off position')
                elif event.key == pygame.K_SPACE and not self.ready:
                    self.lick_timer.start()
                    self.ready = True
                    print('in position')

