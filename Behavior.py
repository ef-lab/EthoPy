from Interface import *
from utils.Timer import *
import pygame
import numpy as np
from datetime import datetime, timedelta


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

    def is_ready(self, init_duration, since=0):
        return True, 0

    def get_response(self, since=0):
        return False

    def get_cond_tables(self):
        return []

    def reward(self):
        return True

    def punish(self):
        pass

    def give_odor(self, delivery_idx, odor_idx, odor_dur, odor_dutycycle):
        pass

    def cleanup(self):
        pass

    def get_cond_tables(self):
        return []

    def prepare(self, condition):
        pass

    def update_history(self, choice=np.nan, reward=np.nan):
        self.choice_history.append(choice)
        self.reward_history.append(reward)
        self.logger.update_setup_info('total_liquid', np.nansum(self.reward_history))

    def is_sleep_time(self):
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0) + self.logger.get_setup_info('start_time')
        stop = now.replace(hour=0, minute=0, second=0) + self.logger.get_setup_info('stop_time')
        if stop < start:
            stop = stop + timedelta(days=1)
        time_restriction = now < start or now > stop
        return time_restriction

    def is_hydrated(self):
        rew = np.nansum(self.reward_history)
        if self.params['max_reward']:
            return rew >= self.params['max_reward']
        else:
            return False


class RPBehavior(Behavior):
    """ This class handles the behavior variables for RP """
    def __init__(self, logger, params):
        self.interface = RPProbe(logger)
        self.cond_tables = ['RewardCond']
        super(RPBehavior, self).__init__(logger, params)

    def get_cond_tables(self):
        return ['RewardCond']

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
        self.logger.log_liquid(self.licked_probe, self.reward_amount[self.licked_probe])
        self.update_history(self.licked_probe, self.reward_amount[self.licked_probe])
        return True

    def give_odor(self, delivery_port, odor_id, odor_dur, odor_dutycycle):
        self.interface.give_odor(delivery_port, odor_id, odor_dur, odor_dutycycle)
        self.logger.log_stim()

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
        self.interface = RPProbe(logger)
        self.ts = TS.Touchscreen()
        self.ts_press_event = TS.TS_PRESS
        self.last_touch_tmst = 0

        for touch in self.ts.touches:
            touch.on_press = self._touch_handler
            touch.on_release = self._touch_handler
        self.ts.run()

    def get_cond_tables(self):
        return ['RewardCond']

    def is_licking(self, since=0):
        licked_probe, tmst = self.interface.get_last_lick()
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
        if tmst >= since: self.resp_timer.start()
        self.has_touched = tmst >= since
        return self.has_touched

    def is_hydrated(self):
        rew = np.nansum(self.reward_history)
        if self.params['max_reward']:
            return rew >= self.params['max_reward']
        else:
            return False

    def get_response(self, since=0):
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
            self.interface.give_liquid(licked_probe)
            self.update_history(self.target_loc, self.reward_amount[licked_probe])
            self.logger.log_liquid(self.licked_probe, self.reward_amount[licked_probe])
            return True
        return False

    def punish(self):
        touched_loc = self.touch if self.has_touched else np.nan
        self.update_history(touched_loc)

    def give_odor(self, delivery_port, odor_id, odor_dur, odor_dutycycle):
        self.interface.give_odor(delivery_port, odor_id, odor_dur, odor_dutycycle)
        self.logger.log_stim()

    def cleanup(self):
        self.interface.cleanup()
        self.ts.stop()

    def prepare(self, condition):
        self.curr_cond = condition
        self.reward_amount = self.interface.calc_pulse_dur(condition['reward_amount'])
        self.target_loc = condition['correct_loc']
        buttons = list()
        buttons.append(self.Button(self.loc2px(condition['ready_loc']), 'ready'))
        for i, loc in enumerate(zip(condition['obj_pos_x'], condition['obj_pos_y'])):
            is_target = True if (condition['correct_loc'] == np.array(loc)).all() else False
            touch_area = condition['touch_area'][i] if 'touch_area' in condition else (100, 300)
            buttons.append(self.Button(self.loc2px(loc), 'choice', is_target, touch_area))
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


class VRBehavior(Behavior):
    def __init__(self, logger, params):
        self.interface = VRProbe(logger)
        self.vr = Ball(params['x_max'], params['y_max'], params['x0'], params['y0'], params['theta0'])
        super(VRBehavior, self).__init__(logger, params)

    def is_licking(self, since=0):
        licked_probe, tmst = self.interface.get_last_lick()
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
            ready, ready_time = self.interface.in_position()
            return ready and ready_time > duration

    def is_correct(self, condition):
        return np.any(np.equal(self.licked_probe, condition['probe']))

    def get_position(self):
        return self.vr.getPosition()

    def reward(self):
        self.update_history(self.licked_probe, self.reward_amount[self.licked_probe])
        self.interface.give_liquid(self.licked_probe)
        self.logger.log_liquid(self.licked_probe, self.reward_amount[self.licked_probe])

    def present_odor(self, delivery_port, odor_id, dutycycle):
        self.interface.present_odor(self, delivery_port, odor_id, dutycycle)
        self.logger.log_stim()

    def update_odor(self, delivery_port, dutycycle):
        self.interface.update_odor(delivery_port, dutycycle)
        self.logger.log_stim()

    def inactivity_time(self):  # in minutes
        return np.minimum(self.interface.timer_probe1.elapsed_time(),
                          self.interface.timer_probe2.elapsed_time()) / 1000 / 60

    def cleanup(self):
        self.mouse1.close()
        self.mouse2.close()
        self.interface.cleanup()

    def prepare(self, condition):
        self.reward_amount = self.interface.calc_pulse_dur(condition['reward_amount'])
        self.loc_x = condition['loc_x']
        self.loc_y = condition['loc_y']
        self.theta = condition['theta']


    class MouseReader():
        def __init__(self, path, dpm=31200):
            self.dpm = dpm
            self.queue = multiprocessing.Queue()
            self.file = open(path, "rb")
            self.thread_end = multiprocessing.Event()
            self.thread_runner = multiprocessing.Process(target=self.reader, args=(self.queue,self.dpm,))
            self.thread_runner.start()

        def reader(self, queue, dpm):
            while not self.thread_end.is_set():
                data = self.file.read(3)  # Reads the 3 bytes
                x, y = struct.unpack("2b", data[1:])
                queue.put({'x': x / dpm, 'y': y / dpm, 'timestamp': time.time()})

        def close(self):
            self.thread_end.set()
            self.thread_runner.join()


class DummyProbe(Behavior):
    def __init__(self, logger, params):
        import pygame
        self.lick_timer = Timer()
        self.lick_timer.start()
        self.ready_timer = Timer()
        self.ready_timer.start()
        self.ready = False
        self.interface = 0
        pygame.init()
        self.screen = pygame.display.set_mode((800, 480))
        super(DummyProbe, self).__init__(logger, params)

    def get_cond_tables(self):
        return ['RewardCond']

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
        self.logger.log_liquid(self.licked_probe, self.reward_amount)
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
                    print(pygame.mouse.get_pos())
            elif event.type == pygame.MOUSEBUTTONDOWN:
                print(pygame.mouse.get_pos())
        return probe
