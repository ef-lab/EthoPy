import os

import datajoint as dj
import numpy as np

# import experiment needs in definition of Configuration and Trial tables
from core.Logger import experiment, stimulus
from utils.helper_functions import DictStruct
from utils.Presenter import Presenter
from utils.Timer import Timer


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
        distance         : float
        center_x         : float
        center_y         : float
        aspect           : float
        size             : float
        fps                      : tinyint UNSIGNED
        resolution_x             : smallint
        resolution_y             : smallint
        description              : varchar(256)
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
    period, in_operation, flip_count, photodiode, rec_fliptimes = 'Trial', False, 0, False, False
    fill_colors = DictStruct({'start': [], 'ready': [], 'reward': [], 'punish': [], 'background': (0, 0, 0)})

    def init(self, exp):
        """store parent objects """
        self.logger = exp.logger
        self.exp = exp
        screen_properties = self.logger.get(table='SetupConfiguration.Screen', key=self.exp.params, as_dict=True)
        self.monitor = DictStruct(screen_properties[0])
        if self.logger.is_pi:
            cmd = 'echo %d > /sys/class/backlight/rpi_backlight/brightness' % self.monitor.intensity
            os.system(cmd)
            exp.interface.setup_touch_exit()

    def setup(self):
        """setup stimulation for presentation before experiment starts"""
        self.Presenter = Presenter(self.logger, self.monitor, background_color=self.fill_colors.background,
                                   photodiode=self.photodiode, rec_fliptimes=self.rec_fliptimes)

    def prepare(self, curr_cond=False, stim_period=''):
        """prepares stuff for presentation before trial starts"""
        self.curr_cond = curr_cond if stim_period == '' else curr_cond[stim_period]
        self.period = stim_period

    def start(self):
        """start stimulus"""
        self.in_operation = True
        self.log_start()
        self.timer.start()

    def present(self):
        """stimulus presentation method"""
        pass

    def fill(self, color=False):
        """stimulus hidding method"""
        if not color:
            color = self.fill_colors.background
        if self.fill_colors.background: self.Presenter.fill(color)

    def stop(self):
        """stop stimulus"""
        self.fill()
        self.log_stop()
        self.in_operation = False

    def exit(self):
        """exit stimulus stuff"""
        self.Presenter.quit()

    def ready_stim(self):
        """Stim Cue for ready"""
        if self.fill_colors.ready: self.fill(self.fill_colors.ready)

    def reward_stim(self):
        """Stim Cue for reward"""
        if self.fill_colors.reward: self.fill(self.fill_colors.reward)

    def punish_stim(self):
        """Stim Cue for punishment"""
        if self.fill_colors.punish: self.fill(self.fill_colors.punish)

    def start_stim(self):
        """Stim Cue for start"""
        if self.fill_colors.start: self.fill(self.fill_colors.start)

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

    def name(self):
        return type(self).__name__
