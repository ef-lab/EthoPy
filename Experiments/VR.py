from utils.Timer import *
from StateMachine import *


class State(StateClass):
    def __init__(self, parent=None):
        self.timer = Timer()
        if parent:
            self.__dict__.update(parent.__dict__)

    def setup(self, logger, BehaviorClass, StimulusClass, session_params, conditions):
        self.logger = logger
        self.logger.log_session(session_params, 'VR')

        # Initialize params & Behavior/Stimulus objects
        self.beh = BehaviorClass(self.logger, session_params)
        self.stim = StimulusClass(self.logger, session_params, conditions, self.beh)
        self.params = session_params
        self.logger.log_conditions(conditions, self.stim.get_cond_tables() + self.beh.get_cond_tables())
        exitState = Exit(self)
        self.StateMachine = StateMachine(Prepare(self), exitState)

        # Initialize states
        global states
        states = {
            'PreTrial'     : PreTrial(self),
            'Trial'        : Trial(self),
            'Abort'        : Abort(self),
            'Reward'       : Reward(self),
            'Punish'       : Punish(self),
            'InterTrial'   : InterTrial(self),
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
        return states['PreTrial']


class PreTrial(State):
    def entry(self):
        self.logger.ping()
        self.stim.prepare()
        self.beh.prepare(self.stim.curr_cond)
        self.logger.init_trial(self.stim.curr_cond['cond_hash'])
        super().entry()
        if not self.stim.curr_cond: self.logger.update_setup_info({'status': 'stop'})

    def run(self):
        if self.timer.elapsed_time() > 5000:  # occasionally get control status
            self.timer.start()
            self.logger.ping()

    def next(self):
        if not self.stim.curr_cond:  # if run out of conditions exit
            return states['Exit']
        elif self.logger.setup_status in ['stop', 'exit']:
            return states['Exit']
        else:
            return states['Trial']


class Trial(State):
    def entry(self):
        super().entry()
        self.stim.init()

    def run(self):
        self.stim.present()
        self.response = self.beh.is_licking(self.period_start)

    def next(self):
        if self.response and self.beh.is_correct():  # correct response
            return states['Reward']
        elif not self.beh.is_ready() and self.response:
            return states['Abort']
        elif self.response and not self.beh.is_correct():  # incorrect response
            return states['Punish']
        elif self.timer.elapsed_time() > self.stim.curr_cond['response_duration']:  # timed out
            return states['InterTrial']
        else:
            return states['Trial']

    def exit(self):
        self.stim.stop()
        self.logger.ping()


class Abort(State):
    def run(self):
        self.beh.update_history()
        self.logger.log('AbortedTrial')

    def next(self):
        return states['InterTrial']


class Reward(State):
    def run(self):
        self.beh.reward()

    def next(self):
        return states['InterTrial']


class Punish(State):
    def entry(self):
        self.beh.punish()
        super().entry()

    def run(self):
        self.stim.punish_stim()

    def next(self):
        if self.timer.elapsed_time() >= self.stim.curr_cond['punish_duration']:
            return states['InterTrial']
        else:
            return states['Punish']

    def exit(self):
        self.stim.unshow()


class InterTrial(State):
    def entry(self):
        self.logger.log_trial()
        super().entry()

    def run(self):
        if self.beh.get_response(self.period_start) & self.params.get('noresponse_intertrial'):
            self.timer.start()

    def next(self):
        if self.logger.setup_status in ['stop', 'exit']:
            return states['Exit']
        elif self.timer.elapsed_time() >= self.stim.curr_cond['intertrial_duration']:
            return states['PreTrial']
        else:
            return states['InterTrial']


class Exit(State):
    def run(self):
        self.beh.cleanup()
        self.stim.close()
        self.logger.ping(0)
