from core.Experiment import *


@experiment.schema
class Condition(dj.Manual):
    class Passive(dj.Part):
        definition = """
        # Passive experiment conditions
        -> Condition
        ---
        trial_selection='fixed' : enum('fixed','random','randperm') 
    
        intertrial_duration     : int
        """


class Experiment(State, ExperimentClass):
    cond_tables = ['Passive']
    default_key = {'trial_selection'       : 'fixed',

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
        print(self)
        print('pretrial entry')
        self.prepare_trial()
        print('after prepare trial')
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
        print('trial entry')
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
    def entry(self):
        print('intertrial entry')
        super().entry()

    def next(self):
        if self.is_stopped():
            return 'Exit'
        elif self.state_timer.elapsed_time() >= self.stim.curr_cond['intertrial_duration']:
            return 'PreTrial'
        else:
            return 'InterTrial'
    def exit(self):
        self.stim.unshow()

class Exit(Experiment):
    def run(self):
        self.beh.exit()
        self.stim.exit()
        self.logger.ping(0)
