from core.Experiment import *


@experiment.schema
class MatchPort(dj.Manual):
    definition = """
    # 2AFC experiment conditions
    -> Condition
    ---
    trial_selection='staircase' : enum('fixed','random','staircase','biased') 
    max_reward=3000             : smallint
    min_reward=500              : smallint
    bias_window=5               : smallint
    staircase_window=20         : smallint
    stair_up=0.7                : float
    stair_down=0.55             : float
    noresponse_intertrial=1     : tinyint(1)
    incremental_punishment=1    : tinyint(1)
    
    difficulty                  : int   
    init_ready                  : int
    trial_ready                 : int
    intertrial_duration         : int
    trial_duration              : int
    response_duration           : int
    reward_duration             : int
    punish_duration             : int
    """


class Experiment(State, ExperimentClass):
    cond_tables = ['MatchPort']
    required_fields = ['difficulty']
    default_key = {'trial_selection': 'staircase',
                   'max_reward': 3000,
                   'min_reward': 500,
                   'bias_window': 5,
                   'staircase_window': 20,
                   'stair_up': 0.7,
                   'stair_down': 0.55,
                   'noresponse_intertrial': True,
                   'incremental_punishment': True,

                   'init_ready': 0,
                   'trial_ready': 0,
                   'intertrial_duration': 1000,
                   'tial_duration': 1000,
                   'response_duration': 5000,
                   'reward_duration': 2000,
                   'punish_duration': 1000}

    def entry(self):  # updates stateMachine from Database entry - override for timing critical transitions
        self.logger.curr_state = self.name()
        self.start_time = self.logger.log('Trial.StateOnset', {'state': self.name()})
        self.resp_ready = False
        self.state_timer.start()


class Entry(Experiment):
    def run(self):
        pass

    def next(self):
        if self.logger.setup_status in ['stop', 'exit']:
            return 'Exit'
        elif self.beh.is_sleep_time():
            return 'Offtime'
        else:
            return 'PreTrial'


class PreTrial(Experiment):
    def entry(self):
        self.prepare_trial()
        self.stim.prepare(self.curr_cond)
        self.beh.prepare(self.curr_cond)
        super().entry()

    def run(self):
        if not self.is_stopped() and self.beh.is_ready(self.curr_cond['init_ready'], self.start_time):
            self.resp_ready = True

    def next(self):
        if self.is_stopped():
            return 'Exit'
        elif self.resp_ready:
            return 'Trial'
        else:
            return 'PreTrial'


class Trial(Experiment):
    def entry(self):
        self.resp_ready = False
        super().entry()
        self.stim.start()

    def run(self):
        self.stim.present()  # Start Stimulus
        self.logger.ping()
        self.response = self.beh.get_response(self.trial_start)
        if self.beh.is_ready(self.stim.curr_cond['trial_ready'], self.trial_start):
            self.resp_ready = True
            self.stim.ready_stim()

    def next(self):
        if not self.resp_ready and self.response:          # did not wait
            return 'Abort'
        elif self.response and not self.beh.is_correct():  # response to incorrect probe
            return 'Punish'
        elif self.response and self.beh.is_correct():      # response to correct probe
            return 'Reward'
        elif self.state_timer.elapsed_time() > self.stim.curr_cond['trial_duration']:      # timed out
            return 'Abort'
        elif self.is_stopped():
            return 'Exit'
        else:
            return 'Trial'

    def exit(self):
        self.stim.stop()  # stop stimulus when timeout
        self.logger.ping()


class Abort(Experiment):
    def run(self):
        self.beh.update_history()
        self.logger.log('Trial.Aborted')

    def next(self):
        return 'InterTrial'


class Reward(Experiment):
    def run(self):
        self.stim.reward_stim()
        self.beh.reward()

    def next(self):
        return 'InterTrial'


class Punish(Experiment):
    def entry(self):
        self.beh.punish()
        super().entry()
        self.punish_period = self.stim.curr_cond['punish_duration']
        if self.params.get('incremental_punishment'):
            self.punish_period *= self.beh.get_false_history()

    def run(self):
        self.stim.punish_stim()

    def next(self):
        if self.state_timer.elapsed_time() >= self.punish_period:
            return 'InterTrial'
        else:
            return 'Punish'

    def exit(self):
        self.stim.unshow()


class InterTrial(Experiment):
    def run(self):
        if self.beh.get_response(self.start_time) & self.params.get('noresponse_intertrial'):
            self.state_timer.start()

    def next(self):
        if self.is_stopped():
            return 'Exit'
        elif self.beh.is_sleep_time() and not self.beh.is_hydrated(self.params['min_reward']):
            return 'Hydrate'
        elif self.beh.is_sleep_time() or self.beh.is_hydrated():
            return 'Offtime'
        elif self.state_timer.elapsed_time() >= self.stim.curr_cond['intertrial_duration']:
            return 'PreTrial'
        else:
            return 'InterTrial'


class Hydrate(Experiment):
    def run(self):
        if self.beh.get_response():
            self.beh.reward()
            time.sleep(1)
        self.logger.ping()

    def next(self):
        if self.is_stopped():  # if wake up then update session
            return 'Exit'
        elif self.beh.is_hydrated(self.params['min_reward']) or not self.beh.is_sleep_time():
            return 'Offtime'
        else:
            return 'Hydrate'


class Offtime(Experiment):
    def entry(self):
        super().entry()
        self.stim.unshow([0, 0, 0])

    def run(self):
        if self.logger.setup_status not in ['sleeping', 'wakeup'] and self.beh.is_sleep_time():
            self.logger.update_setup_info({'status': 'sleeping'})
        self.logger.ping()
        time.sleep(1)

    def next(self):
        if self.is_stopped():  # if wake up then update session
            return 'Exit'
        elif self.logger.setup_status == 'wakeup' and not self.beh.is_sleep_time():
            return 'PreTrial'
        elif self.logger.setup_status == 'sleeping' and not self.beh.is_sleep_time():  # if wake up then update session
            return 'Exit'
        elif not self.beh.is_hydrated() and not self.beh.is_sleep_time():
            return 'Exit'
        else:
            return 'Offtime'

    def exit(self):
        if self.logger.setup_status in ['wakeup', 'sleeping']:
            self.logger.update_setup_info({'status': 'running'})


class Exit(Experiment):
    def run(self):
        self.beh.exit()
        if self.stim:
            self.stim.exit()
        self.logger.ping(0)
