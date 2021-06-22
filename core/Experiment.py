import datajoint as dj
import numpy as np
from utils.helper_functions import *
from utils.Timer import *
import importlib

experiment = dj.create_virtual_module('experiment', 'test_experiments', create_tables=True)
stimulus = dj.create_virtual_module('stimulus', 'test_stimuli', create_tables=True)
behavior = dj.create_virtual_module('behavior', 'test_behavior', create_tables=True)


class State:
    state_timer, __shared_state = Timer(), {}

    def __init__(self, parent=None):
        self.__dict__ = self.__shared_state
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


class ExperimentClass:
    """  Parent Experiment"""
    curr_state, curr_trial, total_reward, cur_dif, flip_count, states, stim = '', 0, 0, 0, 0, dict(), []
    rew_probe, un_choices, difficulties, iter, curr_cond, dif_h = [], [], [], [], dict(), list()
    required_fields, default_key, conditions, cond_tables = [], dict(), [], []

    # move from State to State using a template method.
    class StateMachine:
        def __init__(self, states):
            self.states = states
            self.futureState = states['Entry']
            self.currentState = states['Entry']
            self.exitState = states['Exit']

        # # # # Main state loop # # # # #
        def run(self):
            while self.futureState != self.exitState:
                if self.currentState != self.futureState:
                    self.currentState.exit()
                    self.currentState = self.futureState
                    self.currentState.entry()
                self.currentState.run()
                self.futureState = self.states[self.currentState.next()]
            self.currentState.exit()
            self.exitState.run()

    def setup(self, logger, BehaviorClass, session_params):
        self.params = {**self.default_key, **session_params}
        self.logger = logger
        self.logger.log_session({**self.default_key, **session_params}, self.__class__.__name__)
        self.beh = BehaviorClass()
        self.beh.setup(logger, self.params)
        self.interface = self.beh.interface
        self.session_timer = Timer()

    def start(self):
        # Initialize states
        states = dict()
        for state in self.__class__.__subclasses__():
            states.update({state().__class__.__name__: state(self)})
        state_control = self.StateMachine(states)
        state_control.run()

    def make_conditions(self, stim_class, conditions):
        conditions = factorize(conditions)
        conditions = self._log_conditions(**stim_class().make_conditions(conditions))
        conditions = self._log_conditions(**self.beh.make_conditions(conditions))
        for cond in conditions:
            assert np.all([field in cond for field in self.required_fields])
            cond.update({**self.default_key, **cond, 'experiment_class': self.cond_tables[0]})
        print(conditions)
        return conditions

    def push_conditions(self, conditions):
        self.conditions += self._log_conditions(conditions, condition_tables=['Condition'] + self.cond_tables, priority=2)
        resp_cond = self.params['resp_cond'] if 'resp_cond' in self.params else 'response_port'
        for stim_class in np.unique([cond['stimulus_class'] for cond in self.conditions]):
            importlib.import_module('Stimuli.' + stim_class)
        diff_flag = np.all(['difficulty' in cond for cond in conditions])
        if diff_flag: self.difficulties = np.array([cond['difficulty'] for cond in self.conditions])
        if np.all([resp_cond in cond for cond in conditions]):
            if diff_flag:
                self.choices = np.array([make_hash([d[resp_cond], d['difficulty']]) for d in conditions])
            else:
                self.choices = np.array([make_hash(d[resp_cond]) for d in conditions])
            self.un_choices, un_idx = np.unique(self.choices, axis=0, return_index=True)
            if diff_flag: self.un_difs = self.difficulties[un_idx]

    def prepare_trial(self):
        old_cond = self.curr_cond
        self._get_new_cond()
        global stim
        if 'stimulus_class' not in old_cond or old_cond['stimulus_class'] != self.curr_cond['stimulus_class']:
            print(self.curr_cond)
            stim_class = importlib.import_module('Stimuli.' + self.curr_cond['stimulus_class'])
            globals().update(stim_class.__dict__)
            stim_class = eval(self.curr_cond['stimulus_class'])
            self.stim = stim_class()
            self.stim.setup(self.logger, self.conditions)
        self.curr_trial += 1
        self.logger.update_trial_idx(self.curr_trial)
        self.trial_start = self.logger.logger_timer.elapsed_time()
        self.logger.log('Trial', dict(cond_hash=self.curr_cond['cond_hash'], time=self.trial_start), priority=3)

    def name(self): return type(self).__name__

    def _log_conditions(self, conditions, condition_tables=['Condition'], schema='experiment', hsh='cond_hash', priority=5):
        fields, hash_dict = list(), dict()
        for ctable in condition_tables:
            table = rgetattr(eval(schema), ctable)
            fields += list(table().heading.names)
        for condition in conditions:
            key = {sel_key: condition[sel_key] for sel_key in fields if sel_key != hsh}
            condition.update({hsh: make_hash(key)})
            hash_dict[condition[hsh]] = condition[hsh]
            for ctable in condition_tables:  # insert dependant condition tables
                priority += 1
                core = [field for field in rgetattr(eval(schema), ctable).primary_key if field != hsh]
                if core and hasattr(condition[core[0]], '__iter__'):
                    for idx, pcond in enumerate(condition[core[0]]):
                        cond_key = {k: v if type(v) in [int, float, str] else v[idx] for k, v in condition.items()}
                        self.logger.put(table=ctable, tuple=cond_key, schema=schema, priority=priority)
                else: self.logger.put(table=ctable, tuple=condition.copy(), schema=schema, priority=priority)
        return conditions

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
class SetupConfiguration(dj.Lookup):
    definition = """
    # Setup configuration
    setup_conf_idx           : tinyint                      # configuration version
    ---
    discription              : varchar(256)
    """

    class Port(dj.Part):
        definition = """
        # Probe identity
        port                     : tinyint                      # port id
        -> SetupConfiguration
        ---
        discription              : varchar(256)
        """

    class Screen(dj.Part):
        definition = """
        # Screen information
        screen_id                : tinyint
        -> SetupConfiguration
        ---
        intensity                : tinyint UNSIGNED 
        monitor_distance         : float
        monitor_aspect           : float
        monitor_size             : float
        fps                      : tinyint UNSIGNED
        resolution_x             : smallint
        resolution_y             : smallint
        discription              : varchar(256)
        """


@experiment.schema
class Session(dj.Manual):
    definition = """
    # Session info
    animal_id            : smallint UNSIGNED            # animal id
    session              : smallint UNSIGNED            # session number
    ---
    -> SetupConfiguration
    user                 : varchar(32)
    experiment_type=null : varchar(256)   
    setup=null           : varchar(256)                 # computer id
    session_tmst         : timestamp                    # session timestamp
    protocol=null        : varchar(256)                 # protocol file
    git_hash             : varchar(12)                  # short github hash
    """

    class Notes(dj.Part):
        definition = """
        # File session info
        -> Session
        timestamp=CURRENT_TIMESTAMP : timestamp         # timestamp
        ---
        note=null                   : varchar(2048)     # session notes
        """

    class Excluded(dj.Part):
        definition = """
        # Excluded sessions
        -> Session
        ---
        reason=null                 : varchar(2048)      # notes for exclusion
        timestamp=CURRENT_TIMESTAMP : timestamp  
        """


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
class Recording(dj.Manual):
    definition = """
    # Recording info
    -> Session
    ---
    aim                      : varchar(16)               # aim of recording 
    """

    class Notes(dj.Part):
        definition = """
        # File session info
        -> Recording
        timestamp            : timestamp                 # timestamp
        ---
        note=null            : varchar(2048)             # session notes
        """

    class Files(dj.Part):
        definition = """
        # File session info
        -> Recording
        -> Software
        ---
        filename=null        : varchar(256)              # file
        source_path=null     : varchar(512)              # local path
        target_path=null     : varchar(512)              # remote drive path
        timestamp            : timestamp                 # timestamp
        """


@experiment.schema
class Condition(dj.Manual):
    definition = """
    # unique stimulus conditions
    cond_hash             : char(24)                 # unique condition hash
    ---
    stimulus_class        : varchar(128) 
    behavior_class        : varchar(128)
    experiment_class      : varchar(128)
    """


@experiment.schema
class Trial(dj.Manual):
    definition = """
    # Trial information
    -> Session
    trial_idx            : smallint UNSIGNED            # unique condition index
    ---
    -> Condition
    time                 : int                          # start time from session start (ms)
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
    setup                       : varchar(256)                 # Setup name
    ---
    status="exit"               : enum('ready','running','stop','sleeping','exit','offtime','wakeup') 
    animal_id=0                 : int                          # animal id
    task_idx=0                  : int                          # task identification number
    session=0                   : int                          
    trials=0                    : int                          
    total_liquid=0              : float                        
    state='none'                : varchar(255)                 
    difficulty=0                : smallint                     
    start_time='00:00:00'       : time                         
    stop_time='23:59:00'        : time                         
    last_ping=CURRENT_TIMESTAMP : timestamp                    
    notes=''                    : varchar(256)                 
    queue_size=0                : int                          
    ip=null                     : varchar(16)                  # setup IP address
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


