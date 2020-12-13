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
        self.choices = np.array(np.empty(0))
        self.choice_history = list()  # History term for bias calculation
        self.reward_history = list()  # History term for performance calculation
        self.licked_probe = 0
        self.reward_amount = dict()
        self.curr_cond = []

    def is_licking(self, since=False):
        return 0

    def is_ready(self, init_duration, since=0):
        return True, 0

    def is_hydrated(self):
        return False

    def response(self, since=0):
        return self.is_licking(since) > 0

    def reward(self):
        pass

    def punish(self):
        pass

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

    def update_history(self, choice=np.nan, reward=np.nan):
        self.choice_history.append(choice)
        self.reward_history.append(reward)
        self.logger.update_total_liquid(np.nansum(self.reward_history))

    def prepare(self, condition, choices):
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

    def response(self, since=0):
        return self.is_licking(since) > 0

    def is_ready(self, duration, since=False):
        ready, ready_time, tmst = self.probe.in_position()
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

    def is_hydrated(self):
        rew = np.nansum(self.reward_history)
        if self.params['max_reward']:
            return rew >= self.params['max_reward']
        else:
            return False

    def reward(self):
        self.update_history(self.licked_probe, self.reward_amount[self.licked_probe])
        self.probe.give_liquid(self.licked_probe)
        self.logger.log_liquid(self.licked_probe, self.reward_amount[self.licked_probe])
        return True

    def give_odor(self, delivery_port, odor_id, odor_dur, odor_dutycycle):
        self.probe.give_odor(delivery_port, odor_id, odor_dur, odor_dutycycle)
        self.logger.log_stim()

    def inactivity_time(self):  # in minutes
        return np.minimum(self.probe.timer_probe1.elapsed_time(),
                          self.probe.timer_probe2.elapsed_time()) / 1000 / 60

    def cleanup(self):
        self.probe.cleanup()

    def prepare(self, condition, choices):
        self.curr_cond = condition
        self.reward_amount = self.probe.calc_pulse_dur(condition['reward_amount'])

    def punish(self):
        if self.licked_probe > 0:
            probe = self.licked_probe
        else:
            probe = np.nan
        self.update_history(probe)


class TouchBehavior(Behavior):
    def __init__(self, logger, params):
        import ft5406 as TS
        super(TouchBehavior, self).__init__(logger, params)
        self.screen_sz = np.array([800, 480])
        self.touch_area = 50  # +/- area in pixels that a touch can occur
        self.since = 0
        self.has_touched = False
        self.buttons = list()
        self.loc2px = lambda x: self.screen_sz/2 + np.array(x)*self.screen_sz[0]
        self.px2loc = lambda x: np.array(x)/self.screen_sz[0] - self.screen_sz/2
        self.probe = RPProbe(logger)
        self.ts = TS.Touchscreen()
        self.ts_press_event = TS.TS_PRESS
        self.last_touch_tmst = 0
        for touch in self.ts.touches:
            touch.on_press = self._touch_handler
            touch.on_release = self._touch_handler
        self.ts.run()

    def is_licking(self, since=0):
        licked_probe, tmst = self.probe.get_last_lick()
        if tmst >= since and licked_probe:
            self.licked_probe = licked_probe
            self.resp_timer.start()
        else:
            self.licked_probe = 0
        return self.licked_probe

    def is_touching(self, since=0, group='choice'):
        if group == 'target':
            tmst = np.max([b.tmst if b.is_target else 0 for b in self.buttons])
            self.touch = self.target_loc
        else:
            tmsts = [b.tmst if b.group == group else 0 for b in self.buttons]
            mx_idx = np.argmax(tmsts)
            tmst = tmsts[mx_idx]
            if group == 'choice':
                locs = [b.loc if b.group == group else 0 for b in self.buttons]
                self.touch = locs[mx_idx]
        if tmst >= since:
            self.resp_timer.start()
        self.has_touched = tmst >= since
        return self.has_touched

    def is_hydrated(self):
        rew = np.nansum(self.reward_history)
        if self.params['max_reward']:
            return rew >= self.params['max_reward']
        else:
            return False

    def response(self, since=0):
        self.since = since
        return self.is_licking(since) > 0 or self.is_touching(since)

    def is_ready(self, duration, since=0):
        if duration == 0:
            return True
        else:
            return self.is_touching(since, 'ready')

    def is_correct(self):
        return self.is_touching(self.since, 'target')

    def reward(self):
        licked_probe = self.is_licking()
        if np.any(np.equal(licked_probe, self.curr_cond['probe'])):
            self.probe.give_liquid(licked_probe)
            self.update_history(self.target_loc, self.reward_amount[licked_probe])
            self.logger.log_liquid(self.licked_probe, self.reward_amount[licked_probe])
            return True
        return False

    def punish(self):
        touched_loc =  self.touch if self.has_touched else np.nan
        self.update_history(touched_loc)

    def give_odor(self, delivery_port, odor_id, odor_dur, odor_dutycycle):
        self.probe.give_odor(delivery_port, odor_id, odor_dur, odor_dutycycle)
        self.logger.log_stim()

    def cleanup(self):
        self.probe.cleanup()
        self.ts.stop()

    def prepare(self, condition, choices):
        self.curr_cond = condition
        self.reward_amount = self.probe.calc_pulse_dur(condition['reward_amount'])
        self.target_loc = condition['correct_loc']
        buttons = list()
        buttons.append(self.Button(self.loc2px(condition['ready_loc']), 'ready'))
        for choice in choices:
            is_target = True if (condition['correct_loc'] == choice).all() else False
            buttons.append(self.Button(self.loc2px(choice), 'choice', is_target))
        self.buttons = np.asarray(buttons, dtype=object)

    def _touch_handler(self, event, touch):
        if event == self.ts_press_event:
            self.last_touch_tmst = self.logger.log_touch(self.px2loc([touch.x, touch.y]))
            for idx, button in enumerate(self.buttons):
                if self.buttons[idx].is_pressed(touch):
                    self.buttons[idx].tmst = self.last_touch_tmst

    class Button:
        def __init__(self, loc, group='choice', is_target=False, touch_area=(100, 300)):
            self.loc = loc
            self.tmst = 0
            self.touch_area = touch_area
            self.group = group
            self.is_target = is_target

        def is_pressed(self, touch):
            touch_x = self.loc[0] + self.touch_area[0] > touch.x > self.loc[0] - self.touch_area[0]
            touch_y = self.loc[1] + self.touch_area[1] > touch.y > self.loc[1] - self.touch_area[1]
            return touch_x and touch_y


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

    def is_ready(self, duration, since=0):
        if duration == 0:
            return True
        self.__get_events()
        elapsed_time = self.ready_timer.elapsed_time()
        return self.ready and elapsed_time >= duration

    def inactivity_time(self):  # in minutes
        return self.lick_timer.elapsed_time() / 1000 / 60

    def is_licking(self, since=0):
        probe = self.__get_events()
        # reset lick timer if licking is detected &
        if probe > 0:
            self.resp_timer.start()
        self.licked_probe = probe
        return probe

    def is_correct(self):
        return np.any(np.equal(self.licked_probe, self.curr_cond['probe']))

    def prepare(self, condition, choices):
        self.curr_cond = condition
        self.reward_amount = condition['reward_amount']

    def reward(self):
        self.update_history(self.licked_probe, self.reward_amount)
        self.logger.log_liquid(self.licked_probe, self.reward_amount)
        print('Giving Water at probe:%1d' % self.licked_probe)
        return True

    def punish(self):
        print('punishing')
        if self.licked_probe > 0:
            probe = self.licked_probe
        else:
            probe = np.nan
        self.update_history(probe)

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
                elif event.key == pygame.K_SPACE and not self.ready:
                    self.lick_timer.start()
                    self.ready = True
                    print('in position')
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE and self.ready:
                    self.ready = False
                    print('off position')
        return probe
