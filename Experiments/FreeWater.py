from utils.Timer import *
from Experiment import *
from datetime import datetime, timedelta


class State(StateClass):
    def __init__(self, parent=None):
        self.timer = Timer()
        if parent:
            self.__dict__.update(parent.__dict__)

    def setup(self, logger, BehaviorClass, StimulusClass, session_params, conditions):
        self.logger = logger
        self.logger.log_session(session_params, 'FreeWater')
        # Initialize params & Behavior/Stimulus objects
        self.beh = BehaviorClass(self.logger, session_params)
        self.stim = StimulusClass(self.logger, session_params, conditions, self.beh)
        self.params = session_params
        self.logger.log_conditions(conditions, self.stim.get_cond_tables() + self.beh.get_cond_tables())

        # Initialize states
        exitState = Exit(self)
        self.StateMachine = StateMachine(Prepare(self), exitState)
        global states
        states = {
            'PreTrial'     : PreTrial(self),
            'Trial'        : Trial(self),
            'Abort'        : Abort(self),
            'InterTrial'   : InterTrial(self),
            'Reward'       : Reward(self),
            'Offtime'      : Offtime(self),
            'Exit'         : exitState}

    def entry(self):  # updates stateMachine from Database entry - override for timing critical transitions
        self.logger.curr_state = type(self).__name__
        self.period_start = self.logger.log('StateOnset', {'state': type(self).__name__})
        self.timer.start()

    def run(self):
        self.StateMachine.run()


class Prepare(State):
    def run(self):
        self.stim.setup()  # prepare stimulus

    def next(self):
        if self.beh.is_sleep_time():
            return states['Offtime']
        else:
            return states['PreTrial']


class PreTrial(State):
    def entry(self):
        self.stim.prepare()
        if not self.stim.curr_cond:
            self.logger.update_setup_info({'status': 'stop'})
        else:
            self.beh.prepare(self.stim.curr_cond)
        super().entry()

    def run(self):
        self.logger.ping()

    def next(self):
        if self.logger.setup_status in ['stop', 'exit'] or not self.stim.curr_cond:
            return states['Exit']
        elif self.beh.is_ready(self.stim.curr_cond['init_duration']):
            return states['Trial']
        else:
            return states['PreTrial']


class Trial(State):
    def entry(self):
        self.resp_ready = False
        super().entry()
        self.stim.start()
        self.trial_start = self.logger.init_trial(self.stim.curr_cond['cond_hash'])

    def run(self):
        self.stim.present()  # Start Stimulus
        self.response = self.beh.get_response(self.trial_start)
        if self.beh.is_ready(self.stim.curr_cond['delay_duration'], self.trial_start):
            self.resp_ready = True
            self.stim.ready_stim()

    def next(self):
        if not self.resp_ready and self.response:                           # did not wait
            return states['Abort']
        elif self.response and self.beh.is_correct():  # response to correct probe
            return states['Reward']
        elif self.timer.elapsed_time() > self.stim.curr_cond['trial_duration']:      # timed out
            return states['InterTrial']
        else:
            return states['Trial']

    def exit(self):
        self.logger.log_trial()
        self.stim.stop()  # stop stimulus when timeout
        self.logger.ping()


class Abort(State):
    def run(self):
        self.beh.update_history()
        self.logger.log('AbortedTrial')

    def next(self):
        return states['InterTrial']


class Reward(State):
    def run(self):
        self.stim.reward_stim()
        self.beh.reward()

    def next(self):
        return states['InterTrial']


class InterTrial(State):
    def run(self):
        if self.beh.get_response(self.period_start) & self.params.get('noresponse_intertrial'):
            self.timer.start()

    def next(self):
        if self.logger.setup_status in ['stop', 'exit']:
            return states['Exit']
        elif self.beh.is_hydrated():
            return states['Offtime']
        elif self.timer.elapsed_time() >= self.stim.curr_cond['intertrial_duration']:
            return states['PreTrial']
        else:
            return states['InterTrial']


class Offtime(State):
    def entry(self):
        super().entry()
        self.stim.unshow([0, 0, 0])

    def run(self):
        response = self.beh.get_response()
        if not self.beh.is_hydrated(self.params['min_reward']) and response:
            self.beh.reward()
        if self.logger.setup_status not in ['sleeping', 'wakeup'] and self.beh.is_sleep_time():
            self.logger.update_setup_info({'status': 'sleeping'})
        self.logger.ping()
        time.sleep(1)

    def next(self):
        if self.logger.setup_status in ['stop', 'exit']:  # if wake up then update session
            return states['Exit']
        elif self.logger.setup_status == 'wakeup' and not self.beh.is_sleep_time():
            return states['PreTrial']
        elif self.logger.setup_status == 'sleeping' and not self.beh.is_sleep_time():  # if wake up then update session
            return states['Exit']
        elif not self.beh.is_hydrated() and not self.beh.is_sleep_time():
            return states['Exit']
        else:
            return states['Offtime']

    def exit(self):
        if self.logger.setup_status in ['wakeup', 'sleeping']:
            self.logger.update_setup_info({'status': 'running'})


class Exit(State):
    def run(self):
        self.beh.cleanup()
        self.stim.close()
        self.logger.ping(0)
