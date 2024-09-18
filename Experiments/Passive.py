from core.Experiment import *


@experiment.schema
class Condition(dj.Manual):
    class Passive(dj.Part):
        definition = """
        # Passive experiment conditions
        -> Condition
        ---
        intertrial_duration     : int
        """


class Experiment(State, ExperimentClass):
    cond_tables = ['Passive']
    default_key = {'trial_selection'        : 'fixed',
                   'intertrial_duration'    : 100}

    def entry(self):  # updates stateMachine from Database entry - override for timing critical transitions
        self.logger.curr_state = self.name()
        self.state_timer.start()


class Entry(Experiment):
    def entry(self):
        self.stim.prepare

    def next(self):
        return 'PreTrial'


class PreTrial(Experiment):
    def entry(self):
        self.prepare_trial()
        if not self.is_stopped():
            self.stim.prepare(self.curr_cond)
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
        if self.is_stopped():
            return 'Exit'
        elif not self.stim.in_operation:     # timed out
            return 'InterTrial'
        else:
            return 'Trial'

    def exit(self):
        self.stim.stop()


class InterTrial(Experiment):
    def entry(self):
        super().entry()
        if self.stim.curr_cond['intertrial_duration'] > 0:
            self.stim.fill()

    def next(self):
        if self.is_stopped():
            return 'Exit'
        elif self.state_timer.elapsed_time() >= self.stim.curr_cond['intertrial_duration']:
            return 'PreTrial'
        else:
            return 'InterTrial'


class Exit(Experiment):
    def run(self):
        self.stop()
