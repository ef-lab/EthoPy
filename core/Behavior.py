from datetime import datetime, timedelta
from core.Experiment import *
from matplotlib import cm
import matplotlib.pyplot as plt
import bisect


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
            params = {'probe_colors': ['red', 'blue'],  # set function parameters with defaults
                      'xlim': [-500, 3000],
                      'figsize': (15, 15),
                      'dotsize': 4, **kwargs}
            conds = (Condition() & self).getGroups()  # conditions in trials for animal
            fig, axs = plt.subplots(round(len(conds) ** .5), -(-len(conds) // round(len(conds) ** .5)),
                                    sharex=True, figsize=params['figsize'])

            for idx, cond in enumerate(conds):  # iterate through conditions
                selected_trials = (Lick * (self - AbortedTrial) & (Condition & cond)).proj(  # select trials with licks
                    selected='(time <= end_time) AND (time >= start_time)') & 'selected > 0'
                trials, probes, times = ((Lick * (self & selected_trials)).proj(  # get licks for all trials
                    trial_time='time-start_time') & ('(trial_time>{}) AND (trial_time<{})'.format(
                    params['xlim'][0], params['xlim'][1]))).fetch('trial_idx', 'probe', 'trial_time', order_by='time')
                un_trials, idx_trials = np.unique(trials, return_inverse=True)  # get unique trials

                axs.item(idx).scatter(times, idx_trials, params['dotsize'],  # plot all of them
                                      c=np.array(params['probe_colors'])[probes - 1])
                axs.item(idx).axvline(x=0, color='green', linestyle='-')

                if np.unique(cond['obj_duration'])[0]:
                    name = 'Obj:{}'.format(np.unique((ObjectCond & cond).fetch('obj_id')))
                elif np.unique(cond['movie_duration'])[0] and np.unique(cond['odor_duration'])[0]:
                    name = 'Mov:%s  Odor:%d' % (np.unique((MovieCond & cond).fetch('movie_name'))[0],
                                                np.unique(cond['dutycycle'])[0])
                elif np.unique(cond['movie_duration'])[0]:
                    name = 'Mov:{}'.format(np.unique((MovieCond & cond).fetch('movie_name'))[0])
                elif np.unique(cond['odor_duration'])[0]:
                    name = 'Odor:{}'.format(np.unique(cond['dutycycle'])[0])

                selected_pd = pd.DataFrame(selected_trials.fetch(order_by=('trial_idx', 'time')))
                selected_pd.drop_duplicates(subset=["trial_idx"], keep='first', inplace=True)
                name = '{} p:{:.2f}'.format(name, np.nanmean(selected_pd['probe'] == np.unique(cond['probe'])[0]))

                axs.item(idx).set_title(name, color=np.array(params['probe_colors'])[np.unique(cond['probe'])[0] - 1],
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
        if isinstance(self.curr_cond['reward_port'], list):
            self.curr_cond['reward_port'] = [self.licked_probe]
            self.curr_cond['response_port'] = [self.licked_probe]
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





