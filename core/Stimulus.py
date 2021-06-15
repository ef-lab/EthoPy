from core.Experiment import *


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

    cond_tables = []
    required_fields = []
    default_key = dict()

    def setup(self, logger, interface):
        """setup stimulation for presentation before experiment starts"""
        self.logger = logger
        self.interface = interface

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

    def make_conditions(self, conditions, logger):
        """generate and store stimulus condition hashes"""
        for cond in conditions:
            assert np.all([field in cond for field in self.required_fields])
            cond.update({**self.default_key, **cond, 'stimulus_class': self.cond_tables[0]})
        return logger.log_conditions(conditions=conditions,
                                     condition_tables= ['StimCondition'] + self.cond_tables,
                                     schema='stimulus',
                                     hsh='stim_hash')



