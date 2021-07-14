from core.Experiment import *


@experiment.schema
class Navigate(dj.Manual):
    definition = """
    # Navigation experiment conditions
    -> Condition
    ---
    trial_selection='staircase' : enum('fixed','random','staircase','biased') 
    bias_window=5               : smallint
    staircase_window=20         : smallint
    stair_up=0.7                : float
    stair_down=0.55             : float
    noresponse_intertrial=1     : tinyint(1)
    norun_response=1            : tinyint(1)
    incremental_punishment=1    : tinyint(1)

    difficulty                  : int   
    trial_ready                 : int
    trial_duration              : int
    intertrial_duration         : int
    reward_duration             : int
    punish_duration             : int
    """


class Experiment(State, ExperimentClass):
    cond_tables = ['Navigate']
    required_fields = []
    default_key = {'trial_selection'       : 'staircase',
                   'bias_window'           : 5,
                   'staircase_window'      : 20,
                   'stair_up'              : 0.7,
                   'stair_down'            : 0.55,
                   'noresponse_intertrial' : True,
                   'norun_response'        : True,
                   'incremental_punishment': True,

                   'difficulty'             : 0,
                   'trial_ready'            : 0,
                   'intertrial_duration'    : 1000,
                   'trial_duration'         : 1000,
                   'reward_duration'        : 2000,
                   'punish_duration'        : 1000}

    def entry(self):  # updates stateMachine from Database entry - override for timing critical transitions
        self.logger.curr_state = self.name()
        self.start_time = self.logger.log('Trial.StateOnset', {'state': self.name()})
        self.resp_ready = False
        self.state_timer.start()


class Entry(Experiment):
    def entry(self):
        pass

    def next(self):
        if self.is_stopped():
            return 'Exit'
        else:
            return 'PreTrial'


class PreTrial(Experiment):
    def entry(self):
        self.prepare_trial()
        self.beh.prepare(self.curr_cond)
        self.stim.prepare(self.curr_cond)
        self.logger.ping()
        super().entry()

    def next(self):
        if self.is_stopped():
            return 'Exit'
        else:
            return 'Trial'


class Trial(Experiment):
    def entry(self):
        super().entry()
        self.stim.start()

    def run(self):
        self.stim.present()
        self.response = self.beh.is_licking(self.start_time)
        time.sleep(.1)

    def next(self):
        if self.response and self.beh.is_correct() and not self.beh.is_running():  # correct response
            return 'Reward'
        elif not self.beh.is_ready() and self.response:
            return 'Abort'
        elif self.response and self.beh.is_ready():  # incorrect response
            return 'Punish'
        elif self.state_timer.elapsed_time() > self.stim.curr_cond['trial_duration']:  # timed out
            return 'InterTrial'
        elif self.is_stopped():
            return 'Exit'
        else:
            return 'Trial'

    def exit(self):
        self.stim.stop()
        self.logger.ping()


class Abort(Experiment):
    def run(self):
        self.beh.update_history()
        self.logger.log('AbortedTrial')

    def next(self):
        return 'InterTrial'


class Reward(Experiment):
    def run(self):
        self.beh.reward()

    def next(self):
        return 'InterTrial'


class Punish(Experiment):
    def entry(self):
        self.beh.punish()
        super().entry()

    def run(self):
        self.stim.punish_stim()

    def next(self):
        if self.state_timer.elapsed_time() >= self.stim.curr_cond['punish_duration']:
            return 'InterTrial'
        else:
            return 'Punish'

    def exit(self):
        self.stim.unshow()


class InterTrial(Experiment):
    def entry(self):
        self.logger.log_trial()
        super().entry()

    def run(self):
        if self.beh.get_response(self.start_time) & self.params.get('noresponse_intertrial'):
            self.state_timer.start()

    def next(self):
        if self.is_stopped():
            return 'Exit'
        elif self.state_timer.elapsed_time() >= self.stim.curr_cond['intertrial_duration']:
            return 'PreTrial'
        elif not self.is_running:
            return 'Pretrial'
        else:
            return 'InterTrial'


class Exit(Experiment):
    def run(self):
        self.beh.exit()
        if self.stim:
            self.stim.exit()
        self.logger.ping(0)