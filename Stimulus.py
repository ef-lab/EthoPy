import datajoint as dj
stimulus = dj.create_virtual_module('stimuli', 'test_stimuli', create_tables=True)


@stimulus.schema
class RewardCond(dj.Manual):
    definition = """
    # reward probe conditions
    -> Condition
    ---
    probe=0              :int                           # probe number
    reward_amount=0      :int                           # reward amount
    """


@stimulus.schema
class LiquidDelivery(dj.Manual):
    definition = """
    # Liquid delivery timestamps
    -> Session
    time			    : int 	            # time from session start (ms)
    probe               : int               # probe number
    """


@stimulus.schema
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
class ProbeTest(dj.Manual):
    definition = """
    # Lick timestamps
    setup                 : varchar(256)                 # Setup name
    probe                 : int               # probe number
    timestamp             : timestamp  
    ___
    result=null           : enum('Passed','Failed')
    pulses=null           : int
    """


class Stimulus:
    """ This class handles the stimulus presentation
    use function overrides for each stimulus class
    """
    def __init__(self, logger):
        self.logger = logger
        self.isrunning = False

    def get_cond_tables(self):
        """return condition tables"""
        return []

    def setup(self):
        """setup stimulation for presentation before experiment starts"""
        pass

    def prepare(self, conditions=False):
        """prepares stuff for presentation before trial starts"""
        pass

    def init(self, cond=False):
        """initialize stuff for each trial"""
        pass

    def ready_stim(self):
        """Stim Cue for ready"""
        pass

    def reward_stim(self):
        """Stim Cue for reward"""
        pass

    def punish_stim(self):
        """Stim Cue for punishment"""
        pass

    def present(self):
        """trial presentation method"""
        pass

    def stop(self):
        """stop trial"""
        pass

