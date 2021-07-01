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

    cond_tables, required_fields, default_key = [], [], dict()

    def setup(self, exp):
        """setup stimulation for presentation before experiment starts"""
        self.logger = exp.logger
        self.exp = exp

    def prepare(self, condition=False):
        """prepares stuff for presentation before trial starts"""
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

    def exit(self):
        """exit stimulus stuff"""
        pass

    def set_intensity(self):
        intensity = self.logger.get(schema='experiment', table='SetupConfiguration.Screen')
        if self.logger.is_pi:
            cmd = 'echo %d > /sys/class/backlight/rpi_backlight/brightness' % intensity
            os.system(cmd)

    def make_conditions(self, exp, conditions):
        """generate and store stimulus condition hashes"""
        conditions = factorize(conditions)
        for cond in conditions:
            assert np.all([field in cond for field in self.required_fields])
            if 'trial_period' not in cond: cond['trial_period'] = 'Trial'
            cond.update({**self.default_key, **cond, 'stimulus_class': self.cond_tables[0]})
        if self.__class__.__name__ not in exp.stims:
            exp.stims[self.__class__.__name__] = self
            exp.stims[self.__class__.__name__].setup(exp)
        return exp.log_conditions(conditions, schema='stimulus', hsh='stim_hash',
                                    condition_tables=['StimCondition'] + self.cond_tables)

