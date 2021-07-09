from core.Experiment import *
import os


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
        time                 : int                          # start time from session start (ms)
        ---
        -> StimCondition
        period=NULL          : varchar(64)
        end_time=NULL        : int                          # end time from session start (ms)
        """


class Stimulus:
    """ This class handles the stimulus presentation use function overrides for each stimulus class """

    cond_tables, required_fields, default_key, curr_cond, conditions = [], [], dict(), dict(), []

    def init(self, exp):
        """store parent objects """
        self.logger = exp.logger
        self.exp = exp
        intensity = self.logger.get(schema='experiment', table='SetupConfiguration.Screen')
        if self.logger.is_pi:
            cmd = 'echo %d > /sys/class/backlight/rpi_backlight/brightness' % intensity
            os.system(cmd)

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
        self.logger.log('StimCondition.Trial', dict(period='', stim_hash=self.curr_cond['stim_hash']),
                        schema='stimulus')

    def present(self):
        """stimulus presentation method"""
        pass

    def stop(self):
        """stop stimulus"""
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

    def make_conditions(self, conditions=[]):
        """generate and store stimulus condition hashes"""
        for cond in conditions:
            assert np.all([field in cond for field in self.required_fields])
            cond.update({**self.default_key, **cond})
        conditions = self.exp.log_conditions(conditions, schema='stimulus', hsh='stim_hash',
                                       condition_tables=['StimCondition'] + self.cond_tables)
        self.conditions += conditions
        return conditions

