# -*- coding: utf-8 -*-
import datajoint as dj
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import bisect
import itertools

schema = dj.schema('lab_behavior')
MovieTables = dj.create_virtual_module('movies.py', 'lab_stimuli')
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

    def plotDifficulty(self, **kwargs):
        # parameters
        params = {'probe_colors': np.array([[1, 0, 0], [0, .5, 1]]), 'trial_bins': 10, 'range': 0.9, **kwargs}

        def plot_trials(trials, **kwargs):
            conds, trial_idxs = ((Trial & trials) * Condition()).fetch('cond_tuple', 'trial_idx')
            offset = ((trial_idxs - 1) % params['trial_bins'] - params['trial_bins'] / 2) * params['range'] * 0.1
            difficulties = [cond['difficulty'] for cond in conds]
            plt.scatter(trial_idxs, difficulties + offset, zorder=10, **kwargs)

        for key in Session() & self:
            # correct trials
            correct_trials = ((LiquidDelivery * Trial & key).proj(
                selected='(time - end_time)<100 AND (time - end_time)>0') & 'selected > 0')

            # missed trials
            incorrect_trials = ((Lick * Trial & key).proj(
                selected='(time <= end_time) AND (time > start_time)') & 'selected > 0') - (Trial() & correct_trials)

            # incorrect trials
            missed_trials = ((Trial - correct_trials & key) - incorrect_trials).proj()

            # plot trials
            fig = plt.figure(figsize=(10, 4), tight_layout=True)
            plot_trials(correct_trials, s=4, c=params['probe_colors'][correct_trials.fetch('probe') - 1])
            plot_trials(incorrect_trials, s=4, marker='o', facecolors='none', edgecolors=[.3, .3, .3], linewidths=.5)
            plot_trials(missed_trials, s=.1, c=[[0, 0, 0]])

            # plot info
            plt.xlabel('Trials')
            plt.ylabel('Difficulty')
            plt.title('Animal:%d  Session:%d' % (key['animal_id'], key['session']))
            plt.ylim((0.4, 3.6))
            plt.xlim((-1, 1400))
            plt.yticks((1, 2, 3))
            plt.gca().xaxis.set_ticks_position('none')
            plt.gca().yaxis.set_ticks_position('none')
            plt.box(False)
            plt.show()


@schema
class Condition(dj.Manual):
    definition = """
    # unique stimulus conditions
    cond_hash             : char(24)                 # unique condition hash
    ---
    cond_tuple=null        : blob      
    """


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
         
    def filter_cp(self):
        
        cp_df = pd.DataFrame(self.fetch())
        cp_df['change'] = cp_df['in_position'].diff()
        cp_df = cp_df.dropna()
        cp_df = cp_df.astype({'change': 'int32'})
        cp_df_filtered = cp_df[np.abs(cp_df['change']) == 1]
        result = cp_df_filtered.loc[cp_df_filtered.groupby('animal_id').timestamp.idxmax(),:]
        
        return result

@schema
class Lick(dj.Manual):
    definition = """
    # Lick timestamps
    -> Session
    time	     	  	: int           	# time from session start (ms)
    probe               : int               # probe number
    """
    
    def plot(self, **kwargs):
        params = {'probe_colors':['red','blue'], # set function parameters with defaults
                  'xlim':[-500, 3000], **kwargs}
        conds = Condition() & (Trial() & self) # conditions in trials for animal
        fig, axs = plt.subplots(round(len(conds)**.5), -(-len(conds)//round(len(conds)**.5)),
                                sharex=True, figsize=(30, 20))
        for idx, cond in enumerate(conds): #  iterate through conditions
            trials, probes, times = ((Lick * Trial & cond).proj( # get licks for all trials of one condition
                trial_time='time-start_time') & ('(trial_time>%d) AND (trial_time<%d)' % (params['xlim']))).\
                fetch('trial_idx', 'probe', 'trial_time')
            axs.item(idx).scatter(times, range(1,len(trials)), 2, c=params['probe_colors'][probes-1]) # plot all of them
            axs.item(idx).axvline(x=0, color='green', linestyle='-')
            axs.item(idx).set_title('Mov:%s Odor:%s \n %s   %s' % (str(cond['cond_tuple'].get('movie_name')),
                str(cond['cond_tuple'].get('dutycycle')), str(cond['cond_tuple'].get('movie_duration')),
                str(cond['cond_tuple'].get('odor_duration'))),
                               color=params['probe_colors'][cond['cond_tuple']['probe']-1], fontsize=9)
            axs.item(idx).set_yticks(range(0, len(trials) + 1, len(trials)//3))
        plt.ylim(0, )
        plt.xlim(params['xlim'])
        plt.show()


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


