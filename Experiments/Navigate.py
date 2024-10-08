from core.Experiment import *


@experiment.schema
class Condition(dj.Manual):
    class Navigate(dj.Part):
        definition = """
        # Navigation experiment conditions
        -> Condition
        ---
        max_reward=3000             : smallint
        min_reward=500              : smallint
        norun_response=1            : tinyint(1)

        trial_selection='staircase' : enum('fixed','block','random','staircase', 'biased') 
        difficulty                  : int   
        bias_window=5               : smallint
        staircase_window=20         : smallint
        stair_up=0.7                : float
        stair_down=0.55             : float
        noresponse_intertrial=1     : tinyint(1)
        incremental_punishment=1    : tinyint(1)
        next_up=0                   : tinyint
        next_down=0                 : tinyint
        metric='accuracy'           : enum('accuracy','dprime') 
        antibias=1                  : tinyint(1)
    
        trial_ready                 : int
        trial_duration              : int
        intertrial_duration         : int
        reward_duration             : int
        punish_duration             : int
        """


class Experiment(State, ExperimentClass):
    cond_tables = ['Navigate']
    required_fields = ['difficulty']
    default_key = {'noresponse_intertrial' : True,
                   'norun_response'        : True,
                   'incremental_punishment': True,
                   'trial_selection'       : 'staircase',

                   'trial_ready'            : 0,
                   'intertrial_duration'    : 1000,
                   'trial_duration'         : 1000,
                   'reward_duration'        : 2000,
                   'punish_duration'        : 1000}

    def entry(self):  # updates stateMachine from Database entry - override for timing critical transitions
        self.logger.curr_state = self.name()
        self.start_time = self.logger.log('Trial.StateOnset', {'state': self.name()})
        self.resp_ready = False
        self.state_timer.start()


class Entry(Experiment):
    def entry(self):
        pass

    def next(self):
        return 'PreTrial'


class PreTrial(Experiment):
    def entry(self):
        self.prepare_trial()
        if not self.is_stopped():
            self.beh.prepare(self.curr_cond)
            self.stim.prepare(self.curr_cond)
            self.state_timer.start()

    def next(self):
        if self.is_stopped():
            return 'Exit'
        else:
            return 'Trial'


class Trial(Experiment):
    def entry(self):
        super().entry()
        self.is_in_correct_loc = False
        self.stim.start()
        self.beh.vr.update_location = True

    def run(self):
        self.stim.present()
        self.response = self.beh.get_response(self.start_time)
        is_in_correct_loc = self.beh.is_in_correct_loc()
        if is_in_correct_loc and not self.is_in_correct_loc:
            self.stim.ready_stim()
        self.is_in_correct_loc = is_in_correct_loc
        time.sleep(.1)

    def next(self):
        if self.response and self.is_in_correct_loc and not self.beh.is_running():  # correct response
            return 'Reward'
        elif not self.beh.is_ready() and self.response:
            return 'Abort'
        elif self.response and self.beh.is_ready() and not self.beh.is_running():  # incorrect response
            return 'Punish'
        elif self.state_timer.elapsed_time() > self.stim.curr_cond['trial_duration']:  # timed out
            return 'Abort'
        elif self.is_stopped():
            return 'Exit'
        else:
            return 'Trial'

    def exit(self):
        self.stim.stop()
        self.beh.vr.update_location = False


class Abort(Experiment):
    def entry(self):
        pass

    def run(self):
        self.beh.update_history()
        self.logger.log('Trial.Aborted')

    def next(self):
        return 'InterTrial'


class Reward(Experiment):
    def run(self):
        self.beh.reward()

    def next(self):
        return 'InterTrial'


class Punish(Experiment):
    def entry(self):
        self.beh.punish()
        super().entry()

    def run(self):
        self.stim.punish_stim()

    def next(self):
        if self.state_timer.elapsed_time() >= self.stim.curr_cond['punish_duration']:
            return 'InterTrial'
        else:
            return 'Punish'

    def exit(self):
        self.stim.fill()


class InterTrial(Experiment):
    def entry(self):
        self.state_timer.start()

    def run(self):
        if self.beh.is_licking() and self.curr_cond['noresponse_intertrial']:
            self.state_timer.start()

    def next(self):
        if self.is_stopped():
            return 'Exit'
        elif self.beh.is_running():
            return 'InterTrial'
        elif self.state_timer.elapsed_time() >= self.stim.curr_cond['intertrial_duration']:
            return 'PreTrial'
        else:
            return 'InterTrial'


class Exit(Experiment):
    def entry(self):
        self.interface.release()
        
    def run(self):
        self.stop()
