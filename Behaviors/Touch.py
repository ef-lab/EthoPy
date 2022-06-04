from core.Behavior import *
import numpy as np


@behavior.schema
class Touch(Behavior, dj.Manual):
    definition = """
    # This class handles the behavior variables for RP
    ->BehCondition
    """

    class Response(dj.Part):
        definition = """
        # Touch response condition
        -> Touch
        response_loc_x            : float            # response port id
        response_loc_y            : float   
        """

    class Reward(dj.Part):
        definition = """
        # reward port conditions
        -> Touch
        ---
        reward_port               : tinyint          # reward port id
        reward_amount=0           : float            # reward amount
        reward_type               : varchar(16)      # reward type
        """

    cond_tables = ['Touch', 'Touch.Response', 'Touch.Reward']
    required_fields = ['response_loc_x', 'response_loc_y', 'reward_amount']
    default_key = {'reward_type': 'water', 'reward_port': 1}

    def setup(self, exp):
        import ft5406 as TS
        super(Touch, self).setup(exp)
        self.screen_sz = np.array([800, 480])
        self.touch_area = 50  # +/- area in pixels that a touch can occur
        self.since = 0
        self.has_touched = False
        self.logging = True
        self.buttons = list()
        self.loc2px = lambda x: self.screen_sz/2 + np.array(x)*self.screen_sz[0]
        self.px2loc = lambda x: np.array(x)/self.screen_sz[0] - self.screen_sz/2
        self.ts = TS.Touchscreen()
        self.ts_press_event = TS.TS_PRESS
        self.last_touch_tmst = 0

        for touch in self.ts.touches:
            touch.on_press = self._touch_handler
            touch.on_release = self._touch_handler
        self.ts.run()

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
        #if tmst >= since: self.resp_timer.start()
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
        licked_port = self.is_licking(reward=True)
        if np.any(np.equal(licked_port, self.curr_cond['probe'])):
            self.interface.give_liquid(licked_port)
            self.log_reward(self.reward_amount[self.licked_port])
            self.update_history(self.licked_port, self.reward_amount[self.licked_port])
            return True
        return False

    def punish(self):
        touched_loc = self.touch if self.has_touched else np.nan
        self.update_history(touched_loc, punish=True)

    def exit(self):
        super().exit()
        self.interface.cleanup()
        self.ts.stop()

    def prepare(self, condition):
        self.curr_cond = condition
        self.reward_amount = self.interface.calc_pulse_dur(condition['reward_amount'])
        self.target_loc = condition['correct_loc']
        buttons = list()
        buttons.append(self.Button(self.loc2px(condition['ready_loc']), 'ready',self.screen_sz))
        for i, loc in enumerate(zip(condition['obj_pos_x'], condition['obj_pos_y'])):
            is_target = True if (condition['correct_loc'] == np.array(loc)).all() else False
            touch_area = condition['touch_area'][i] if 'touch_area' in condition else (100, 300)
            buttons.append(self.Button(self.loc2px(loc), 'choice', self.screen_sz, is_target, touch_area))
        self.buttons = np.asarray(buttons, dtype=object)

    def _touch_handler(self, event, touch):
        if event == self.ts_press_event:
            loc = self.px2loc([touch.x, self.screen_sz[1] - touch.y])
            self.last_touch_tmst = self.logger.log('Touch', dict(loc_x=loc[0], loc_y=loc[1]))
            for idx, button in enumerate(self.buttons):
                if self.buttons[idx].is_pressed(touch):
                    self.buttons[idx].tmst = self.last_touch_tmst

    class Button:
        def __init__(self, loc, group='choice', screen_sz=(800, 480), is_target=False, touch_area=(100, 300)):
            self.loc = loc
            self.screen_sz = screen_sz
            self.tmst = 0
            self.touch_area = touch_area
            self.group = group
            self.is_target = is_target

        def is_pressed(self, touch):
            touch_x = self.loc[0] + self.touch_area[0]/2 > touch.x > self.loc[0] - self.touch_area[0]/2
            touch_y = self.loc[1] + self.touch_area[1]/2 > self.screen_sz[1] - touch.y > self.loc[1] - self.touch_area[1]/2
            return touch_x and touch_y

