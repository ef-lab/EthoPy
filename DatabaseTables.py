# -*- coding: utf-8 -*-
import datajoint as dj
import matplotlib.pyplot as plt
from matplotlib import cm
import numpy as np
from datetime import datetime, timedelta
import bisect
import itertools

schema = dj.schema('lab_behavior')
Stimuli = dj.create_virtual_module('Stimuli.py', 'lab_stimuli')
Mice = dj.create_virtual_module('mice.py', 'lab_mice')


def erd():
    """for convenience"""
    dj.ERD(schema).draw()


@schema
class SetupControl(dj.Lookup):
    definition = """
    #
    setup                : varchar(256)                 # Setup name
    ---
    ip                   : varchar(16)                  # setup IP address
    status="ready"       : enum('ready','running','stop','sleeping','offtime','exit') 
    animal_id=null       : int                          # animal id
    task_idx=null        : int                          # task identification number
    last_ping            : timestamp                    
    notes=null           : varchar(256)                 
    current_session=null : int                          
    last_trial=null      : int                          
    total_liquid=null    : float     
    state=null           : varchar(256)  
    """


@schema
class Task(dj.Lookup):
    definition = """
    # Behavioral experiment parameters
    task_idx             : int                          # task identification number
    ---
    protocol             : varchar(4095)                # stimuli to be presented (array of dictionaries)
    description=""       : varchar(2048)                # task description
    timestamp            : timestamp    
    """


@schema
class Session(dj.Manual):
    definition = """
    # Behavior session infod
    animal_id            : int                          # animal id
    session              : smallint                     # session number
    ---
    setup=null           : varchar(256)                 # computer id
    session_tmst         : timestamp                    # session timestamp
    notes=null           : varchar(2048)                # session notes
    session_params=null  : mediumblob                   
    conditions=null      : mediumblob      
    protocol=null        : varchar(256)                 # protocol file
    experiment_type=null : varchar(256)                 
    """


@schema
class Condition(dj.Manual):
    definition = """
    # unique stimulus conditions
    cond_hash             : char(24)                 # unique condition hash
    ---
    cond_tuple=null        : blob      
    """

    def getGroups(self):
        odor_flag = (len(Trial & OdorCond.Port() & self) > 0)  # filter trials by hash number of odor
        movie_flag = (len(Trial & MovieCond & self) > 0)  # filter trials by hash number of movies
        if movie_flag and odor_flag:
            conditions = RewardCond() * MovieCond() * (OdorCond.Port() & 'delivery_port=1')\
                         * OdorCond() & (Trial & self)
        elif not movie_flag and odor_flag:
            conditions = (RewardCond() *  (OdorCond.Port() & 'delivery_port=1') * OdorCond() & (Trial & self)).proj(
                movie_duration='0', dutycycle='dutycycle', odor_duration='odor_duration', probe='probe')
        elif movie_flag and not odor_flag:
            conditions = (RewardCond() * MovieCond() & (Trial & self)).proj(
                movie_duration='movie_duration',probe='probe', dutycycle='0', odor_duration='0')
        else:
            return []
        uniq_groups, groups_idx = np.unique(
            [cond.astype(int) for cond in conditions.fetch('movie_duration','dutycycle','odor_duration','probe')],
            axis=1, return_inverse=True)
        conditions = conditions.fetch()
        condition_groups = [conditions[groups_idx == group] for group in set(groups_idx)]
        return condition_groups


@schema
class Trial(dj.Manual):
    definition = """
    # Trial information
    -> Session
    trial_idx            : smallint                     # unique condition index
    ---
    -> Condition
    start_time           : int                          # start time from session start (ms)
    end_time             : int                          # end time from session start (ms)
    """

    def plotLicks(self, **kwargs):
        params = {'probe_colors':['red','blue'],                                # set function parameters with defaults
                  'xlim':[-500, 3000],
                  'figsize':(15, 15),
                  'dotsize': 4, **kwargs}
        conds = (Condition() & self).getGroups()                          # conditions in trials for animal
        fig, axs = plt.subplots(round(len(conds)**.5), -(-len(conds)//round(len(conds)**.5)),
                                sharex=True, figsize=params['figsize'])
        for idx, cond in enumerate(conds):                                                #  iterate through conditions
            selected_trials = (Lick * self & (Condition & cond)).proj(                       # select trials with licks
                selected='(time <= end_time) AND (time > start_time)') & 'selected > 0'
            trials, probes, times = ((Lick * (self & selected_trials)).proj(                 # get licks for all trials
                trial_time='time-start_time') & ('(trial_time>%d) AND (trial_time<%d)' %
                (params['xlim'][0], params['xlim'][1]))).fetch('trial_idx', 'probe', 'trial_time')
            un_trials, idx_trials = np.unique(trials, return_inverse=True)                          # get unique trials
            axs.item(idx).scatter(times, idx_trials, params['dotsize'],                              # plot all of them
                                  c=np.array(params['probe_colors'])[probes-1])
            axs.item(idx).axvline(x=0, color='green', linestyle='-')
            if np.unique(cond['movie_duration'])[0] and np.unique(cond['odor_duration'])[0]:
                name = 'Mov:%s  Odor:%d' % (np.unique((MovieCond & cond).fetch('movie_name'))[0],
                                            np.unique(cond['dutycycle'])[0])
            elif np.unique(cond['movie_duration'])[0]:
                name = 'Mov:%s' % np.unique((MovieCond & cond).fetch('movie_name'))[0]
            elif np.unique(cond['odor_duration'])[0]:
                name = 'Odor:%d' % np.unique(cond['dutycycle'])[0]
            name = '%s p:%.2f' % (name, np.nanmean(selected_trials.fetch('probe')==np.unique(cond['probe'])[0]))
            axs.item(idx).set_title(name, color=np.array(params['probe_colors'])[np.unique(cond['probe'])[0] - 1],
                                    fontsize=9)
            axs.item(idx).invert_yaxis()
        plt.xlim(params['xlim'])
        plt.show()

    def plotDifficulty(self, **kwargs):
        params = {'probe_colors': [[1, 0, 0], [0, .5, 1]],
                  'trial_bins': 10,
                  'range': 0.9,
                  'xlim': (-1,),
                  'ylim': (0.4,), **kwargs}

        def plot_trials(trials, **kwargs):
            conds, trial_idxs = ((Trial & trials) * Condition()).fetch('cond_tuple', 'trial_idx')
            offset = ((trial_idxs - 1) % params['trial_bins'] - params['trial_bins'] / 2) * params['range'] * 0.1
            difficulties = [cond['difficulty'] for cond in conds]
            plt.scatter(trial_idxs, difficulties + offset, zorder=10, **kwargs)

        # correct trials
        correct_trials = ((LiquidDelivery * self).proj(
            selected='(time - end_time)<100 AND (time - end_time)>0') & 'selected > 0')

        # missed trials
        incorrect_trials = ((Lick * self).proj(
            selected='(time <= end_time) AND (time > start_time)') & 'selected > 0') - (self & correct_trials)

        # incorrect trials
        missed_trials = ((self - correct_trials) - incorrect_trials).proj()

        # plot trials
        fig = plt.figure(figsize=(10, 4), tight_layout=True)
        plot_trials(correct_trials, s=4, c=np.array(params['probe_colors'])[correct_trials.fetch('probe') - 1])
        plot_trials(incorrect_trials, s=4, marker='o', facecolors='none', edgecolors=[.3, .3, .3], linewidths=.5)
        plot_trials(missed_trials, s=.1, c=[[0, 0, 0]])

        # plot info
        plt.xlabel('Trials')
        plt.ylabel('Difficulty')
        plt.title('Animal:%d  Session:%d' % (Session() & self).fetch1('animal_id','session'))
        plt.yticks(range(int(min(plt.gca().get_ylim())),int(max(plt.gca().get_ylim()))+1))
        plt.ylim(params['ylim'][0])
        plt.xlim(params['xlim'][0])
        plt.gca().xaxis.set_ticks_position('none')
        plt.gca().yaxis.set_ticks_position('none')
        plt.box(False)
        plt.show()


@schema
class AbortedTrial(dj.Manual):
    definition = """
    # Aborted Trials
    -> Session
    trial_idx            : smallint                     # unique condition index
    """


@schema
class CenterPort(dj.Manual):
    definition = """
    # Center port information
    -> Session
    time	     	   	: int           	# time from session start (ms)
    ---
    in_position          : smallint
    state=null           : varchar(256)  
    timestamp            : timestamp    
    """
         
    def plot(self, **kwargs):
        params = {'range': (0, 1000),
                  'bins': 100, **kwargs}
        d = np.diff(self.fetch('time'))
        plt.hist(d, params['bins'], range=params['range'])


@schema
class Lick(dj.Manual):
    definition = """
    # Lick timestamps
    -> Session
    time	     	  	: int           	# time from session start (ms)
    probe               : int               # probe number
    """


@schema
class Touch(dj.Manual):
    definition = """
    # Lick timestamps
    -> Session
    time	     	  	: int           	# time from session start (ms)
    loc_x               : int               # x touch location
    loc_y               : int               # y touch location
    """


@schema
class LiquidDelivery(dj.Manual):
    definition = """
    # Liquid delivery timestamps
    -> Session
    time			    : int 	            # time from session start (ms)
    probe               : int               # probe number
    """

    def plot(self):
        
        animals =  Mice.Mice() & self

        for animal in animals:

            # define animal
            liquids = (self*Session() & animal).fetch('session_tmst','reward_amount')

            # convert timestamps to dates
            tstmps = liquids[0].tolist()
            dates = [datetime.date(d) for d in tstmps] 
            
            # find first index for plot, i.e. for last 15 days
            last_tmst = liquids[0][-1]
            last_date =  datetime.date(last_tmst)
            starting_date = last_date - timedelta(days=15) # keep only last 15 days
            starting_idx = bisect.bisect_right(dates, starting_date)
            
            # keep only 15 last days 
            # construct the list of tuples (date,reward)
            dates_ = dates[starting_idx:] # lick dates, for last 15 days
            liqs_ = liquids[1][starting_idx:].tolist() # lick rewards for last 15 days
            tuples_list = list(zip(dates_, liqs_))

            # construct tuples (unique_date, total_reward_per_day)
            dates_liqs_unique = [(dt, sum(v for d,v in grp)) for dt, grp in itertools.groupby(tuples_list,
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
            plt.title('animal_id: %d' % animal['animal_id'])
            plt.ylim([0,3000])


@schema
class StimOnset(dj.Manual):
    definition = """
    # Stimulus onset timestamps
    -> Session
    time			    : int 	            # time from session start (ms)
    ---
    period              : enum('Trial','Cue','Response')
    """

@schema
class StateOnset(dj.Manual):
    definition = """
    # Trial period timestamps
    -> Session
    time			    : int 	            # time from session start (ms)
    ---
    state               : enum('Cue','Delay','Response','PreTrial','Trial','InterTrial','Reward','Punish', 'Abort','Sleep','Offtime','Exit')
    """


@schema
class MovieCond(dj.Manual):
    definition = """
    # movie clip conditions
    -> Condition
    ---
    movie_name           : char(8)                      # short movie title
    clip_number          : int                          # clip index
    movie_duration       : int                          # movie duration
    skip_time            : smallint                     # start time in clip
    static_frame         : smallint                     # static frame presentation
    """


@schema
class BarCond(dj.Manual):
    definition = """
    # Fancy Bar stimulus conditions
    -> Condition
    ---
    axis                  : enum('vertical','horizontal')
    bar_width             : float  # degrees
    bar_speed             : float  # degrees/sec
    flash_speed           : float  # cycles/sec
    grat_width            : float  # degrees
    grat_freq             : float
    grid_width            : float
    grit_freq             : float
    style                 : enum('checkerboard', 'grating')
    direction             : float             # 1 for UD LR, -1 for DU RL
    flatness_correction   : smallint    # 1 correct for flatness of monitor, 0 do not
    intertrial_duration   : int
    """

@schema
class ObjectCond(dj.Manual):
    definition = """
    # Object stimuli conditions with Panda3D
    -> Condition
    ---
    background_color      : tinyblob
    ambient_color         : tinyblob
    direct1_color         : tinyblob
    direct1_dir           : tinyblob
    direct2_color         : tinyblob
    direct2_dir           : tinyblob
    obj_id                : blob
    obj_pos_x             : blob
    obj_pos_y             : blob
    obj_mag               : blob
    obj_rot               : blob
    obj_tilt              : blob
    obj_yaw               : blob
    obj_delay             : blob
    obj_dur               : blob
    """

@schema
class RewardCond(dj.Manual):
    definition = """
    # reward probe conditions
    -> Condition
    ---
    probe=0              :int                           # probe number
    reward_amount=0      :int                           # reward amount
    """


@schema
class OdorCond(dj.Manual):
    definition = """
    # odor conditions
    -> Condition
    ---
    odor_duration             : int                     # odor duration (ms)
    """

    class Port(dj.Part):
        definition = """
        # odor conditions
        -> OdorCond
        delivery_port        : int                      # delivery idx for channel mapping
        ---
        odor_id              : int                      # odor index for odor identity
        dutycycle            : int                      # odor dutycycle
        """

@schema
class LiquidCalibration(dj.Manual):
    definition = """
    # Liquid delivery calibration sessions for each probe
    setup                        : varchar(256)         # Setup name
    probe                        : int                  # probe number
    date                         : date                 # session date (only one per day is allowed)
    """

    class PulseWeight(dj.Part):
        definition = """
        # Data for volume per pulse duty cycle estimation
        -> LiquidCalibration
        pulse_dur                : int                  # duration of pulse in ms
        ---
        pulse_num                : int                  # number of pulses
        weight                   : float                # weight of total liquid released in gr
        timestamp                : timestamp            # timestamp
        """

    def plot(self):
        colors = cm.get_cmap('nipy_spectral', len(self))
        for idx, key in enumerate(self):
            d, n, w = (LiquidCalibration.PulseWeight() & key).fetch('pulse_dur', 'pulse_num', 'weight')
            plt.plot(d, (w / n) * 1000, label=(key['setup'] + ' #' + str(key['probe'])),c=colors(idx))
            plt.legend(loc=1)
            plt.xlabel('Time (ms)')
            plt.ylabel('Liquid(uL)')


