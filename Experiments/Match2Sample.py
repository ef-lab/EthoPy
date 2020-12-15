from utils.Timer import *
from StateMachine import *


class State(StateClass):
    def __init__(self, parent=None):
        self.timer = Timer()
        if parent:
            self.__dict__.update(parent.__dict__)

    def setup(self, logger, BehaviorClass, StimulusClass, session_params, conditions):
        self.logger = logger
        self.logger.log_session(session_params, 'Match2Sample')

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
            'Cue'          : Cue(self),
            'Delay'        : Delay(self),
            'Response'     : Response(self),
            'Abort'        : Abort(self),
            'Reward'       : Reward(self),
            'Punish'       : Punish(self),
            'InterTrial'   : InterTrial(self),
            'Offtime'      : Offtime(self),
            'Sleep'        : Sleep(self),
            'Exit'         : exitState}

    def entry(self):  # updates stateMachine from Database entry - override for timing critical transitions
        self.logger.update_setup_info('state', type(self).__name__)
        self.StateMachine.status = self.logger.setup_status
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
        self.beh.prepare(self.stim.curr_cond)
        self.logger.init_trial(self.stim.curr_cond['cond_hash'])
        self.period_start = self.logger.log_period('PreTrial')
        self.resp_ready = False
        super().entry()
        if not self.stim.curr_cond: self.logger.update_setup_info('status', 'stop', nowait=True)

    def run(self):
        if self.beh.is_ready(self.stim.curr_cond['init_ready'], self.period_start):
            self.resp_ready = True
        if self.timer.elapsed_time() > 5000:  # occasionally get control status
            self.timer.start()
            self.StateMachine.status = self.logger.get_setup_info('status')
            self.logger.ping()

    def next(self):
        if not self.stim.curr_cond:  # if run out of conditions exit
            return states['Exit']
        elif self.beh.is_ready:
            return states['Cue']
        else:
            return states['PreTrial']


class Cue(State):
    def entry(self):
        self.resp_ready = False
        super().entry()
        self.stim.init(type(self).__name__)
        self.period_start = self.logger.log_period('Cue')

    def run(self):
        self.stim.present()
        self.response = self.beh.response(self.period_start)
        if self.beh.is_ready(self.stim.curr_cond['cue_ready'], self.period_start):
            self.resp_ready = True

    def next(self):
        if self.resp_ready:
            return states['Delay']
        elif self.response:
            return states['Abort']
        elif self.timer.elapsed_time() > self.stim.curr_cond['cue_duration']:
            return states['Abort']
        else:
            return states['Cue']

    def exit(self):
        self.stim.stop()


class Delay(State):
    def entry(self):
        super().entry()
        self.period_start = self.logger.log_period('Delay')
        self.resp_ready = False

    def run(self):
        self.response = self.beh.response(self.period_start)
        if self.beh.is_ready(self.stim.curr_cond['delay_ready'], self.period_start):
            self.resp_ready = True

    def next(self):
        if self.resp_ready:
            return states['Response']
        elif self.response:
            return states['Abort']
        elif not self.resp_ready and self.timer.elapsed_time() > self.stim.curr_cond['delay_duration']:
            return states['Abort']
        else:
            return states['Delay']


class Response(State):
    def entry(self):
        super().entry()
        self.stim.init(type(self).__name__)
        self.period_start = self.logger.log_period(type(self).__name__)
        self.resp_ready = False

    def run(self):
        self.stim.present()  # Start Stimulus
        self.response = self.beh.response(self.period_start)
        if self.beh.is_ready(self.stim.curr_cond['resp_ready'], self.period_start):
            self.resp_ready = True

    def next(self):
        if self.response and self.beh.is_correct() and self.resp_ready:  # correct response
            return states['Reward']
        elif not self.resp_ready and self.response:
            return states['Abort']
        elif self.response and not self.beh.is_correct():  # incorrect response
            return states['Punish']
        elif self.timer.elapsed_time() > self.stim.curr_cond['response_duration']:      # timed out
            return states['InterTrial']
        else:
            return states['Response']

    def exit(self):
        self.stim.stop()
        self.logger.ping()


class Abort(State):
    def run(self):
        self.beh.update_history()
        self.logger.log_trial()
        self.logger.log_abort()

    def next(self):
        return states['InterTrial']


class Reward(State):
    def entry(self):
        self.logger.log_trial()
        super().entry()

    def run(self):
        self.rewarded = self.beh.reward()

    def next(self):
        if self.rewarded or self.timer.elapsed_time() >= self.stim.curr_cond['reward_duration']:
            return states['InterTrial']
        else:
            return states['Reward']


class Punish(State):
    def entry(self):
        self.logger.log_trial()
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
        super().entry()
        self.period_start = self.logger.log_period(type(self).__name__)

    def run(self):
        if self.beh.response(self.period_start) & self.params.get('noresponse_intertrial'):
            self.timer.start()

    def next(self):
        if self.beh.is_sleep_time():
            return states['Sleep']
        elif self.beh.is_hydrated():
            return states['Offtime']
        elif self.timer.elapsed_time() >= self.stim.curr_cond['intertrial_duration']:
            return states['PreTrial']
        else:
            return states['InterTrial']


class Sleep(State):
    def entry(self):
        self.logger.update_setup_info('state', type(self).__name__)
        self.logger.update_setup_info('status', 'sleeping')
        self.stim.unshow([0, 0, 0])

    def run(self):
        self.logger.ping()
        time.sleep(5)

    def next(self):
        if self.logger.setup_status == 'stop':  # if wake up then update session
            return states['Exit']
        elif self.logger.setup_status == 'wakeup' and not self.beh.is_sleep_time():
            return states['PreTrial']
        elif self.logger.setup_status == 'sleeping' and not self.beh.is_sleep_time():  # if wake up then update session
            return states['Exit']
        else:
            return states['Sleep']

    def exit(self):
        if not self.logger.setup_status == 'stop':
            self.logger.update_setup_info('status', 'running')


class Offtime(State):
    def entry(self):
        self.logger.update_setup_info('state', type(self).__name__)
        self.logger.update_setup_info('status', 'offtime')
        self.stim.unshow([0, 0, 0])

    def run(self):
        self.logger.ping()
        time.sleep(5)

    def next(self):
        if self.logger.setup_status == 'stop':  # if wake up then update session
            return states['Exit']
        elif self.beh.is_sleep_time():
            return states['Sleep']
        else:
            return states['Offtime']


class Exit(State):
    def run(self):
        self.beh.cleanup()
        self.stim.close()
