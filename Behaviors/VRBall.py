from core.Behavior import *


class VRBehavior(Behavior):
    def __init__(self, logger, params):
        self.interface = VRProbe(logger)
        super(VRBehavior, self).__init__(logger, params)

    def prepare(self, condition):
        self.reward_amount = self.interface.calc_pulse_dur(condition['reward_amount'])
        self.vr = Ball(condition['x_max'], condition['y_max'], condition['x0'], condition['y0'], condition['theta0'])
        self.loc_x0 = condition['loc_x0']
        self.loc_y0 = condition['loc_y0']
        self.theta0 = condition['theta0']

    def is_licking(self, since=0):
        licked_probe, tmst = self.interface.get_last_lick()
        if tmst >= since and licked_probe:
            self.licked_probe = licked_probe
            self.resp_timer.start()
        else:
            self.licked_probe = 0
        return self.licked_probe

    def is_ready(self):
        x, y = self.get_position()
        in_position = any(((self.resp_loc_x - x)**2 + (self.resp_loc_y - y)**2)**.5 < self.radius)
        return in_position

    def is_correct(self, condition):
        x, y = self.get_position()
        in_position = ((self.correct_loc[0] - x)**2 + (self.correct_loc[1] - y)**2)**.5 < self.radius
        return in_position

    def get_position(self):
        return self.vr.getPosition()

    def reward(self):
        self.interface.give_liquid(self.licked_probe)
        self.update_history(self.licked_probe, self.reward_amount[self.licked_probe])
        self.logger.log('LiquidDelivery', dict(probe=self.licked_probe,
                                               reward_amount=self.reward_amount[self.licked_probe]))

    def cleanup(self):
        self.mouse1.close()
        self.mouse2.close()
        self.interface.cleanup()

