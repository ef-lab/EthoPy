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
        self.probe_history = np.array([])  # History term for bias calculation
        self.reward_history = np.array([])  # History term for performance calculation
        self.licked_probe = 0
        self.reward_amount = dict()

    def is_licking(self, since=0):
        return 0

    def is_ready(self, init_duration):
        return False, 0

    def is_hydrated(self):
        rew = np.nansum(self.reward_history)
        if self.params['max_reward']:
            return rew >= self.params['max_reward']
        else:
            return False

    def reward(self):
        self.update_history(self.licked_probe, self.reward_amount[self.licked_probe])
        self.logger.log_liquid(self.licked_probe, self.reward_amount[self.licked_probe])
        print('Giving Water at probe:%1d' % self.licked_probe)

    def punish(self):
        if self.licked_probe > 0:
            probe = self.licked_probe
        else:
            probe = np.nan
        self.update_history(probe)

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

    def update_history(self, probe=np.nan, reward=np.nan):
        self.probe_history = np.append(self.probe_history, probe)
        self.reward_history = np.append(self.reward_history, reward)
        self.logger.update_total_liquid(np.nansum(self.reward_history))

    def prepare(self, condition):
        pass


class RPBehavior(Behavior):
    """ This class handles the behavior variables for RP """
    def __init__(self, logger, params):
        self.probe = RPProbe(logger)
        super(RPBehavior, self).__init__(logger, params)

    def is_licking(self, since=0):
        licked_probe, tmst = self.probe.get_last_lick()
        if tmst >= since and licked_probe:
            self.licked_probe = licked_probe
            self.resp_timer.start()
        else:
            self.licked_probe = 0
        return self.licked_probe

    def is_ready(self, duration):
        if duration == 0:
            return True
        else:
            ready, ready_time = self.probe.in_position()
            return ready and ready_time > duration

    def is_correct(self, condition):
        return np.any(np.equal(self.licked_probe, condition['probe']))

    def reward(self):
        self.update_history(self.licked_probe, self.reward_amount[self.licked_probe])
        self.probe.give_liquid(self.licked_probe)
        self.logger.log_liquid(self.licked_probe, self.reward_amount[self.licked_probe])

    def give_odor(self, delivery_port, odor_id, odor_dur, odor_dutycycle):
        self.probe.give_odor(delivery_port, odor_id, odor_dur, odor_dutycycle)
        self.logger.log_stim()

    def inactivity_time(self):  # in minutes
        return np.minimum(self.probe.timer_probe1.elapsed_time(),
                          self.probe.timer_probe2.elapsed_time()) / 1000 / 60

    def cleanup(self):
        self.probe.cleanup()

    def prepare(self, condition):
        self.reward_amount = self.probe.calc_pulse_dur(condition['reward_amount'])


class DummyProbe(Behavior):
    def __init__(self, logger, params):
        self.lick_timer = Timer()
        self.lick_timer.start()
        self.ready_timer = Timer()
        self.ready_timer.start()
        self.ready = False
        self.probe = 0
        pygame.init()
        super(DummyProbe, self).__init__(logger, params)

    def is_ready(self, init_duration):
        self.__get_events()
        elapsed_time = self.ready_timer.elapsed_time()
        return self.ready and elapsed_time > init_duration

    def inactivity_time(self):  # in minutes
        return self.lick_timer.elapsed_time() / 1000 / 60

    def is_licking(self, since=0):
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
