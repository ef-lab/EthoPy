import datajoint as dj
import numpy as np

from utils.helper_functions import make_hash
from utils.Timer import *

experiment = dj.create_virtual_module('experiment', 'test_experiments', create_tables=True)
stimulus = dj.create_virtual_module('stimulus', 'test_stimuli', create_tables=True)
behavior = dj.create_virtual_module('behavior', 'test_behavior', create_tables=True)


class State:
    state_timer = Timer()

    def __init__(self, parent=None):
        if parent: self.__dict__.update(parent.__dict__)

    def entry(self):
        """Entry transition method"""
        pass

    def run(self):
        """Main run command"""
        pass

    def next(self):
        """Exit transition method"""
        assert 0, "next not implemented"

    def exit(self):
        """Exit transition method"""
        pass


# move from State to State using a template method.
class StateMachine:
    def __init__(self, initialState, exitState):
        self.futureState = initialState
        self.currentState = initialState
        self.exitState = exitState

    # # # # Main state loop # # # # #
    def run(self):
        while self.futureState != self.exitState:
            if self.currentState != self.futureState:
                self.currentState.exit()
                self.currentState = self.futureState
                self.currentState.entry()
            self.currentState.run()
            self.futureState = self.currentState.next()
        self.currentState.exit()
        self.exitState.run()


class ExperimentClass:
    """  Parent Experiment"""
    curr_state, curr_trial, total_reward, cur_dif, flip_count, states = '', 0, 0, 1, 0, dict()
    rew_probe, un_choices, difficulties, iter, curr_cond, dif_h = [], [], [], [], dict(), list()
    required_fields, default_key, conditions, default_session_params = [], dict(), [], dict()

    def setup(self, logger, BehaviorClass, session_params):
        session_params.update({**self.default_session_params, **session_params})
        self.params = session_params
        self.logger = logger
        #self.logger.log_session(session_params, self.exp_type)
        self.beh = BehaviorClass(logger, session_params)
        self.interface = self.beh.interface
        self.session_timer = Timer()

    def run(self):
        # Initialize states
        global states
        states = dict()
        for state in Experiment.__subclasses__():
            states.update({state().__class__.__name__: state(self)})
        state_control = StateMachine(states['Entry'], states['Exit'])
        state_control.run()

    def make_conditions(self, stim_class, conditions):
        conditions = stim_class().make_conditions(conditions, self.logger)
        for cond in conditions:
            assert np.all([field in cond for field in self.required_fields])
            cond.update({**self.default_key, **cond})
        return self.beh.make_conditions(conditions)

    def push_conditions(self, conditions):
        self.conditions += self.logger.log_conditions(conditions, condition_tables=['Condition', self.exp_type])
        resp_cond = self.params['resp_cond'] if 'resp_cond' in self.params else 'probe'
        if np.all(['difficulty' in cond for cond in conditions]):
            self.difficulties = np.array([cond['difficulty'] for cond in self.conditions])
        if np.all([resp_cond in cond for cond in conditions]):
            if self.difficulties:
                self.choices = np.array([make_hash([d[resp_cond], d['difficulty']]) for d in conditions])
            else:
                self.choices = np.array([make_hash(d[resp_cond]) for d in conditions])
            self.un_choices, un_idx = np.unique(self.choices, axis=0, return_index=True)
            if self.difficulties: self.un_difs = self.difficulties[un_idx]

    def prepare(self):
        old_cond = self.curr_cond
        self._get_new_cond()
        if 'stimulus_class' not in self.curr_cond or old_cond['stimulus_class'] != self.curr_cond['stimulus_class']:
            stim_class = eval(self.curr_cond['stimulus_class'])
            self.stim = stim_class()
            self.stim.setup()

    def name(self):
        return type(self).__name__

    def _anti_bias(self, choice_h, un_choices):
        choice_h = np.array([make_hash(c) for c in choice_h[-self.params['bias_window']:]])
        if len(choice_h) < self.params['bias_window']: choice_h = self.choices
        fixed_p = 1 - np.array([np.mean(choice_h == un) for un in un_choices])
        if sum(fixed_p) == 0:  fixed_p = np.ones(np.shape(fixed_p))
        return np.random.choice(un_choices, 1, p=fixed_p/sum(fixed_p))

    def _get_new_cond(self):
        """Get curr condition & create random block of all conditions
        Should be called within init_trial
        """
        if self.params['trial_selection'] == 'fixed':
            self.curr_cond = [] if len(self.conditions) == 0 else self.conditions.pop()
        elif self.params['trial_selection'] == 'block':
            if np.size(self.iter) == 0: self.iter = np.random.permutation(np.size(self.conditions))
            cond = self.conditions[self.iter[0]]
            self.iter = self.iter[1:]
            self.curr_cond = cond
        elif self.params['trial_selection'] == 'random':
            self.curr_cond = np.random.choice(self.conditions)
        elif self.params['trial_selection'] == 'bias':
            idx = [~np.isnan(ch).any() for ch in self.beh.choice_history]
            choice_h = np.asarray(self.beh.choice_history)
            anti_bias = self._anti_bias(choice_h[idx], self.un_choices)
            selected_conditions = [i for (i, v) in zip(self.conditions, self.choices == anti_bias) if v]
            self.curr_cond = np.random.choice(selected_conditions)
        elif self.params['trial_selection'] == 'staircase':
            idx = [~np.isnan(ch).any() for ch in self.beh.choice_history]
            rew_h = np.asarray(self.beh.reward_history); rew_h = rew_h[idx]
            choice_h = [[c, d] for c, d in zip(np.asarray(self.beh.choice_history)[idx], np.asarray(self.dif_h)[idx])]
            if self.iter == 1 or np.size(self.iter) == 0:
                self.iter = self.params['staircase_window']
                perf = np.nanmean(np.greater(rew_h[-self.params['staircase_window']:], 0))
                if   perf > self.params['stair_up']   and self.cur_dif < max(self.difficulties):  self.cur_dif += 1
                elif perf < self.params['stair_down'] and self.cur_dif > min(self.difficulties):  self.cur_dif -= 1
                self.logger.update_setup_info({'difficulty': self.cur_dif})
            elif np.size(self.beh.choice_history) and self.beh.choice_history[-1:][0] > 0: self.iter -= 1
            anti_bias = self._anti_bias(choice_h, self.un_choices[self.un_difs == self.cur_dif])
            sel_conds = [i for (i, v) in zip(self.conditions, np.logical_and(self.choices == anti_bias,
                                                       self.difficulties == self.cur_dif)) if v]
            self.curr_cond = np.random.choice(sel_conds)
            self.dif_h.append(self.cur_dif)


@experiment.schema
class Software(dj.Lookup):
    definition = """
    # Acquisition program
    software             : varchar(64)                  # program identification number
    version              : varchar(10)                  # version of program
    ---
    description=""       : varchar(2048)                # description
    """


@experiment.schema
class Session(dj.Manual):
    definition = """
    # Session info
    animal_id            : int                          # animal id
    session              : smallint                     # session number
    ---
    -> Software
    user                 : varchar(32)
    experiment_type=null : varchar(256)   
    setup=null           : varchar(256)                 # computer id
    session_tmst         : timestamp                    # session timestamp
    session_params=null  : mediumblob                   
    conditions=null      : mediumblob      
    protocol=null        : varchar(256)                 # protocol file
    """

    class Notes(dj.Part):
        definition = """
        # File session info
        -> Session
        timestamp            : timestamp                   # timestamp
        ---
        note=null            : varchar(2048)               # session notes
        """

    class Files(dj.Part):
        definition = """
        # File session info
        -> Session
        -> Sofrware
        ---
        filename=null        : varchar(256)                # file
        source_path=null     : varchar(512)                # local path
        target_path=null     : varchar(512)                # remote drive path
        timestamp            : timestamp                   # timestamp
        """

    class Excluded(dj.Part):
        definition = """
        # Excluded sessions
        -> Session
        ---
        reason=null            : varchar(2048)             # notes for exclusion
        """


@experiment.schema
class Condition(dj.Manual):
    definition = """
    # unique stimulus conditions
    cond_hash             : char(24)                 # unique condition hash
    ---
    stimulus_class        : varchar(128) 
    """


@experiment.schema
class Trial(dj.Manual):
    definition = """
    # Trial information
    -> Session
    trial_idx            : smallint                     # unique condition index
    ---
    -> Condition
    start_time           : int                          # start time from session start (ms)
    end_time             : int                          # end time from session start (ms)
    """

    class Aborted(dj.Part):
        definition = """
        # Aborted Trials
        -> Trial
        """

    class StateOnset(dj.Part):
        definition = """
        # Trial period timestamps
        -> Trial
        time			    : int 	            # time from session start (ms)
        ---
        state               : varchar(64)
        """


@experiment.schema
class SetupControl(dj.Lookup):
    definition = """
    # Control table 
    setup                : varchar(256)                 # Setup name
    ---
    status="exit"        : enum('ready','running','stop','sleeping','exit','offtime','wakeup') 
    animal_id=null       : int                          # animal id
    task_idx=null        : int                          # task identification number
    session=null         : int                          
    trials=null          : int                          
    total_liquid=null    : float                        
    state=null           : varchar(255)                 
    difficulty=null      : smallint                     
    start_time=null      : time                         
    stop_time=null       : time                         
    last_ping=CURRENT_TIMESTAMP : timestamp                    
    notes=null           : varchar(256)                 
    queue_size=null      : int                          
    ip                   : varchar(16)                  # setup IP address
    """


@experiment.schema
class Task(dj.Lookup):
    definition = """
    # Behavioral experiment parameters
    task_idx             : int                          # task identification number
    ---
    protocol             : varchar(4095)                # stimuli to be presented (array of dictionaries)
    description=""       : varchar(2048)                # task description
    timestamp            : timestamp    
    """


