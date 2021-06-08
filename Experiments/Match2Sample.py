from Experiment import *


class Experiment(StateClass, Session):
    def entry(self):  # updates stateMachine from Database entry - override for timing critical transitions
        self.curr_state = type(self).__name__
        self.start_time = self.logger.log('StateOnset', {'state': type(self).__name__})
        self.state_timer.start()

    def run(self):
        # Initialize states
        exitState = Exit(self)
        state_control = StateMachine(Prepare(self), exitState)
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
            'Hydrate'      : Hydrate(self),
            'Offtime'      : Offtime(self),
            'Exit'         : exitState}
        state_control.run()


class Prepare(Experiment):
    def run(self):
        self.stim.setup()  # prepare stimulus

    def next(self):
        if self.beh.is_sleep_time():
            return states['Offtime']
        else:
            return states['PreTrial']


class PreTrial(Experiment):
    def entry(self):
        self._get_new_cond()
        self.resp_ready = False
        self.stim.prepare()
        self.beh.prepare(self.curr_cond)
        self.logger.init_trial(self.curr_cond['cond_hash'])
        super().entry()
        if not self.curr_cond: self.logger.update_setup_info({'status': 'stop'})

    def run(self):
        if self.beh.is_ready(self.curr_cond['init_ready'], self.start_time):
            self.resp_ready = True
        self.logger.ping()

    def next(self):
        if not self.curr_cond:  # if run out of conditions exit
            return states['Exit']
        elif self.logger.setup_status in ['stop', 'exit']:
            return states['Exit']
        elif self.resp_ready:
            return states['Cue']
        else:
            return states['PreTrial']


class Cue(Experiment):
    def entry(self):
        self.resp_ready = False
        super().entry()
        self.stim.start(type(self).__name__)

    def run(self):
        self.stim.present()
        self.logger.ping()
        self.response = self.beh.get_response(self.start_time)
        if self.beh.is_ready(self.curr_cond['cue_ready'], self.start_time):
            self.resp_ready = True

    def next(self):
        if self.resp_ready:
            return states['Delay']
        elif self.response:
            return states['Abort']
        elif self.state_timer.elapsed_time() > self.curr_cond['cue_duration']:
            return states['Abort']
        elif self.logger.setup_status in ['stop', 'exit']:  # if wake up then update session
            return states['Exit']
        else:
            return states['Cue']

    def exit(self):
        self.stim.stop()


class Delay(Experiment):
    def entry(self):
        self.resp_ready = False
        super().entry()

    def run(self):
        self.response = self.beh.get_response(self.start_time)
        if self.beh.is_ready(self.curr_cond['delay_ready'], self.start_time):
            self.resp_ready = True

    def next(self):
        if self.resp_ready and self.timer.elapsed_time() > self.stim.curr_cond['delay_duration']: # this specifies the minimum amount of time we want to spend in the delay period contrary to the cue_duration FIX IT
            return states['Response']
        elif self.response:
            return states['Abort']
        elif not self.resp_ready and self.state_timer.elapsed_time() > self.curr_cond['delay_duration']:
            return states['Abort']
        elif self.logger.setup_status in ['stop', 'exit']:
            return states['Exit']
        else:
            return states['Delay']


class Response(Experiment):
    def entry(self):
        self.resp_ready = False
        super().entry()
        self.stim.start(type(self).__name__)

    def run(self):
        self.stim.present()  # Start Stimulus
        self.logger.ping()
        self.response = self.beh.get_response(self.start_time)
        if self.beh.is_ready(self.curr_cond['resp_ready'], self.start_time):
            self.resp_ready = True

    def next(self):
        if self.response and self.beh.is_correct() and self.resp_ready:  # correct response
            return states['Reward']
        elif not self.resp_ready and self.response:
            return states['Abort']
        elif self.response and not self.beh.is_correct():  # incorrect response
            return states['Punish']
        elif self.timer.elapsed_time() > self.stim.curr_cond['response_duration']:      # timed out
            return states['Abort']
        elif self.logger.setup_status in ['stop', 'exit']:
            return states['Exit']
        else:
            return states['Response']

    def exit(self):
        self.stim.stop()
        self.logger.ping()


class Abort(Experiment):
    def entry(self):
        super().entry()
        self.beh.update_history()
        self.logger.log('AbortedTrial')

    def run(self):
        pass

    def next(self):
        if self.timer.elapsed_time() >= self.stim.curr_cond['abort_duration']:
            return states['InterTrial']
        elif self.logger.setup_status in ['stop', 'exit']:
            return states['Exit']
        else:
            return states['Abort']


class Reward(Experiment):
    def entry(self):
        self.stim.reward_stim()
        super().entry()

    def run(self):
        self.rewarded = self.beh.reward()

    def next(self):
        if self.rewarded or self.state_timer.elapsed_time() >= self.curr_cond['reward_duration']:
            return states['InterTrial']
        elif self.logger.setup_status in ['stop', 'exit']:
            return states['Exit']
        else:
            return states['Reward']


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
        if self.timer.elapsed_time() >= self.punish_period:
            return states['InterTrial']
        elif self.logger.setup_status in ['stop', 'exit']:
            return states['Exit']
        else:
            return states['Punish']

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
        if self.logger.setup_status in ['stop', 'exit']:
            return states['Exit']
        elif self.beh.is_sleep_time() and not self.beh.is_hydrated(self.params['min_reward']):
            return states['Hydrate']
        elif self.beh.is_sleep_time() or self.beh.is_hydrated():
            return states['Offtime']
        elif self.state_timer.elapsed_time() >= self.curr_cond['intertrial_duration']:
            return states['PreTrial']
        else:
            return states['InterTrial']


class Hydrate(Experiment):
    def run(self):
        if self.beh.get_response():
            self.beh.reward()
            time.sleep(1)
        self.logger.ping()

    def next(self):
        if self.logger.setup_status in ['stop', 'exit']:  # if wake up then update session
            return states['Exit']
        elif self.beh.is_hydrated(self.params['min_reward']) or not self.beh.is_sleep_time():
            return states['Offtime']
        else:
            return states['Hydrate']


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


class Exit(Experiment):
    def run(self):
        self.beh.cleanup()
        self.stim.close()
        self.logger.ping(0)
