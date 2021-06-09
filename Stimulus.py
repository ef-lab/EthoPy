from Experiment import *
stimulus = dj.create_virtual_module('stimuli', 'test_stimuli', create_tables=True)


@stimulus.schema
class StimCondition(dj.Manual):
    definition = """
    # This class handles the stimulus presentation use function overrides for each stimulus class
    stim_hash            : char(24)                     # unique stimulus condition hash  
    """

    class Trial(dj.Part):
        definition = """
        # Stimulus onset timestamps
        -> Trial
        -> StimCondition
        time                 : int                          # start time from session start (ms)
        ---
        period=NULL          : varchar(64)
        end_time=NULL        : int                          # end time from session start (ms)
        """


class Stimulus:
    """ This class handles the stimulus presentation use function overrides for each stimulus class """

    def make_conditions(self, conditions):
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



