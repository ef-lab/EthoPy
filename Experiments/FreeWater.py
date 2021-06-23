from core.Experiment import *


@experiment.schema
class FreeWater(dj.Manual):
    definition = """
    # Passive experiment conditions
    -> Condition
    """

    class SessionParams(dj.Part):
        definition = """
        # Match2Sample experiment conditions 
        -> Match2Sample
        ---
        trial_selection='staircase': enum('fixed','random','staircase','biased') 
        max_reward=3000            : smallint
        min_reward=500             : smallint
        bias_window=5              : smallint
        staircase_window=20        : smallint
        stair_up=0.7               : float
        stair_down=0.55            : float
        noresponse_intertrial=1    : tinyint(1)
        """

    class TrialParams(dj.Part):
        definition = """
        # Match2Sample experiment conditions
        -> Match2Sample
        ---
        difficulty            : int   
        init_ready            : int
        delay_ready           : int 
        intertrial_duration   : int
        trial_duration        : int
        delay_duration        : int
        reward_duration       : int
        punish_duration       : int
        abort_duration        : int 
        """


class Experiment(State, ExperimentClass):
    cond_tables = ['Passive', 'Passive.SessionParams', 'Passive.TrialParams']
    required_fields = ['difficulty']
    default_key = {'trial_selection'     : 'staircase',
                   'max_reward'            : 3000,
                   'min_reward'            : 500,
                   'bias_window'           : 5,
                   'staircase_window'      : 20,
                   'stair_up'              : 0.7,
                   'stair_down'            : 0.55,
                   'noresponse_intertrial' : True,
                   'incremental_punishment': True,

                   'init_ready'             : 0,
                   'cue_ready'              : 0,
                   'delay_ready'            : 0,
                   'resp_ready'             : 0,
                   'intertrial_duration'    : 1000,
                   'cue_duration'           : 1000,
                   'delay_duration'         : 0,
                   'response_duration'      : 5000,
                   'reward_duration'        : 2000,
                   'punish_duration'        : 1000,
                   'abort_duration'         : 0}

    def entry(self):  # updates stateMachine from Database entry - override for timing critical transitions
        self.logger.curr_state = self.name()
        self.start_time = self.logger.log('Trial.StateOnset', {'state': self.name()})
        self.resp_ready = False
        self.state_timer.start()


class Prepare(Experiment):
    def run(self):
        self.stim.setup()  # prepare stimulus

    def next(self):
        if self.beh.is_sleep_time():
            return 'Offtime'
        else:
            return 'PreTrial'


class PreTrial(Experiment):
    def entry(self):
        self.prepare_trial()
        self.stim.prepare(self.curr_cond)
        self.beh.prepare(self.curr_cond)
        super().entry()
        if not self.curr_cond: self.logger.update_setup_info({'status': 'stop'})

    def run(self):
        if self.beh.is_ready(self.curr_cond['init_ready'], self.start_time):
            self.resp_ready = True
        self.logger.ping()

    def next(self):
        if self.logger.setup_status in ['stop', 'exit'] or not self.curr_cond:
            return 'Exit'
        elif self.resp_ready:
            return 'Trial'
        else:
            return 'PreTrial'


class Trial(Experiment):
    def entry(self):
        super().entry()
        self.stim.start()
        self.trial_start = self.logger.init_trial(self.curr_cond['cond_hash'])

    def run(self):
        self.stim.present()  # Start Stimulus
        self.response = self.beh.get_response(self.trial_start)
        if self.beh.is_ready(self.stim.curr_cond['delay_duration'], self.trial_start):
            self.resp_ready = True
            self.stim.ready_stim()

    def next(self):
        if not self.resp_ready and self.response:                           # did not wait
            return 'Abort'
        elif self.response and self.beh.is_correct():  # response to correct probe
            return 'Reward'
        elif self.timer.elapsed_time() > self.stim.curr_cond['trial_duration']:      # timed out
            return 'InterTrial'
        else:
            return 'Trial'

    def exit(self):
        self.logger.log_trial()
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

    def run(self):
        self.rewarded = self.beh.reward()

    def next(self):
        if self.rewarded or self.state_timer.elapsed_time() >= self.curr_cond['reward_duration']:
            return 'InterTrial'
        elif self.logger.setup_status in ['stop', 'exit']:
            return 'Exit'
        else:
            return 'Reward'


class InterTrial(Experiment):
    def run(self):
        if self.beh.get_response(self.period_start) & self.params.get('noresponse_intertrial'):
            self.state_timer.start()

    def next(self):
        if self.logger.setup_status in ['stop', 'exit']:
            return 'Exit'
        elif self.beh.is_sleep_time() and not self.beh.is_hydrated(self.params['min_reward']):
            return 'Hydrate'
        elif self.beh.is_hydrated():
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
        if self.logger.setup_status in ['stop', 'exit']:  # if wake up then update session
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
        if self.logger.setup_status in ['stop', 'exit']:  # if wake up then update session
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
        self.beh.cleanup()
        self.stim.close()
        self.logger.ping(0)
