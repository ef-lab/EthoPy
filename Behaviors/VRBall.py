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

    cond_tables = ['VRBall', 'VRBall.Response', 'VRBall.Reward']
    required_fields = ['x0', 'y0', 'radius', 'response_loc_y', 'response_loc_x',
                       'reward_loc_x', 'reward_loc_y', 'reward_amount']
    default_key = {'reward_type': 'water', 'speed_thr': 0.025,
                   'response_port': 1, 'reward_port': 1, 'theta0': 0}

    def setup(self, exp):
        self.previous_x = 0
        self.previous_y = 0
        self.resp_loc_x = None
        self.resp_loc_y = None
        self.interface = VRProbe(exp=exp)
        super(VRBall, self).setup(exp)
        self.vr = Ball(exp)
        self.flag = True

    def prepare(self, condition):
        if condition['x0'] < 0 or condition['y0'] < 0:
            x0, y0, theta0, time = self.vr.getPosition()
            self.vr.setPosition(condition['x_sz'], condition['y_sz'], x0, y0, theta0)
        else:
            self.vr.setPosition(condition['x_sz'], condition['y_sz'], condition['x0'], condition['y0'],
                                condition['theta0'])
        super().prepare(condition)

    def is_ready(self):
        x, y, theta, tmst = self.get_position()
        in_position = False
        for r_x, r_y in zip(self.curr_cond['response_loc_x'], self.curr_cond['response_loc_y']):
            in_position = in_position or np.sum((np.array([r_x, r_y]) - [x, y]) ** 2) ** .5 < self.curr_cond['radius']
        return in_position

    def is_running(self):
        return self.vr.getSpeed() > self.curr_cond['speed_thr']

    def is_correct(self):
        x, y, theta, tmst = self.get_position()
        cor_loc = np.array([self.curr_cond['reward_loc_x'], self.curr_cond['reward_loc_y']])
        in_position = np.sum((cor_loc - [x, y]) ** 2) ** .5 < self.curr_cond['radius']
        return in_position

    def new_correct(self):
        x, y, theta, tmst = self.get_position()
        in_position=False
        if self.flag == True:
            print('first time')
            for c_x, c_y in zip(self.curr_cond['response_loc_x'], self.curr_cond['response_loc_y']):
                in_position = np.sum((np.array([c_x, c_y]) - [x, y]) ** 2) ** .5 < self.curr_cond['radius']
                if in_position:
                    self.prev_loc_x = x
                    self.prev_loc_y = y
                    print(self.prev_loc_x, self.prev_loc_y)
                    break
            self.flag=False
        elif not self.flag:
            print('another time')
            for c_x, c_y in zip(self.curr_cond['response_loc_x'], self.curr_cond['response_loc_y']):
                prev_position = np.sum((np.array([c_x, c_y]) - [self.prev_loc_x, self.prev_loc_y]) ** 2) ** .5 < self.curr_cond['radius']
                temp_in_position = np.sum((np.array([c_x, c_y]) - [x, y]) ** 2) ** .5 < self.curr_cond['radius']
                print(x, self.prev_loc_x,y, self.prev_loc_y)
                if temp_in_position and not prev_position:
                    in_position = True
                    self.reward_loc_x = x
                    self.reward_loc_y = y
                    break
        return in_position

    def get_position(self):
        return self.vr.getPosition()

    def reward(self):
        self.interface.give_liquid(self.licked_port)
        self.log_reward(self.reward_amount[self.licked_port])
        self.update_history(self.licked_port, self.reward_amount[self.licked_port])

    def punish(self):
        self.update_history(self.licked_port)

    def exit(self):
        self.vr.cleanup()
        self.interface.cleanup()


