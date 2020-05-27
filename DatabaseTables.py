import datajoint as dj

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
class OdorIdentity(dj.Lookup):
    definition = """
    # Odor identity information
    odor_idx               : int                       # odor index
    ---
    odor_name=NULL         : varchar(128)              # odor name
    odor_concentration=100 : int                       # odor concentration in prc
    odor_description=NULL  : varchar(256)
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
    """


@schema
class Condition(dj.Manual):
    definition = """
    # unique stimulus conditions
    -> Session
    cond_idx             : smallint                     # unique condition index
    ---
    """


@schema
class Trial(dj.Manual):
    definition = """
    # Trial information
    -> Session
    trial_idx            : smallint                     # unique condition index
    ---
    cond_idx             : smallint                     # unique condition index
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


@schema
class Lick(dj.Manual):
    definition = """
    # Lick timestamps
    -> Session
    time	     	  	: int           	# time from session start (ms)
    probe               : int               # probe number
    """


@schema
class LiquidDelivery(dj.Manual):
    definition = """
    # Liquid delivery timestamps
    -> Session
    time			    : int 	            # time from session start (ms)
    probe               : int               # probe number
    """

    def plot(self, key='all'):
        if key == 'all':
            df = pd.DataFrame((self * Session).fetch())
        else:
            df = pd.DataFrame((self * Session & key).fetch())

            df['new_tmst'] = (df['session_tmst'] - pd.Timestamp("1970-01-01")) // pd.Timedelta('1ms')
            df['new_tmst'] = df['new_tmst'] + df['time']
            df['new_tmst'] = pd.to_datetime(df['new_tmst'], unit='ms', origin='unix')
            df['new_tmst'] = df['new_tmst'].dt.date

            mice = df['animal_id'].unique()  # unique animal ids
            m_count = df['animal_id'].value_counts()  # count how many times each animal id appears in dataframe
            t_count = df.groupby(['animal_id'])[
                'new_tmst'].value_counts().sort_index()  # count unique timestamps for each animal id
            for r in range(len(df)):
                df['reward_amount'] = df['session_params'][r]['reward_amount']

            df['total_reward'] = np.nan
            kk = 0
            for idx in mice:
                for j in range(len(t_count[idx])):
                    df['total_reward'][kk] = t_count[idx][j] * df['reward_amount'][kk]
                    kk = kk + t_count[idx][j]
            df['total_reward'] = df['total_reward'] / 1000  # convert μl to ml

            # plot
            k = 0
            for idx in mice:
                df1 = df[df['animal_id'] == idx].drop_duplicates('new_tmst', keep='first')
                ax = df1.plot(x='new_tmst', y='total_reward')
                plt.axhline(y=1, color='r', linestyle='-.')  # minimum liquid intake
                plt.xticks(rotation=45)
                plt.ylabel('DeliveredLiquid(ml)')
                ax.set_title('Animal_id: %1d' % idx)
                k = k + m_count[idx]


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
    """


@schema
class RewardCond(dj.Manual):
    definition = """
    # reward probe conditions
    -> Condition
    ---
    probe=0        :int                                 # probe number
    """


@schema
class OdorCond(dj.Manual):
    definition = """
    # odor conditions
    -> Condition
    ---
    odor_idx             : tinyblob                     # odor index for odor identity
    odor_duration             : int                     # odor duration (ms)
    dutycycle            : tinyblob                     # odor dutycycle
    delivery_idx         : tinyblob                     # delivery idx for channel mapping
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


@schema
class MouseWeight(dj.Manual):
    definition = """
    # Weight of the animal
    animal_id                    : int # animal id
    timestamp=CURRENT_TIMESTAMP  : timestamp
    ---
    weight                       : float # in grams
    """

    def plot(self, key='all'):
        if key == 'all':
            mw = pd.DataFrame((self).fetch())
        else:
            mw = pd.DataFrame((self & key).fetch())

        mice = mw['animal_id'].unique()
        m_count = mw['animal_id'].value_counts()
        k = 0
        for idx in mice:
            w0 = mw[mw['animal_id'] == idx].at[k, 'weight']
            ax = mw[mw['animal_id'] == idx].plot(x='timestamp', y='weight')
            ax.axhline(0.7 * w0, linestyle='--', color='red', label="30%")
            ax.axhline(0.8 * w0, linestyle='--', color='pink', label='20%')
            ax.axhline(0.9 * w0, linestyle='--', color='green', label='10%')
            plt.xticks(rotation=45)
            plt.ylabel('Mouse Weight (gr)')
            plt.xlabel('Time')
            date_form = DateFormatter("%d-%m-%y")
            ax.xaxis.set_major_formatter(date_form)
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
            ax.set_title('Animal_id: %1d' % idx)
            k = k + m_count[idx]
        return ax
