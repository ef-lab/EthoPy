from core.Experiment import *


@experiment.schema
class Passive(dj.Manual):
    definition = """
    # Passive experiment conditions
    -> Condition
    """

    class SessionParams(dj.Part):
        definition = """
        # Passive experiment conditions
        -> Passive
        ---
        trial_selection='fixed'    : enum('fixed','random') 
        """

    class TrialParams(dj.Part):
        definition = """
        # Match2Sample experiment conditions
        -> Passive
        ---
        intertrial_duration   : int
        """


class Experiment(State, ExperimentClass):
    cond_tables = ['Passive', 'Passive.SessionParams', 'Passive.TrialParams']
    default_key = {'trial_selection'       : 'fixed',

                   'intertrial_duration'    : 1000}

    def entry(self):  # updates stateMachine from Database entry - override for timing critical transitions
        self.logger.curr_state = self.name()
        self.start_time = self.logger.log('Trial.StateOnset', {'state': self.name()})
        self.state_timer.start()


class Entry(Experiment):
    def entry(self):
        self.stim.setup()  # prepare stimulus

    def next(self):
        return 'PreTrial'


class PreTrial(Experiment):
    def entry(self):
        self.prepare_trial()
        if not self.is_stopped():
            self.stim.prepare(self.curr_cond)
        else:
            self.logger.update_setup_info({'status': 'stop'})
        super().entry()

    def next(self):
        if self.is_stopped():  # if run out of conditions exit
            return 'Exit'
        else:
            return 'Trial'


class Trial(Experiment):
    def entry(self):
        self.stim.start()
        super().entry()

    def run(self):
        self.stim.present()  # Start Stimulus

    def next(self):
        if not self.stim.isrunning:     # timed out
            return 'InterTrial'
        else:
            return 'Trial'

    def exit(self):
        self.stim.stop()
        self.logger.ping()


class InterTrial(Experiment):
    def next(self):
        if self.is_stopped():
            return 'Exit'
        elif self.state_timer.elapsed_time() >= self.stim.curr_cond['intertrial_duration']:
            return 'PreTrial'
        else:
            return 'InterTrial'


class Exit(Experiment):
    def run(self):
        self.beh.exit()
        self.stim.exit()
        self.logger.ping(0)
