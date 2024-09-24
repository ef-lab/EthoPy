from core.Experiment import *


@experiment.schema
class Condition(dj.Manual):
    class FreeWater(dj.Part):
        definition = """
        # Passive experiment conditions
        -> Condition
        ---
        max_reward=3000            : smallint
        noresponse_intertrial=1    : tinyint(1)
        trial_selection='staircase' : enum('fixed','block','random','staircase','biased')     
        intertrial_duration        : int
        """


class Experiment(State, ExperimentClass):
    cond_tables = ['FreeWater']
    required_fields = ['staircase_window'] # Needs to change in the new version
    default_key = {'trial_selection'       : 'fixed',
                   'max_reward'            : 6000,
                   'noresponse_intertrial' : True,
                   'intertrial_duration'   : 1000}

    def entry(self):  # updates stateMachine from Database entry - override for timing critical transitions
        self.logger.curr_state = self.name()
        self.start_time = self.logger.log('Trial.StateOnset', {'state': self.name()})
        self.resp_ready = False
        self.state_timer.start()


class Entry(Experiment):
    def entry(self):
        pass

    def next(self):
        return 'Trial'


class Trial(Experiment):
    def entry(self):
        self.prepare_trial()
        self.stim.prepare(self.curr_cond)
        self.beh.prepare(self.curr_cond)
        super().entry()
        self.stim.start()
        self.stim.start_stim()

    def run(self):
        time.sleep(.01)
        self.stim.present()  # Start Stimulus
        self.response = self.beh.get_response(self.start_time)

    def next(self):
        if self.is_stopped():  # if wake up then update session
            return 'Exit'
        elif self.beh.is_sleep_time():
            return 'Offtime'
        elif self.response and self.beh.is_correct():  # response to correct probe
            return 'Reward'
        else:
            return 'Trial'

    def exit(self):
        self.stim.stop()  # stop stimulus when timeout


class Reward(Experiment):
    def entry(self):
        super().entry()
        self.stim.reward_stim()

    def run(self):
        self.rewarded = self.beh.reward(self.start_time)

    def next(self):
        if self.rewarded:
            return 'InterTrial'
        else:
            return 'Reward'

class InterTrial(Experiment):
    def run(self):
        if self.beh.is_licking() and self.curr_cond['noresponse_intertrial']:
            self.state_timer.start()

    def next(self):
        if self.is_stopped():
            return 'Exit'
        elif self.beh.is_hydrated():
            return 'Offtime'
        elif self.state_timer.elapsed_time() >= self.stim.curr_cond['intertrial_duration']:
            return 'Trial'
        else:
            return 'InterTrial'

    def exit(self):
        self.stim.start_stim()


class Offtime(Experiment):
    def entry(self):
        super().entry()
        self.stim.fill([0, 0, 0])

    def run(self):
        if self.logger.setup_status not in ['sleeping', 'wakeup'] and self.beh.is_sleep_time():
            self.logger.update_setup_info({'status': 'sleeping'})
        time.sleep(1)

    def next(self):
        if self.is_stopped():
            return 'Exit'
        elif self.logger.setup_status == 'wakeup' and not self.beh.is_sleep_time():
            return 'Trial'
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
        self.stop()
