from core.Behavior import *


@behavior.schema
class Response(dj.Manual):
    definition = """
    # Mouse behavioral response
    -> Session  
    """

    class Lick(dj.Part):
        definition = """
        # Lick timestamps
        -> Response
        port_id              : tinyint          # port id
        time	     	  	 : int           	# time from session start (ms)
        """

    class Touch(dj.Part):
        definition = """
        # Touch timestamps
        -> Response
        loc_x               : int               # x touch location
        loc_y               : int               # y touch location
        time	     	    : int           	# time from session start (ms)
        """


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
            self.logger.log('LiquidDelivery', dict(probe=self.licked_probe,
                                                   reward_amount=self.reward_amount[self.licked_probe]))
            return True
        return False

    def punish(self):
        touched_loc = self.touch if self.has_touched else np.nan
        self.update_history(touched_loc)

    def cleanup(self):
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
            buttons.append(self.Button(self.loc2px(loc), 'choice',self.screen_sz, is_target, touch_area))
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

