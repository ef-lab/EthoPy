from core.Experiment import *
import os


@stimulus.schema
class Configuration(dj.Manual):
    definition = """
    # Session stimulus configuration info
    -> experiment.Session
    """

    class Screen(dj.Part):
        definition = """
        # Screen information
        -> Configuration
        screen_idx               : tinyint
        ---
        intensity                : tinyint UNSIGNED 
        monitor_distance         : float
        monitor_center_x         : float
        monitor_center_y         : float
        monitor_aspect           : float
        monitor_size             : float
        fps                      : tinyint UNSIGNED
        resolution_x             : smallint
        resolution_y             : smallint
        discription              : varchar(256)
        """

    class Speaker(dj.Part):
        definition = """
        # Speaker information
        speaker_idx             : tinyint
        -> Configuration
        ---
        sound_freq=10000        : int           # in Hz
        duration=500            : int           # in ms
        volume=50               : tinyint       # 0-100 percentage
        discription             : varchar(256)
        """


@stimulus.schema
class StimCondition(dj.Manual):
    definition = """
    # This class handles the stimulus presentation use function overrides for each stimulus class
    stim_hash            : char(24)                     # unique stimulus condition hash  
    """

    class Trial(dj.Part):
        definition = """
        # Stimulus onset timestamps
        -> experiment.Trial
        period='Trial'       : varchar(16)
        ---
        -> StimCondition
        start_time           : int                          # start time from session start (ms)
        end_time=NULL        : int                          # end time from session start (ms)
        """


class Stimulus:
    """ This class handles the stimulus presentation use function overrides for each stimulus class """

    cond_tables, required_fields, default_key, curr_cond, conditions, timer = [], [], dict(), dict(), [], Timer()
    period, isrunning, flip_count = 'Trial', False, 0

    def init(self, exp):
        """store parent objects """
        self.logger = exp.logger
        self.exp = exp
        screen_properties = self.logger.get(table='SetupConfiguration.Screen', key=self.exp.params, as_dict=True)
        if np.size(screen_properties) > 0:
            self.monitor = screen_properties[0]
            if self.logger.is_pi:
                cmd = 'echo %d > /sys/class/backlight/rpi_backlight/brightness' % self.monitor['intensity']
                os.system(cmd)
                exp.interface.setup_touch_exit()

    def setup(self):
        """setup stimulation for presentation before experiment starts"""
        pass

    def prepare(self, curr_cond=False, stim_period=''):
        """prepares stuff for presentation before trial starts"""
        self.curr_cond = curr_cond if stim_period == '' else curr_cond[stim_period]
        self.period = stim_period

    def start(self):
        """start stimulus"""
        self.isrunning = True
        self.log_start()
        self.timer.start()

    def present(self):
        """stimulus presentation method"""
        pass

    def unshow(self, color=False):
        """stimulus hidding method"""
        pass

    def stop(self):
        """stop stimulus"""
        self.log_stop()
        self.isrunning = False

    def exit(self):
        """exit stimulus stuff"""
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

    def log_start(self):
        """Start time logging"""
        self.start_time = self.logger.logger_timer.elapsed_time()
        self.exp.interface.sync_out(True)

    def log_stop(self):
        """Log stimulus condition start & stop time"""
        stop_time = self.logger.logger_timer.elapsed_time()
        self.exp.interface.sync_out(False)
        self.logger.log('StimCondition.Trial', dict(period=self.period, stim_hash=self.curr_cond['stim_hash'],
                                                    start_time=self.start_time, end_time=stop_time), schema='stimulus')

    def make_conditions(self, conditions=[]):
        """generate and store stimulus condition hashes"""
        for cond in conditions:
            assert np.all([field in cond for field in self.required_fields])
            cond.update({**self.default_key, **cond})
        conditions = self.exp.log_conditions(conditions, schema='stimulus', hsh='stim_hash',
                                       condition_tables=['StimCondition'] + self.cond_tables)
        self.conditions += conditions
        return conditions

