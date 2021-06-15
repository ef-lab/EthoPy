from core.Experiment import *
global states


@experiment.schema
class Match2Sample(ExperimentClass, dj.Manual):
    definition = """
    # Match2Sample experiment conditions
    -> Condition
    """

    class Session(dj.Part):
        definition = """
        # Match2Sample experiment conditions
        -> Match2Sample
        ---
        trial_selection='staircase': enum
        start_time='10:00:00'      : DATE
        stop_time='16:00:00'       : DATE
        intensity=64               : tinyint UNSIGNED
        max_reward=3000            : smallint
        min_reward=500             : smallint
        bias_window=5              : smallint
        staircase_window=20        : smallint
        stair_up=0.7               : float
        stair_down=0.55            : float
        noresponse_intertrial=1    : tinyint(1)
        incremental_punishment=1   : tinyint(1)
        """

    class Trial(dj.Part):
        definition = """
        # Match2Sample experiment conditions
        -> Match2Sample
        ---
        difficulty            : smallint   
        init_ready            : smallint
        cue_ready             : smallint
        delay_ready           : smallint
        resp_ready            : smallint
        intertrial_duration   : smallint
        cue_duration          : smallint
        delay_duration        : smallint
        response_duration     : smallint
        reward_duration       : smallint
        punish_duration       : smallint
        abort_duration        : smallint 
        """

    exp_type = 'Match2Sample'
    required_fields = ['difficulty']
    default_key = {'init_ready': 0,
                   'cue_ready': 0,
                   'delay_ready': 0,
                   'resp_ready': 0,
                   'intertrial_duration': 1000,
                   'cue_duration': 1000,
                   'delay_duration': 0,
                   'response_duration': 5000,
                   'reward_duration': 2000,
                   'punish_duration': 1000,
                   'abort_duration': 0}

    default_params = {'trial_selection'     : 'staircase',
                      'start_time'            : '10:00:00',
                      'stop_time'             : '16:00:00',
                      'intensity'             : 64,
                      'max_reward'            : 3000,
                      'min_reward'            : 500,
                      'bias_window'           : 5,
                      'staircase_window'      : 20,
                      'stair_up'              : 0.7,
                      'stair_down'            : 0.55,
                      'noresponse_intertrial' : True,
                      'incremental_punishment': True}


class Experiment(State, Match2Sample):
    def entry(self):  # updates stateMachine from Database entry - override for timing critical transitions
        self.logger.curr_state = self.name()
        self.start_time = self.logger.log('StateOnset', {'state': self.name()})
        self.resp_ready = False
        self.state_timer.start()


class Entry(Experiment):
    def next(self):
        if self.beh.is_sleep_time():
            return states['Offtime']
        else:
            return states['PreTrial']


class PreTrial(Experiment):
    def entry(self):
        self.prepare()
        self.stim.prepare(self.curr_cond)
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
        super().entry()
        self.stim.start(self.name())

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
        super().entry()
        self.stim.start(self.name())

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
        self.logger.log('Trial.Aborted')

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
