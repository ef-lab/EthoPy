import datajoint as dj
from utils.helper_functions import *
from utils.Timer import *
import itertools
import matplotlib.pyplot as plt

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
    """  Parent Experiment """
    curr_state, curr_trial, total_reward, cur_dif, flip_count, states, stim = '', 0, 0, 0, 0, dict(), []
    rew_probe, un_choices, difs, iter, curr_cond, dif_h, stims = [], [], [], [], dict(), [], dict()
    required_fields, default_key, conditions, cond_tables, quit = [], dict(), [], [], False

    # move from State to State using a template method.
    class StateMachine:
        """  STATE MACHINE """
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
        self.conditions, self.quit, self.curr_cond, self.dif_h, self.stims = [], False, dict(), [], dict()
        self.params = {**self.default_key, **session_params}
        self.logger = logger
        self.logger.log_session({**self.default_key, **session_params}, log_protocol=True)
        self.beh = BehaviorClass()
        self.beh.setup(self)
        self.interface = self.beh.interface
        self.session_timer = Timer()

    def start(self):
        states = dict()
        for state in self.__class__.__subclasses__():  # Initialize states
            states.update({state().__class__.__name__: state(self)})
        state_control = self.StateMachine(states)
        state_control.run()

    def is_stopped(self):
        self.quit = self.quit or self.logger.setup_status in ['stop', 'exit']
        if self.quit and self.logger.setup_status not in ['stop', 'exit']:
            self.logger.update_setup_info({'status': 'stop'})
        return self.quit

    def make_conditions(self, stim_class, conditions, stim_periods=None):
        stim_name = stim_class.__class__.__name__
        if stim_name not in self.stims:
            stim_class.init(self)
            self.stims[stim_name] = stim_class
        conditions.update({'stimulus_class': stim_name})
        if not stim_periods:
            conditions = self.stims[stim_name].make_conditions(factorize(conditions))
        else:
            cond = {stim_periods[0]: self.stims[stim_name].make_conditions(conditions=factorize(conditions[stim_periods[0]])),
                    stim_periods[1]: self.stims[stim_name].make_conditions(conditions=factorize(conditions[stim_periods[1]]))}
            conditions[stim_periods[0]], conditions[stim_periods[1]] = [], []
            for comb in list(itertools.product(cond[stim_periods[0]], cond[stim_periods[1]])):
                conditions[stim_periods[0]].append(comb[0])
                conditions[stim_periods[1]].append(comb[1])
            conditions = factorize(conditions)

        conditions = self.log_conditions(**self.beh.make_conditions(conditions))
        for cond in conditions:
            assert np.all([field in cond for field in self.required_fields])
            cond.update({**self.default_key, **cond, 'experiment_class': self.cond_tables[0]})
        conditions = self.log_conditions(conditions, condition_tables=['Condition'] + self.cond_tables, priority=2)
        return conditions

    def push_conditions(self, conditions):
        self.conditions = conditions
        resp_cond = self.params['resp_cond'] if 'resp_cond' in self.params else 'response_port'
        if np.all(['difficulty' in cond for cond in conditions]):
            self.difs = np.array([cond['difficulty'] for cond in self.conditions])
            diff_flag = True
            self.cur_dif = min(self.difs)
        else:
            diff_flag = False
        if np.all([resp_cond in cond for cond in conditions]):
            if diff_flag:
                self.choices = np.array([make_hash([d[resp_cond], d['difficulty']]) for d in conditions])
            else:
                self.choices = np.array([make_hash(d[resp_cond]) for d in conditions])
            self.un_choices, un_idx = np.unique(self.choices, axis=0, return_index=True)
            if diff_flag: self.un_difs = self.difs[un_idx]

    def prepare_trial(self):
        old_cond = self.curr_cond
        self._get_new_cond()
        if not self.curr_cond:
            self.quit = True
            return
        if 'stimulus_class' not in old_cond or old_cond['stimulus_class'] != self.curr_cond['stimulus_class']:
            if 'stimulus_class' in old_cond: self.stim.exit()
            self.stim = self.stims[self.curr_cond['stimulus_class']]
            self.stim.setup()
        self.curr_trial += 1
        self.logger.update_trial_idx(self.curr_trial)
        self.trial_start = self.logger.logger_timer.elapsed_time()
        self.logger.log('Trial', dict(cond_hash=self.curr_cond['cond_hash'], time=self.trial_start), priority=3)

    def name(self): return type(self).__name__

    def log_conditions(self, conditions, condition_tables=['Condition'], schema='experiment', hsh='cond_hash', priority=5):
        fields, hash_dict = list(), dict()
        for ctable in condition_tables:
            table = rgetattr(eval(schema), ctable)
            fields += list(table().heading.names)
        for cond in conditions:
            key = {sel_key: cond[sel_key] for sel_key in fields if sel_key != hsh and sel_key in cond}  # find all dependant fields and generate hash
            cond.update({hsh: make_hash(key)})
            hash_dict[cond[hsh]] = cond[hsh]
            for ctable in condition_tables:  # insert dependant condition tables
                core = [field for field in rgetattr(eval(schema), ctable).primary_key if field != hsh]
                fields = [field for field in rgetattr(eval(schema), ctable).heading.names]
                if not np.all([np.any(np.array(k) == list(cond.keys())) for k in fields]): continue # only insert complete tuples
                if core and hasattr(cond[core[0]], '__iter__'):
                    for idx, pcond in enumerate(cond[core[0]]):
                        cond_key = {k: cond[k] if type(cond[k]) in [int, float, str] else cond[k][idx] for k in fields}
                        self.logger.put(table=ctable, tuple=cond_key, schema=schema, priority=priority)
                else: self.logger.put(table=ctable, tuple=cond.copy(), schema=schema, priority=priority)
                priority += 1
        return conditions

    def log_recording(self, key):
        recs = self.logger.get(schema='experiment', table='Recording', key=self.logger.trial_key, fields=['rec_idx'])
        rec_idx = 1 if not recs else max(recs)+1
        self.logger.log('Recording', data={**key, 'rec_idx': rec_idx}, schema='experiment')

    def _anti_bias(self, choice_h, un_choices):
        choice_h = np.array([make_hash(c) for c in choice_h[-self.params['bias_window']:]])
        if len(choice_h) < self.params['bias_window']: choice_h = self.choices
        fixed_p = 1 - np.array([np.mean(choice_h == un) for un in un_choices])
        if sum(fixed_p) == 0:  fixed_p = np.ones(np.shape(fixed_p))
        return np.random.choice(un_choices, 1, p=fixed_p/sum(fixed_p))

    def _get_new_cond(self):
        """ Get curr condition & create random block of all conditions """
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
            choice_h = np.int64(np.asarray(self.beh.choice_history)[idx])
            choice_h = [[c, d] for c, d in zip(choice_h, np.asarray(self.dif_h)[idx])]
            if self.iter == 1 or np.size(self.iter) == 0:
                self.iter = self.params['staircase_window']
                perf = np.nanmean(np.greater(rew_h[-self.params['staircase_window']:], 0))
                if   perf >= self.params['stair_up']   and self.cur_dif < max(self.difs):  self.cur_dif += 1
                elif perf < self.params['stair_down'] and self.cur_dif > 1:  self.cur_dif -= 1
                self.logger.update_setup_info({'difficulty': self.cur_dif})
            elif np.size(self.beh.choice_history) and self.beh.choice_history[-1:][0] > 0: self.iter -= 1
            anti_bias = self._anti_bias(choice_h, self.un_choices[self.un_difs == self.cur_dif])
            sel_conds = [i for (i, v) in zip(self.conditions, np.logical_and(self.choices == anti_bias,
                                                       self.difs == self.cur_dif)) if v]
            self.curr_cond = np.random.choice(sel_conds)
            self.dif_h.append(self.cur_dif)
        else:
            print('Selection method not implemented!')
            self.quit = True


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
class Aim(dj.Lookup):
    definition = """
    # Recording aim
    rec_aim              : varchar(16)                  # aim
    ---
    rec_type             : enum('functional','structural','behavior','other') 
    description=""       : varchar(2048)                # description
    """

    contents = [
        ['two-photon', 'functional', 'Classic two-photon scan'],
        ['widefield' , 'functional', 'wide field imaging of caclium fluorescence'],
        ['intrinsic' , 'functional', 'intrinsic imaging'],
        ['patching'  , 'functional', 'patching'],
        ['stack'     , 'structural', 'two-photon stack of images'],
        ['vessels'   , 'structural', 'map of vessels'],
        ['ball'      , 'behavior'  , '2D Navigation on ball'],
        ['eye'       , 'behavior'  , 'eye movements']
    ]


@experiment.schema
class AnesthesiaType(dj.Lookup):
    definition = """
    # Acquisition program
    anesthesia           : varchar(32)                  # anesthesia type
    ---
    description=""       : varchar(2048)                # description
    """
    contents = [
        ['awake'            , 'anesthesia not used'],
        ['isoflurane'       , 'through evaporator' ],
        ['ketamine/xylazine', 'mixtured injected IP'],
    ]


@experiment.schema
class Software(dj.Lookup):
    definition = """
    # Acquisition program
    software             : varchar(64)                  # program identification number
    version              : varchar(10)                  # version of program
    ---
    description=""       : varchar(2048)                # description
    """
    contents = [
        ['PyMouse'  , '0.1'  , 'self generated files'],
        ['Imager'   , '0.1'  , 'Imager recording program'],
        ['OpenEphys', '0.5.4', 'Neuropixel recordings'],
        ['Miniscope', '1.10' , 'miniscope recordings'],
    ]


@experiment.schema
class SurgeryType(dj.Lookup):
    definition = """
    # Surgery types
    type                 : varchar(16)                  # aim
    ---
    description=""       : varchar(2048)                # description
    """
    contents = [
        ['implant'  , 'Head implant'],
        ['thinning' , 'Scull thinning for imaging'],
        ['window'   , 'Scull window creation'],
        ['injection', 'Viral injection'],
        ['burrhole' , 'Burr hole creation'],
    ]


@experiment.schema
class Surgery(dj.Manual):
    definition = """
    # Surgery information
    animal_id            : smallint UNSIGNED            # animal id
    timestamp            : timestamp                    # timestamp
    ---
    user_name            : varchar(16)                  # user performing the surgery
    ->SurgeryType      
    note=null            : varchar(2048)                # surgery notes
    """


@experiment.schema
class Anesthesia(dj.Manual):
    definition = """
    # Excluded sessions
    animal_id                   : smallint UNSIGNED  # animal id
    timestamp                   : timestamp          # timestamp
    ---
    -> AnesthesiaType
    dose=""                     : varchar(10)        # anesthesia dosage
    note=null                   : varchar(2048)      # anesthesia notes
    """


@experiment.schema
class Session(dj.Manual):
    definition = """
    # Session info
    animal_id            : smallint UNSIGNED            # animal id
    session              : smallint UNSIGNED            # session number
    ---
    -> SetupConfiguration
    -> AnesthesiaType
    user_name            : varchar(16)                  # user performing the experiment
    setup=null           : varchar(256)                 # computer id
    session_tmst         : timestamp                    # session timestamp
    """

    class Protocol(dj.Part):
        definition = """
        # Protocol info
        -> Session
        ---
        protocol_name        : varchar(256)                 # protocol filename
        protocol_file        : blob                         # protocol text file
        git_hash             : varchar(32)                  # github hash
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

    class Anesthetized(dj.Part):
        definition = """
        # Anesthetized sessions
        -> Session
        -> Anesthesia
        """


@experiment.schema
class Recording(dj.Manual):
    definition = """
    # File session info
    -> Session
    rec_idx              : smallint UNSIGNED         # unique recording index
    ---
    -> Aim
    -> Software
    filename=null        : varchar(256)              # file
    source_path=null     : varchar(512)              # local path
    target_path=null     : varchar(512)              # shared drive path
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

    def getGroups(self):
        odor_flag = (len(Trial & OdorCond.Port() & self) > 0)  # filter trials by hash number of odor
        movie_flag = (len(Trial & MovieCond & self) > 0)  # filter trials by hash number of movies
        obj_flag = (len(Trial & ObjectCond & self) > 0)  # filter trials by hash number of objects

        if obj_flag:
            conditions = (RewardCond() * ObjectCond() & (Trial & self)).proj(
                movie_duration='0', probe='probe', dutycycle='0', odor_duration='0', obj_duration='obj_dur')
        elif movie_flag and odor_flag:
            conditions = (RewardCond() * MovieCond() * (OdorCond.Port() & 'delivery_port=1') \
                          * OdorCond() & (Trial & self)).proj(movie_duration='movie_duration', dutycycle='dutycycle',
                                                              odor_duration='odor_duration', probe='probe',
                                                              obj_duration='0')
        elif not movie_flag and odor_flag:
            conditions = (RewardCond() * (OdorCond.Port() & 'delivery_port=1') * OdorCond() & (Trial & self)).proj(
                movie_duration='0', dutycycle='dutycycle', odor_duration='odor_duration', probe='probe',
                obj_duration='0')
        elif movie_flag and not odor_flag:
            conditions = (RewardCond() * MovieCond() & (Trial & self)).proj(
                movie_duration='movie_duration', probe='probe', dutycycle='0', odor_duration='0', obj_duration='0')
        else:
            return []

        uniq_groups, groups_idx = np.unique(
            [cond.astype(int) for cond in
             conditions.fetch('movie_duration', 'dutycycle', 'odor_duration', 'obj_duration', 'probe')],
            axis=1, return_inverse=True)
        conditions = conditions.fetch()
        condition_groups = [conditions[groups_idx == group] for group in set(groups_idx)]
        return condition_groups


@experiment.schema
class Trial(dj.Manual):
    definition = """
    # Trial information
    -> Session
    trial_idx            : smallint UNSIGNED         # unique trial index
    ---
    -> Condition
    time                 : int                       # start time from session start (ms)
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

    def plotDifficulty(self, **kwargs):
        conds = (self * Condition()).fetch('cond_tuple')
        min_difficulty = np.min([cond['difficulty'] for cond in conds])

        params = {'probe_colors': [[1, 0, 0], [0, .5, 1]],
                  'trial_bins': 10,
                  'range': 0.9,
                  'xlim': (-1,),
                  'ylim': (min_difficulty - 0.6,), **kwargs}

        def plot_trials(trials, **kwargs):
            conds, trial_idxs = ((Trial & trials) * Condition()).fetch('cond_tuple', 'trial_idx')
            offset = ((trial_idxs - 1) % params['trial_bins'] - params['trial_bins'] / 2) * params['range'] * 0.1
            difficulties = [cond['difficulty'] for cond in conds]
            plt.scatter(trial_idxs, difficulties + offset, zorder=10, **kwargs)

        # correct trials
        correct_trials = ((LiquidDelivery * self).proj(
            selected='ABS(time - end_time)<200 AND (time - start_time)>0') & 'selected > 0')

        # missed trials
        missed_trials = (self & AbortedTrial).proj()

        # incorrect trials
        incorrect_trials = ((self - correct_trials) - missed_trials).proj()
        print('correct: {}, incorrect: {}, missed: {}'.format(len(correct_trials), len(incorrect_trials),
                                                              len(missed_trials)))
        print('correct: {}, incorrect: {}, missed: {}'.format(len(np.unique(correct_trials.fetch('trial_idx'))),
                                                              len(np.unique(incorrect_trials.fetch('trial_idx'))),
                                                              len(np.unique(missed_trials.fetch('trial_idx')))))

        # plot trials
        fig = plt.figure(figsize=(10, 5), tight_layout=True)
        plot_trials(correct_trials, s=4, c=np.array(params['probe_colors'])[correct_trials.fetch('probe') - 1])
        plot_trials(incorrect_trials, s=4, marker='o', facecolors='none', edgecolors=[.3, .3, .3], linewidths=.5)
        plot_trials(missed_trials, s=.1, c=[[0, 0, 0]])

        # plot info
        plt.xlabel('Trials')
        plt.ylabel('Difficulty')
        plt.title('Animal:%d  Session:%d' % (Session() & self).fetch1('animal_id', 'session'))
        plt.yticks(range(int(min(plt.gca().get_ylim())), int(max(plt.gca().get_ylim())) + 1))
        plt.ylim(params['ylim'][0])
        plt.xlim(params['xlim'][0])
        plt.gca().xaxis.set_ticks_position('none')
        plt.gca().yaxis.set_ticks_position('none')
        plt.box(False)
        plt.show()


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


