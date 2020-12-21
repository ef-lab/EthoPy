from utils.Timer import *
from StateMachine import *
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

        logger.update_setup_info('start_time', session_params['start_time'])
        logger.update_setup_info('stop_time', session_params['stop_time'])

        exitState = Exit(self)
        self.StateMachine = StateMachine(Prepare(self), exitState)

        # Initialize states
        global states
        states = {
            'PreTrial'     : PreTrial(self),
            'Trial'        : Trial(self),
            'Abort'        : Abort(self),
            'InterTrial'   : InterTrial(self),
            'Reward'       : Reward(self),
            'Sleep'        : Sleep(self),
            'Offtime'      : Offtime(self),
            'Exit'         : exitState}

    def entry(self):  # updates stateMachine from Database entry - override for timing critical transitions
        self.logger.update_setup_info('state', type(self).__name__)
        self.period_start = self.logger.log('StateOnset', {'state': type(self).__name__})
        self.timer.start()

    def run(self):
        self.StateMachine.run()


class Prepare(State):
    def run(self):
        self.stim.setup()  # prepare stimulus

    def next(self):
        if self.beh.is_sleep_time():
            return states['Sleep']
        else:
            return states['PreTrial']


class PreTrial(State):
    def entry(self):
        self.stim.prepare()
        if not self.stim.curr_cond:
            self.logger.update_setup_info('status', 'stop', nowait=True)
        else:
            self.beh.prepare(self.stim.curr_cond)
        super().entry()

    def run(self):
        if self.timer.elapsed_time() > 5000:  # occasionally get control status
            self.timer.start()
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
        self.stim.init()
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
        self.logger.log_abort()

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
        elif self.beh.is_sleep_time():
            return states['Sleep']
        elif self.beh.is_hydrated():
            return states['Offtime']
        elif self.timer.elapsed_time() >= self.stim.curr_cond['intertrial_duration']:
            return states['PreTrial']
        else:
            return states['InterTrial']


class Sleep(State):
    def entry(self):
        super().entry()
        self.logger.update_setup_info('status', 'sleeping')
        self.stim.unshow([0, 0, 0])

    def run(self):
        self.logger.ping()
        time.sleep(5)

    def next(self):
        if self.logger.setup_status in ['stop', 'exit']:  # if wake up then update session
            return states['Exit']
        elif self.logger.setup_status == 'wakeup' and not self.beh.is_sleep_time():
            return states['PreTrial']
        elif self.logger.setup_status == 'sleeping' and not self.beh.is_sleep_time():  # if wake up then update session
            return states['Exit']
        else:
            return states['Sleep']

    def exit(self):
        if self.logger.setup_status not in ['stop', 'exit']:
            self.logger.update_setup_info('status', 'running', nowait=True)
            self.logger.setup_status = 'running'


class Offtime(State):
    def entry(self):
        super().entry()
        self.logger.update_setup_info('status', 'offtime')
        self.stim.unshow([0, 0, 0])

    def run(self):
        self.logger.ping()
        time.sleep(5)

    def next(self):
        if self.logger.setup_status in ['stop', 'exit']:  # if wake up then update session
            return states['Exit']
        elif self.beh.is_sleep_time():
            return states['Sleep']
        else:
            return states['Offtime']


class Exit(State):
    def run(self):
        self.beh.cleanup()
        self.stim.close()
