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
        self.probe_history = []  #  History term for bias calculation
        self.reward_history = []  #  History term for performance calculation
        self.licked_probe = 0

    def is_licking(self):
        return False, False

    def is_ready(self, elapsed_time=False):
        return False, 0

    def is_hydrated(self):
        rew = np.nansum(self.reward_history)
        self.logger.update_total_liquid(rew)
        if self.params['max_reward']:
            return rew >= self.params['max_reward']
        else:
            return False

    def reward(self, reward_amount=0):
        hist = self.probe_history; hist.append(self.licked_probe)
        self.probe_history = hist
        rew = self.reward_history; rew.append(reward_amount)
        self.reward_history = rew
        print('Giving Water at probe:%1d' % self.licked_probe)

    def punish(self):
        hist = self.probe_history; hist.append(self.licked_probe)
        self.probe_history = hist
        rew = self.reward_history; rew.append(0)
        self.reward_history = rew

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

    def prepare(self, condition):
        pass


class RPBehavior(Behavior):
    """ This class handles the behavior variables for RP """
    def __init__(self, logger, params):
        self.probe = RPProbe(logger)
        self.probe_history = []  #  History term for bias calculation
        self.reward_history = []  #  History term for performance calculation
        super(RPBehavior, self).__init__(logger, params)

    def is_licking(self):
        self.licked_probe = self.probe.lick()
        if self.licked_probe > 0: # reset lick timer if licking is detected
            self.resp_timer.start()
        return self.licked_probe

    def is_ready(self, init_duration):
        if init_duration == 0:
            return True
        else:
            ready, ready_time = self.probe.in_position()
            return ready and ready_time > init_duration

    def reward(self, reward_amount=0):
        hist = self.probe_history; hist.append(self.licked_probe)
        self.probe_history = self.probe_history.append(hist)
        rew = self.reward_history; rew.append(reward_amount)
        self.reward_history = self.reward_history.append(rew)
        self.probe.give_liquid(self.licked_probe)
        self.logger.log_liquid(self.licked_probe, reward_amount)

    def give_odor(self, delivery_idx, odor_idx, odor_dur, odor_dutycycle):
        self.probe.give_odor(delivery_idx, odor_idx, odor_dur, odor_dutycycle)
        self.logger.log_stim()

    def inactivity_time(self):  # in minutes
        return numpy.minimum(self.probe.timer_probe1.elapsed_time(),
                             self.probe.timer_probe2.elapsed_time()) / 1000 / 60

    def cleanup(self):
        self.probe.cleanup()

    def prepare(self, condition):
        self.probe.calc_pulse_dur(condition['reward_amount'])


class DummyProbe(Behavior):
    def __init__(self, logger, params):
        self.lick_timer = Timer()
        self.lick_timer.start()
        self.ready_timer = Timer()
        self.ready_timer.start()
        self.ready = False
        self.probe = 0

        super(DummyProbe, self).__init__(logger, params)

    def is_ready(self, init_duration):
        self.__get_events()
        elapsed_time = self.ready_timer.elapsed_time()
        return self.ready and elapsed_time > init_duration

    def inactivity_time(self):  # in minutes
        return self.lick_timer.elapsed_time() / 1000 / 60

    def is_licking(self):
        probe = self.__get_events()
        # reset lick timer if licking is detected &
        if probe > 0:
            self.resp_timer.start()
        self.licked_probe = probe
        return probe

    def __get_events(self):
        probe = 0
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.logger.log_lick(1)
                    print('Probe 1 activated!')
                    probe = 1
                    self.lick_timer.start()
                elif event.key == pygame.K_RIGHT:
                    self.logger.log_lick(2)
                    print('Probe 2 activated!')
                    probe = 2
                elif event.key == pygame.K_SPACE and self.ready:
                    self.ready = False
                    print('off position')
                elif event.key == pygame.K_SPACE and not self.ready:
                    self.lick_timer.start()
                    self.ready = True
                    print('in position')
        return probe
