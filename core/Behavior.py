from datetime import datetime, timedelta
from core.Experiment import *


@behavior.schema
class Rewards(dj.Manual):
    definition = """
    # reward trials
    -> experiment.Trial   
    time			        : int 	           # time from session start (ms)
    ---
    reward_type             : varchar(16)
    reward_amount           : float            # reward amount
    """


@behavior.schema
class Activity(dj.Manual):
    definition = """
    # Mouse behavioral response
    -> experiment.Trial  
    """

    class Proximity(dj.Part):
        definition = """
        # Center port information
        -> Activity
        port                 : tinyint          # port id
        time	     	  	 : int           	# time from session start (ms)
        ---
        in_position          : tinyint
        """

    class Lick(dj.Part):
        definition = """
        # Lick timestamps
        -> Activity
        port                 : tinyint          # port id
        time	     	  	 : int           	# time from session start (ms)
        """

    class Touch(dj.Part):
        definition = """
        # Touch timestamps
        -> Activity
        loc_x               : int               # x touch location
        loc_y               : int               # y touch location
        time	     	    : int           	# time from session start (ms)
        """


@behavior.schema
class BehCondition(dj.Manual):
    definition = """
    # reward probe conditions
    beh_hash               : char(24)                     # unique reward hash
    """

    class Trial(dj.Part):
        definition = """
        # movie clip conditions
        -> experiment.Trial
        -> BehCondition
        time			      : int 	                # time from session start (ms)
        """


@behavior.schema
class PortCalibration(dj.Manual):
    definition = """
    # Liquid deliver y calibration sessions for each port with water availability
    setup                        : varchar(256)                 # Setup name
    port                         : tinyint                      # port id
    date                         : date                         # session date (only one per day is allowed)
    ---
    pressure                     : float 
    """

    class Liquid(dj.Part):
        definition = """
        # Data for volume per pulse duty cycle estimation
        -> PortCalibration
        pulse_dur                : int                  # duration of pulse in ms
        ---
        pulse_num                : int                  # number of pulses
        weight                   : float                # weight of total liquid released in gr
        timestamp                : timestamp            # timestamp
        """

    class Test(dj.Part):
        definition = """
        # Lick timestamps
        setup                 : varchar(256)                 # Setup name
        port                  : tinyint                      # port id
        timestamp             : timestamp  
        ___
        result=null           : enum('Passed','Failed')
        pulses=null           : int
        """


class Behavior:
    """ This class handles the behavior variables """
    cond_tables, interface, required_fields, curr_cond = [], [], [], []
    default_key = dict()

    def setup(self, exp):
        self.params = exp.params
        self.resp_timer = Timer()
        self.resp_timer.start()
        self.exp = exp
        self.logger = exp.logger
        self.rew_probe = 0
        self.choices = np.array(np.empty(0))
        self.choice_history = list()  # History term for bias calculation
        self.reward_history = list()  # History term for performance calculation
        self.licked_probe = 0
        self.reward_amount = dict()
        if self.interface: self.interface.load_calibration()

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

    def exit(self):
        pass

    def log_activity(self, table, key):
        key.update({'time': self.logger.logger_timer.elapsed_time(), **self.logger.trial_key})
        self.logger.log('Activity', key, schema='behavior', priority=5)
        self.logger.log('Activity.' + table, key, schema='behavior')

    def log_reward(self, reward_amount):
        self.logger.log('Rewards', {**self.curr_cond, 'reward_amount': reward_amount}, schema='behavior')

    def make_conditions(self, conditions):
        """generate and store stimulus condition hashes"""
        if self.cond_tables:
            for cond in conditions:
                assert np.all([field in cond for field in self.required_fields])
                cond.update({**self.default_key, **cond, 'behavior_class': self.cond_tables[0]})
            return dict(conditions=conditions, condition_tables=['BehCondition'] + self.cond_tables,
                        schema='behavior', hsh='beh_hash')
        else:
            for cond in conditions:
                cond.update({**self.default_key, **cond, 'behavior_class': 'None'})
            return dict(conditions=conditions, condition_tables=[], schema='behavior')

    def prepare(self, condition):
        pass

    def update_history(self, choice=np.nan, reward=np.nan):
        self.choice_history.append(choice)
        self.reward_history.append(reward)
        self.logger.total_reward = np.nansum(self.reward_history)

    def get_false_history(self, h=10):
        idx = np.logical_and(np.isnan(self.reward_history), ~np.isnan(self.choice_history))
        return np.sum(np.cumprod(np.flip(idx[-h:])))

    def is_sleep_time(self):
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0) + self.logger.setup_info['start_time']
        stop = now.replace(hour=0, minute=0, second=0) + self.logger.setup_info['stop_time']
        if stop < start:
            stop = stop + timedelta(days=1)
        time_restriction = now < start or now > stop
        return time_restriction

    def is_hydrated(self, rew=False):
        if rew:
            return self.logger.total_reward >= rew
        elif self.params['max_reward']:
            return self.logger.total_reward >= self.params['max_reward']
        else:
            return False





