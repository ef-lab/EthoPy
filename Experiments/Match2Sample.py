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
        self.logger.log_session(session_params, 'Match2Sample')
        # Initialize params & Behavior/Stimulus objects
        self.beh = BehaviorClass(self.logger, session_params)
        self.stim = StimulusClass(self.logger, session_params, conditions, self.beh)
        self.params = session_params
        self.logger.log_conditions(conditions, self.stim.get_condition_tables())

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
            'Sleep'        : Sleep(self),
            'OffTime'      : OffTime(self),
            'Exit'         : exitState}

    def entry(self):  # updates stateMachine from Database entry - override for timing critical transitions
        self.StateMachine.status = self.logger.get_setup_info('status')
        self.logger.update_state(self.__class__.__name__)
        self.timer.start()

    def run(self):
        self.StateMachine.run()

    def is_sleep_time(self):
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0) + self.logger.get_setup_info('start_time')
        stop = now.replace(hour=0, minute=0, second=0) + self.logger.get_setup_info('stop_time')
        if stop < start:
            stop = stop + timedelta(days=1)
        time_restriction = now < start or now > stop
        return time_restriction


class Prepare(State):
    def run(self):
        self.stim.setup() # prepare stimulus

    def next(self):
        if self.is_sleep_time():
            return states['Sleep']
        else:
            return states['PreTrial']

class PreTrial(State):
    def entry(self):
        self.stim.prepare()
        self.logger.update_state(self.__class__.__name__)
        self.beh.prepare(self.stim.curr_cond)
        self.logger.init_trial(self.stim.curr_cond['cond_hash'])
        self.period_start = self.logger.log_period('PreTrial')
        self.resp_ready = False
        self.timer.start()

    def run(self):
        if self.beh.is_ready(self.stim.curr_cond['init_ready'], self.period_start):
            self.resp_ready = True

    def next(self):
        if not self.stim.curr_cond: # if run out of conditions exit
            return states['Exit']
        elif self.is_sleep_time():
            return states['Sleep']
        elif self.beh.is_ready:
            return states['Cue']
        else:
            if self.timer.elapsed_time() > 5000: # occasionally get control status
                self.timer.start()
                self.StateMachine.status = self.logger.get_setup_info('status')
                self.logger.ping()
            return states['PreTrial']


class Cue(State):
    def entry(self):
        self.resp_ready = False
        self.timer.start()
        self.logger.update_state(self.__class__.__name__)
        self.stim.init(self.__class__.__name__)
        self.timer.start()  # trial start counter
        self.period_start = self.logger.log_period('Cue')

    def run(self):
        self.stim.present()
        self.probe = self.beh.is_licking(self.period_start)
        if self.beh.is_ready(self.stim.curr_cond['cue_ready'], self.period_start):
            self.resp_ready = True

    def next(self):
        if self.probe > 0:
            return states['Abort']
        elif not self.resp_ready and self.timer.elapsed_time() > self.stim.curr_cond['cue_duration']:
            return states['Abort']
        elif self.resp_ready:
            return states['Delay']
        else:
            return states['Cue']

    def exit(self):
        self.stim.stop()


class Delay(State):
    def entry(self):
        self.timer.start()
        self.logger.update_state(self.__class__.__name__)
        self.period_start = self.logger.log_period('Delay')
        self.resp_ready = False

    def run(self):
        self.probe = self.beh.is_licking(self.period_start)
        if self.beh.is_ready(self.stim.curr_cond['delay_ready'], self.period_start):
            self.resp_ready = True

    def next(self):
        if self.probe > 0:
            return states['Abort']
        elif not self.resp_ready and self.timer.elapsed_time() > self.stim.curr_cond['delay_duration']:
            return states['Abort']
        elif self.resp_ready:
            return states['Response']
        else:
            return states['Delay']


class Response(State):
    def entry(self):
        self.timer.start()
        self.logger.update_state(self.__class__.__name__)
        self.stim.init(self.__class__.__name__)
        self.period_start = self.logger.log_period(self.__class__.__name__)
        self.resp_ready = False

    def run(self):
        self.stim.present()  # Start Stimulus
        self.probe = self.beh.is_licking(self.period_start)
        if self.beh.is_ready(self.stim.curr_cond['resp_ready'], self.period_start):
            self.resp_ready = True

    def next(self):
        if not self.resp_ready and self.probe > 0:
            return states['Abort']
        elif self.probe > 0 and not self.beh.is_correct(self.stim.curr_cond): # response to incorrect probe
            return states['Punish']
        elif self.probe > 0 and self.beh.is_correct(self.stim.curr_cond): # response to correct probe
            return states['Reward']
        elif self.timer.elapsed_time() > self.stim.curr_cond['response_duration']:      # timed out
            return states['InterTrial']
        else:
            return states['Response']

    def exit(self):
        self.stim.stop()
        self.logger.log_trial()
        self.logger.ping()
        self.beh.update_history()


class Abort(State):
    def run(self):
        self.logger.log_trial()
        self.logger.log_abort()

    def next(self):
        return states['InterTrial']


class Reward(State):
    def run(self):
        self.beh.reward()
        print('Rewarding')

    def next(self):
        return states['InterTrial']


class Punish(State):
    def entry(self):
        self.beh.punish()
        self.timer.start()
        self.logger.update_state(self.__class__.__name__)
        print('Punishing')

    def run(self):
        self.stim.punish_stim()

    def next(self):
        if self.timer.elapsed_time() >= self.stim.curr_cond['timeout_duration']:
            return states['InterTrial']
        else:
            return states['Punish']

    def exit(self):
        self.stim.unshow()


class InterTrial(State):
    def entry(self):
        self.timer.start()

    def run(self):
        if self.beh.is_licking() & self.params.get('nolick_intertrial'):
            self.timer.start()

    def next(self):
        if self.is_sleep_time():
            return states['Sleep']
        elif self.beh.is_hydrated():
            return states['OffTime']
        elif self.timer.elapsed_time() >= self.stim.curr_cond['intertrial_duration']:
            return states['PreTrial']
        else:
            return states['InterTrial']


class Sleep(State):
    def entry(self):
        self.logger.update_state(self.__class__.__name__)
        self.logger.update_setup_status('sleeping')
        self.stim.set_intensity(0)

    def run(self):
        self.logger.ping()
        time.sleep(5)

    def next(self):
        if self.logger.get_setup_info('status') == 'stop':  # if wake up then update session
            return states['Exit']
        elif self.logger.get_setup_info('status') == 'wakeup' and not self.is_sleep_time():
            self.logger.update_setup_status('running')
            return states['PreTrial']
        elif self.logger.get_setup_info('status') == 'sleeping' and not self.is_sleep_time():  # if wake up then update session
            self.logger.update_setup_status('running')
            return states['Exit']
        else:
            return states['Sleep']


class OffTime(State):
    def entry(self):
        self.logger.update_state(self.__class__.__name__)
        self.logger.update_setup_status('offtime')
        self.stim.set_intensity(0)

    def run(self):
        self.logger.ping()
        time.sleep(5)

    def next(self):
        if self.logger.get_setup_info('status') == 'stop':  # if wake up then update session
            return states['Exit']
        elif self.is_sleep_time():
            return states['Sleep']
        else:
            return states['OffTime']


class Exit(State):
    def run(self):
        self.beh.cleanup()
        self.stim.close()
