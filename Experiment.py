import numpy as np
from utils.Timer import *
from utils.generator import make_hash
import datajoint as dj
experiment = dj.create_virtual_module('exp', 'test_experiments', create_tables=True)


class StateClass:
    state_timer = Timer()

    def __init__(self, parent=None):
        if parent: self.__dict__.update(parent.__dict__)

    def entry(self):
        """Entry transition method"""
        pass

    def run(self):
        """Main run command"""
        assert 0, "run not implemented"

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


class ParentExperiment:
    """  Parent Experiment"""
    curr_state, curr_trial, total_reward, cur_dif, flip_count = '', 0, 0, 1, 0
    rew_probe, un_choices, difficulties, iter, curr_cond, dif_h = [], [], [], [], dict(), list()

    def setup(self, logger, BehaviorClass, session_params, conditions):
        self.params = session_params
        self.logger = logger
        self.conditions = conditions
        self.beh = BehaviorClass(logger, session_params)
        self.session_timer = Timer()

        resp_cond = session_params['resp_cond'] if 'resp_cond' in session_params else 'probe'
        if np.all(['difficulty' in cond for cond in conditions]):
            self.difficulties = np.array([cond['difficulty'] for cond in self.conditions])
        if np.all([resp_cond in cond for cond in conditions]):
            if self.difficulties:
                self.choices = np.array([make_hash([d[resp_cond], d['difficulty']]) for d in conditions])
            else:
                self.choices = np.array([make_hash(d[resp_cond]) for d in conditions])
            self.un_choices, un_idx = np.unique(self.choices, axis=0, return_index=True)
            if self.difficulties: self.un_difs = self.difficulties[un_idx]
        self.logger.log_conditions(conditions)

    def start_session(self, session_type):
        self.total_reward = 0
        self.session_timer.start()  # start session time

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
class Session(dj.Manual):
    definition = """
    # Behavior session info
    animal_id            : int                          # animal id
    session              : smallint                     # session number
    ---
    setup=null           : varchar(256)                 # computer id
    session_tmst         : timestamp                    # session timestamp
    notes=null           : varchar(2048)                # session notes
    session_params=null  : mediumblob                   
    conditions=null      : mediumblob      
    protocol=null        : varchar(256)                 # protocol file
    experiment_type=null : varchar(256)                 
    """

    class Files(dj.Part):
        definition = """
        # File session info
        -> Session
        program              : varchar(256)
        ---
        filename=null        : varchar(256)                # file
        source_path=null     : varchar(512)                # local path
        target_path=null     : varchar(512)                # remote drive path
        timestamp            : timestamp                   # timestamp
        """

    class StateOnset(dj.Part):
        definition = """
        # Trial period timestamps
        -> Session
        time			    : int 	            # time from session start (ms)
        ---
        state               : varchar(64)
        """


@experiment.schema
class Condition(dj.Manual):
    definition = """
    # unique stimulus conditions
    cond_hash             : char(24)                 # unique condition hash
    ---
    stimulus_type         : varchar(128)
    stimulus_hash         : char(24)
    cond_tuple=null       : blob      
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
        -> Session
        trial_idx            : smallint                     # unique condition index
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


