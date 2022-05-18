from datetime import datetime, timedelta
from core.Experiment import *
from core.Interface import *
from matplotlib import cm
import matplotlib.pyplot as plt
import bisect
from importlib import import_module
from dataclasses import dataclass, fields
from dataclasses import field as datafield


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

    def plot(self):
        liquids = (self * experiment.Session()).fetch('session_tmst', 'reward_amount')

        # convert timestamps to dates
        tstmps = liquids[0].tolist()
        dates = [d.date() for d in tstmps]

        # find first index for plot, i.e. for last 15 days
        last_date = dates[-1]
        starting_date = last_date - timedelta(days=15)  # keep only last 15 days
        starting_idx = bisect.bisect_right(dates, starting_date)

        # keep only 15 last days
        # construct the list of tuples (date,reward)
        dates_ = dates[starting_idx:]  # lick dates, for last 15 days
        liqs_ = liquids[1][starting_idx:].tolist()  # lick rewards for last 15 days
        tuples_list = list(zip(dates_, liqs_))

        # construct tuples (unique_date, total_reward_per_day)
        dates_liqs_unique = [(dt, sum(v for d, v in grp)) for dt, grp in itertools.groupby(tuples_list,
                                                                                           key=lambda x: x[0])]
        print('last date: {}, amount: {}'.format(dates_liqs_unique[-1][0], dates_liqs_unique[-1][1]))

        dates_to_plot = [tpls[0] for tpls in dates_liqs_unique]
        liqs_to_plot = [tpls[1] for tpls in dates_liqs_unique]

        # plot
        plt.figure(figsize=(9, 3))
        plt.plot(dates_to_plot, liqs_to_plot)
        plt.ylabel('liquid (microl)')
        plt.xlabel('date')
        plt.xticks(rotation=45)
        plt.ylim([0, 3000])


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

        def plot(self, **kwargs):
            params = {'range': (0, 1000),
                      'bins': 100, **kwargs}
            d = np.diff(self.fetch('time'))
            plt.hist(d, params['bins'], range=params['range'])

    class Lick(dj.Part):
        definition = """
        # Lick timestamps
        -> Activity
        port                 : tinyint          # port id
        time	     	  	 : int           	# time from session start (ms)
        """

        def plot(self, **kwargs):
            params = {'port_colors': ['red', 'blue'],  # set function parameters with defaults
                      'xlim': [-500, 10000],
                      'figsize': (15, 15),
                      'dotsize': 4, **kwargs}
            
            key = {"animal_id" : np.unique(self.fetch('animal_id'))[0],
                   "session" : np.unique(self.fetch('session'))[0]}

            conds = ((Trial & key)).getGroups()  # conditions in trials for animal
            
            fig, axs = plt.subplots(round(len(conds) ** .5), -(-len(conds) // round(len(conds) ** .5)),
                                    sharex=True, figsize=params['figsize'])

            for idx, cond in enumerate(conds):  # iterate through conditions
                selected_trials = (self.proj(ltime = 'time') * (((Trial & key) - Trial.Aborted()) & cond)).proj(ltime = 'ltime - time')
                trials, ports, times = selected_trials.fetch('trial_idx', 'port', 'ltime', order_by='trial_idx')
                un_trials, idx_trials = np.unique(trials, return_inverse=True)  # get unique trials
                axs.item(idx).scatter(times, idx_trials, params['dotsize'],  # plot all of them
                                      c=np.array(params['port_colors'])[ports - 1])
                axs.item(idx).axvline(x=0, color='green', linestyle='-')

                name = f'Object: {cond[0][5]}, Response Port: {cond[0][8]}'
                #perf = len(np.unique((selected_trials & f'port = {cond[0][8]}').fetch('trial_idx')))/len(un_trials)
                perf = len(Trial & selected_trials & Rewards.proj(rtime = 'time'))/len(un_trials)
                title = f'{name}, Performance:{perf:.2f}'

                axs.item(idx).set_title(title, color=np.array(params['port_colors'])[cond[0][8] - 1],
                                        fontsize=9)
                axs.item(idx).invert_yaxis()
            plt.xlim(params['xlim'])
            plt.show()

    class Touch(dj.Part):
        definition = """
        # Touch timestamps
        -> Activity
        loc_x               : int               # x touch location
        loc_y               : int               # y touch location
        time	     	    : int           	# time from session start (ms)
        """

    class Position(dj.Part):
        definition = """
        # 2D possition timestamps
        -> Activity
        loc_x               : float               # x 2d location
        loc_y               : float               # y 2d location
        theta               : float               # direction in space
        time	     	    : int           	# time from session start (ms)
        """


@behavior.schema
class Configuration(dj.Manual):
    definition = """
    # Session behavior configuration info
    -> experiment.Session
    """

    class Port(dj.Part):
        definition = """
        # Probe identity
        -> Configuration
        port                     : tinyint                      # port id
        type="Lick"              : varchar                      # port type
        ---
        ready=0                  : tinyint                      # ready flag
        response=0               : tinyint                      # response flag
        reward=0                 : tinyint                      # reward flag
        discription              : varchar(256)
        """

    class Ball(dj.Part):
        definition = """
        # Ball information
        -> Configuration
        ---
        ball_radius=0.125        : float                   # in meters
        material="styrofoam"     : varchar(64)             # ball material
        coupling="bearings"      : enum('bearings','air')  # mechanical coupling
        discription              : varchar(256)
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
    # Liquid delivery calibration sessions for each port with water availability
    setup                        : varchar(256)                 # Setup name
    port                         : tinyint                      # port id
    date                         : date                         # session date (only one per day is allowed)
    """

    class Liquid(dj.Part):
        definition = """
        # Data for volume per pulse duty cycle estimation
        -> PortCalibration
        pulse_dur                    : int                  # duration of pulse in ms
        ---
        pulse_num                    : int                  # number of pulses
        weight                       : float                # weight of total liquid released in gr
        timestamp=CURRENT_TIMESTAMP  : timestamp            # timestamp
        pressure=0                   : float                # air pressure (PSI)
        """

    class Test(dj.Part):
        definition = """
        # Lick timestamps
        setup                        : varchar(256)                 # Setup name
        port                         : tinyint                      # port id
        timestamp=CURRENT_TIMESTAMP  : timestamp  
        ___
        result=null                  : enum('Passed','Failed')
        pulses=null                  : int
        """

    def plot(self):
        colors = cm.get_cmap('nipy_spectral', len(self))
        for idx, key in enumerate(self):
            d, n, w = (PortCalibration.Liquid() & key).fetch('pulse_dur', 'pulse_num', 'weight')
            plt.plot(d, (w / n) * 1000, label=(key['setup'] + ' #' + str(key['probe'])),c=colors(idx))
            plt.legend(loc=1)
            plt.xlabel('Time (ms)')
            plt.ylabel('Liquid(uL)')


class Behavior:
    """ This class handles the behavior variables """
    cond_tables, interface, required_fields, curr_cond, response, licked_port, logging = [], [], [], [], [], 0, False
    default_key, reward_amount, choice_history, reward_history, last_response = dict(), dict(), list(), list(), []

    def setup(self, exp):
        interface_module = (experiment.SetupConfiguration & {'setup_conf_idx': exp.params['setup_conf_idx']}
                            ).fetch('interface')[0]
        interface = getattr(import_module(f'Interfaces.{interface_module}'), interface_module)
        self.interface = interface(exp=exp, beh=self)
        self.params = exp.params
        self.exp = exp
        self.logger = exp.logger
        self.choices = np.array(np.empty(0))
        self.choice_history = list()  # History term for bias calculation
        self.reward_history = list()  # History term for performance calculation
        self.reward_amount = dict()
        self.interface.load_calibration()
        self.response, self.last_response, self.last_lick = Activity(), Activity(), Activity()
        self.logging = True

    def is_ready(self, init_duration, since=0):
        return True, 0

    def get_response(self, since=0, clear=True):
        response = self.last_response
        if clear:
            self.response = Activity()
            self.last_response = Activity()
            self.licked_port = 0
        if response.time and response.time >= since and response.port:
            self.response = response
            return True
        return False

    def is_licking(self, since=0, reward=False):
        if self.last_lick.time >= since and self.last_lick.port:
            if not reward or (reward and self.last_lick.reward):
                self.licked_port = self.last_lick.port
        else:
            self.licked_port = 0
        return self.licked_port

    def reward(self):
        return True

    def punish(self):
        pass

    def exit(self):
        self.logging = False

    def log_activity(self, activity_key):
        activity = Activity(**activity_key)
        lg_tmst = self.logger.logger_timer.elapsed_time()
        if not activity.time: activity.time = lg_tmst
        key = {**self.logger.trial_key, **activity.__dict__}
        if self.exp.running and self.logging:
            self.logger.log('Activity', key, schema='behavior', priority=10)
            self.logger.log('Activity.' + activity.type, key, schema='behavior')
        if activity.response: self.last_response = activity
        if activity.type == 'Lick': self.last_lick = activity; self.licked_port = activity.port
        return key['time']

    def log_reward(self, reward_amount):
        if isinstance(self.curr_cond['reward_port'], list):
            self.curr_cond['reward_port'] = [self.licked_port]
            self.curr_cond['response_port'] = [self.licked_port]
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
        self.curr_cond = condition
        self.reward_amount = self.interface.calc_pulse_dur(condition['reward_amount'])
        self.logger.log('BehCondition.Trial', dict(beh_hash=self.curr_cond['beh_hash']),
                        schema='behavior')

    def update_history(self, choice=np.nan, reward=np.nan):
        if np.isnan(choice) and self.response.time > 0: choice = self.response.port
        self.choice_history.append(choice)
        self.reward_history.append(reward)
        self.logger.total_reward = np.nansum(self.reward_history)

    def get_false_history(self, h=10):
        idx = np.logical_and(np.isnan(self.reward_history), ~np.isnan(self.choice_history))
        return np.sum(np.cumprod(np.flip(idx[-h:], axis=0)))

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


@dataclass
class Activity:
    port: int = datafield(compare=True, default=0, hash=True)
    type: str = datafield(compare=True, default='', hash=True)
    time: int = datafield(compare=False, default=0)
    in_position: int = datafield(compare=False, default=0)
    loc_x: int = datafield(compare=False, default=0)
    loc_y: int = datafield(compare=False, default=0)
    theta: int = datafield(compare=False, default=0)
    ready: bool = datafield(compare=False, default=False)
    reward: bool = datafield(compare=False, default=False)
    response: bool = datafield(compare=False, default=False)

    def __init__(self, **kwargs):
        names = set([f.name for f in fields(self)])
        for k, v in kwargs.items():
            if k in names: setattr(self, k, v)
