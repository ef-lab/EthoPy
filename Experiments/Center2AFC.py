from utils.Timer import *
from StateMachine import *
from datetime import datetime, timedelta


class State(StateClass):
    def __init__(self, parent=None):
        self.timer = Timer()
        if parent:
            self.__dict__.update(parent.__dict__)

    def setup(self, logger, BehaviorClass, StimulusClass, session_params, conditions):

        logger.log_session(session_params, conditions)

        # Initialize params & Behavior/Stimulus objects
        self.logger = logger
        self.beh = BehaviorClass(logger, session_params)
        self.stim = StimulusClass(logger, session_params, conditions, self.beh)
        self.params = session_params
        self.StateMachine = StateMachine(Prepare(self), Exit(self))

        # Initialize states
        global states
        states = {
            'PreTrial'     : PreTrial(self),
            'Trial'        : Trial(self),
            'PostTrial'    : PostTrial(self),
            'InterTrial'   : InterTrial(self),
            'Reward'       : Reward(self),
            'Punish'       : Punish(self),
            'Sleep'        : Sleep(self),
            'Exit'         : Exit(self)}

    def entry(self):  # updates stateMachine from Database entry - override for timing critical transitions
        self.StateMachine.state = self.logger.get_setup_state()

    def run(self):
        self.StateMachine.run()


class Prepare(State):
    def run(self):
        self.stim.setup()
        self.stim.prepare()  # prepare stimulus

    def next(self):
        return states['PreTrial']


class PreTrial(State):
    def entry(self):
        self.stim.get_new_cond()
        self.timer.start()

    def run(self): pass

    def next(self):
        if self.beh.is_ready(self.params['init_duration']):
            return states['Trial']
        else:
            self.StateMachine.state = self.logger.get_setup_state()
            return states['PreTrial']


class Trial(State):
    def __init__(self, parent):
        self.__dict__.update(parent.__dict__)
        self.is_ready = 0
        self.probe = 0
        self.resp_ready = False
        super().__init__()

    def entry(self):
        self.stim.init()
        self.beh.is_licking()
        self.timer.start()  # trial start counter
        self.logger.start_trial(self.stim.curr_cond['cond_idx'])
        #self.logger.thread_lock.acquire()

    def run(self):
        self.stim.present()  # Start Stimulus
        self.is_ready = self.beh.is_ready(self.timer.elapsed_time())  # update times
        self.probe = self.beh.is_licking()
        if self.timer.elapsed_time() > self.params['delay_duration'] and not self.resp_ready:
            self.resp_ready = True
            if self.probe > 0: self.beh.update_bias(self.probe)

    def next(self):
        if not self.is_ready and not self.resp_ready:                           # did not wait
            return states['Punish']
        elif self.probe > 0 and self.resp_ready and not self.probe == self.stim.curr_cond['probe']: # response to incorrect probe
            return states['Punish']
        elif self.probe > 0 and self.resp_ready and self.probe == self.stim.curr_cond['probe']: # response to correct probe
            return states['Reward']
        elif self.timer.elapsed_time() > self.params['trial_duration']:      # timed out
            return states['PostTrial']
        else:
            return states['Trial']

    def exit(self):
        #self.logger.thread_lock.release()
        self.logger.log_trial()


class PostTrial(State):
    def run(self):
        self.stim.stop()  # stop stimulus when timeout

    def next(self):
        return states['InterTrial']


class InterTrial(State):
    def run(self):
        if self.beh.is_licking():
            self.timer.start()

    def next(self):
        if Sleep.is_sleep_time():
            return states['Sleep']
        elif self.timer.elapsed_time() > self.params['intertrial_duration']:
            return states['PreTrial']
        else:
            return states['InterTrial']


class Reward(State):
    def run(self):
        self.beh.reward()
        self.stim.stop()

    def next(self):
        return states['InterTrial']


class Punish(State):
    def entry(self):
        self.stim.stop()
        self.stim.unshow([0, 0, 0])
        self.timer.start()

    def run(self): pass

    def next(self):
        if self.timer.elapsed_time() > self.params['timeout_duration']:
            self.stim.unshow()
            return states['InterTrial']
        else:
            return states['Punish']


class Sleep(State):
    def entry(self):
        self.logger.update_setup_state('offtime')
        self.stim.unshow([0, 0, 0])

    def run(self):
        self.logger.ping()
        time.sleep(5)

    def next(self):
        [now, start, stop] = self.get_times()
        if (now < start or now > stop) and self.logger.get_setup_state() == 'offtime':
            return states['Sleep']
        elif self.logger.get_setup_state() == 'offtime':
            self.logger.update_setup_state('running')
            self.stim.unshow()
            return states['Exit']
        else:
            return states['PreTrial']

    def is_sleep_time(self):
        now = datetime.now()
        start = self.params['start_time'] + now.replace(hour=0, minute=0, second=0)
        stop = self.params['stop_time'] + now.replace(hour=0, minute=0, second=0)
        if stop < start:
            stop = stop + timedelta(days=1)
        return now < start or now > stop


class Exit(State):
    def run(self):
        self.beh.cleanup()
        self.stim.unshow()
        self.logger.cleanup()
