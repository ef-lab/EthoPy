# -*- coding: utf-8 -*-
import datajoint as dj
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter
import numpy as np
from usefull_functions import none_to_empty
import math 
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
    
    def plot(self):
    
        odor_flag = (len(Trial & OdorCond.Port() & self)>0) # filter trials by hash number of odor
        movie_flag = (len(Trial & MovieCond & self)>0) # filter trials by hash number of movies
        print("movie", movie_flag)
        print("odor", odor_flag)

        # conditions in trials for animal
        conds = Condition & (Trial & self) 
        n_conds = len(conds)
        print('# of conditions: {}'.format(len(conds)))

        # licks for specific animal 
        licksdf = pd.DataFrame(self.fetch())
        
        
        fig, axs = plt.subplots(math.ceil(np.sqrt(n_conds)), math.ceil(np.sqrt(n_conds)), 
                        sharex=True, figsize=(30, 20))
        
        axs = axs.ravel()

        i = 0 # first condition index
        for cond in conds:

            # keep only the trials corresponding to one condition (movie,odor)
            cond_trials = pd.DataFrame((Trial & self & cond) * (Condition))

            # define names (get first values in dict, they are all the same)
            movie_name = cond_trials['cond_tuple'][0].get('movie_name')
            movie_duration = cond_trials['cond_tuple'][0].get('movie_duration')
            dutycycle = cond_trials['cond_tuple'][0].get('dutycycle')
            probe = cond_trials['cond_tuple'][0]['probe']

            # set title color
            if probe == 1:
                title_color = 'red'
            else:
                title_color = 'blue'

            tr_count = 0 # first trial index
            for trial in cond_trials['trial_idx'].unique():

                tr_count +=1 # update trial index

                # get licks of this trial
                lickstmp = licksdf.copy()
                lickstmp['trial_times'] = (lickstmp['time'] > 
                                           (int(cond_trials[cond_trials['trial_idx']==trial]['start_time'])-1000)) # flag True if lick is in the current trial
                lickstmp = lickstmp.loc[lickstmp['trial_times'], :] # keep only the licks that have True flag
                if lickstmp.empty is True:
                    #k += 1
                    continue # if no lick is in this trial, break and continue to the next for, (next trial)
                lickstmp['time'] = lickstmp['time'] - int(cond_trials[cond_trials['trial_idx']==trial]['start_time']) # update time stamp, with reference to trial time

                if 1 in lickstmp['probe'].unique():
                    lp1 = lickstmp.groupby('probe').get_group(1)
                    axs[i].scatter(lp1['time'], np.ones(len(lp1))*tr_count, 
                                   color = 'red', 
                                   marker = '.') # scatter plot the licks for probe 1

                if 2 in lickstmp['probe'].unique():
                    lp2 = lickstmp.groupby('probe').get_group(2)
                    axs[i].scatter(lp2.time, np.ones(len(lp2))*tr_count, 
                                   color = 'blue', 
                                   marker = '.') # scatter plot the licks for probe 2

            #odor = cond_trials[cond_trials['trial_idx'] == trial]['odor_id'].values[0]
            #dutycycle = cond_trials[cond_trials['trial_idx']==trial]['dutycycle'].values[0]

            axs[i].axvline(x=0, color='green', linestyle='-')
            strtitle = ', '.join((none_to_empty(movie_name), none_to_empty(str(dutycycle)), none_to_empty(str(movie_duration)) ))
            axs[i].set_title(strtitle, color = title_color, fontsize = 9)
            axs[i].set_yticks(range(0,tr_count+1,int(math.ceil(tr_count/3))))
            #axs[i].set_xticks(-1000, 4000)

            i +=1 # update fig index
            print('.', end='')


        plt.ylim(0,)            
        plt.xlim(-1000, 4000)
        plt.show()





@schema
class LiquidDelivery(dj.Manual):
    definition = """
    # Liquid delivery timestamps
    -> Session
    time			    : int 	            # time from session start (ms)
    probe               : int               # probe number
    """

    def plot(self, key='all'):
        
        # load dataset
        query = self*Session() 
        
        if key=='all':
            keys = list(range(1,11)) # 11 mice
        else:
            keys = [key]  
            
        
        for k in keys:
            
            # define animal
            liquids = (query & "animal_id = %d" %k).fetch('session_tmst','reward_amount')

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
            plt.title('animal_id: %1d' % k)
            plt.ylim([0,3000])
    
    
#    def plot(self, key='all'):
#        if key == 'all':
#            df = pd.DataFrame((self * Session).fetch())
#        else:
#            df = pd.DataFrame((self * Session & key).fetch())
#
#        df['new_tmst'] = (df['session_tmst'] - pd.Timestamp("1970-01-01")) // pd.Timedelta('1ms')
#        df['new_tmst'] = df['new_tmst'] + df['time']
#        df['new_tmst'] = pd.to_datetime(df['new_tmst'], unit='ms', origin='unix')
#        df['new_tmst'] = df['new_tmst'].dt.date

#        mice = df['animal_id'].unique()  # unique animal ids
#        m_count = df['animal_id'].value_counts()  # count how many times each animal id appears in dataframe
#       t_count = df.groupby(['animal_id'])['new_tmst'].value_counts().sort_index()  # count unique timestamps for each animal id
#        r = 1000
#        #print(df['session_params'][r]['reward_amount'])
#        df['session_params'][r]['reward_amount']
#        df['reward_amount_new'] = np.nan
#        for r in range(len(df)):
#            df['reward_amount_new'][r] = df['session_params'][r]['reward_amount']
#
#        df['total_reward'] = np.nan # pre-allocate
#        kk = 0
#        for idx in mice:
#            for j in range(len(t_count[idx])):
#                df['total_reward'][kk] = t_count[idx][j] * df['reward_amount_new'][kk]
#                kk = kk + t_count[idx][j]
#        df['total_reward'] = df['total_reward'] / 1000  # convert μl to ml
#
#        # plot
#        ymin = df['total_reward'].min()
#        ymax =  df['total_reward'].max()
#        #k = 0
#        for idx in mice:
#            df1 = df[df['animal_id'] == idx].drop_duplicates('new_tmst', keep='first')
#            ax = df1.plot(x='new_tmst', y='total_reward')
#            plt.axhline(y=1, color='r', linestyle='-.')  # minimum liquid intake
#            plt.xticks(rotation=45)
#            plt.ylabel('DeliveredLiquid(ml)')
#            ax.set_title('Animal_id: %1d' % idx)
#            #k = k + m_count[idx]
#            axes = plt.gca()
#            axes.set_ylim([ymin,ymax])
#        return ax


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


