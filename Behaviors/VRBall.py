from core.Behavior import *
from core.Interface import *


@behavior.schema
class VRBall(Behavior, dj.Manual):
    definition = """
    # This class handles the behavior variables for RP
    ->BehCondition
    ---
    x_sz                 : float
    y_sz                 : float
    x0                   : float
    y0                   : float            
    theta0               : float
    radius               : float
    speed_thr            : float # in m/sec
    """

    class Response(dj.Part):
        definition = """
        # Lick response condition
        -> VRBall
        response_loc_y            : float            # response y location
        response_loc_x            : float            # response x location
        response_port             : tinyint          # response port id
        """

    class Reward(dj.Part):
        definition = """
        # reward port conditions
        -> VRBall
        ---
        reward_loc_x              : float
        reward_loc_y              : float
        reward_port               : tinyint          # reward port id
        reward_amount=0           : float            # reward amount
        reward_type               : varchar(16)      # reward type
        """

    cond_tables = ['VRBall', 'VRBall.Response', 'VRBall.Reward', 'VRBall.Position']
    required_fields = ['x0', 'y0', 'radius', 'response_loc_y', 'response_loc_x',
                       'reward_loc_x', 'reward_loc_y', 'reward_amount']
    default_key = {'reward_type': 'water', 'speed_thr': 0.025,
                   'response_port': 1, 'reward_port': 1, 'theta0': 0}

    def setup(self, exp):
        self.previous_x = 0
        self.previous_y = 0
        self.resp_loc_x = None
        self.resp_loc_y = None
        self.interface = VRProbe(exp.logger)
        super(VRBall, self).setup(exp)
        source_path = '/home/eflab/Tracking/'
        target_path = '/mnt/lab/data/Tracking/'
        self.vr = Ball(exp.logger, path=source_path, target_path=target_path)
        self.logger.log('Session.Recording', dict(rec_aim='ball', software='PyMouse', version='0.1',
                                                  filename=self.vr.filename, source_path=source_path,
                                                  target_path=target_path), schema='experiment')

    def prepare(self, condition):
        self.vr.setPosition(condition['x_sz'], condition['y_sz'], condition['x0'], condition['y0'], condition['theta0'])
        super().prepare()

    def is_licking(self, since=0):
        licked_probe, tmst = self.interface.get_last_lick()
        if tmst >= since and licked_probe:
            self.licked_probe = licked_probe
            self.resp_timer.start()
        else:
            self.licked_probe = 0
        return self.licked_probe

    def is_ready(self):
        x, y, theta, tmst = self.get_position()
        in_position = any(
            [np.sum((np.array(r) - [x, y]) ** 2) ** .5 < self.curr_cond['radius'] for r in self.curr_cond['resp_loc']])
        return in_position

    def is_running(self):
        return self.vr.getSpeed() > self.curr_cond['speed_thr']

    def is_correct(self):
        x, y, theta, tmst = self.get_position()
        in_position = np.sum((np.array(self.curr_cond['correct_loc']) - [x, y]) ** 2) ** .5 < self.curr_cond['radius']
        return in_position

    def get_position(self):
        return self.vr.getPosition()

    def reward(self):
        self.interface.give_liquid(self.licked_port)
        self.log_reward(self.reward_amount[self.licked_port])
        self.update_history(self.licked_probe, self.reward_amount[self.licked_probe])

    def start_odor(self):
        self.interface.start_odor(0)

    def cleanup(self):
        self.vr.quit()
        self.interface.cleanup()


