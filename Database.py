import datajoint as dj

schema = dj.schema('lab_behavior')
MovieTables = dj.create_virtual_module('movies.py', 'pipeline_stimulus')


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
    state="ready"        : enum('ready','running','stopped','sleeping','offtime') 
    animal_id=null       : int                          # animal id
    task_idx=null        : int                          # task identification number
    last_ping=null       : timestamp                    
    notes=null           : varchar(256)                 
    current_session=null : int                          
    last_trial=null      : int                          
    total_liquid=null    : float     
    """


@schema
class Task(dj.Lookup):
    definition = """
    # Behavioral experiment parameters
    task_idx             : int                          # task identification number
    ---
    protocol             : varchar(4095)                # stimuli to be presented (array of dictionaries)
    description=""       : varchar(2048)                # task description
    timestamp=null       : timestamp    
    """


@schema
class OdorIdentity(dj.Lookup):
    definition = """
    # Odor identity information
    odor_idx: int                                       # odor index
    ---
    odor_name: char(128)                                # odor name
    odor_concentration = 100: int                       # odor concentration (%)
    """


@schema
class Session(dj.Manual):
    definition = """
    # Behavior session info
    animal_id            : int                          # animal id
    session_id           : smallint                     # session number
    ---
    setup=null           : varchar(256)                 # computer id
    session_tmst=null    : timestamp                    # session timestamp
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
    ---
    cond_idx             : smallint                     # unique condition index
    trial_idx            : smallint                     # unique condition index
    start_time           : int                          # start time from session start (ms)
    end_time             : int                          # end time from session start (ms)
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


@schema
class StimDelivery(dj.Manual):
    definition = """
    # Liquid delivery timestamps
    -> Session
    time			    : int 	            # time from session start (ms)
    """


@schema
class MovieCond(dj.Manual):
    definition = """
    # movie clip conditions
    -> Condition
    ---
    -> movies.Movie.Clip
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
    # reward probe conditions
    -> Condition
    ---
    odor_idx             : tinyblob                     # odor index for odor identity
    duration             : tinyblob                     # odor duration (ms)
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
        timestamp=null           : timestamp            # timestamp
        """
