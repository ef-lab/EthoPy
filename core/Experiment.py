from core.Logger import *
import itertools
import matplotlib.pyplot as plt
from utils.helper_functions import generate_conf_list

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
    curr_state, curr_trial, total_reward, cur_dif, flip_count, states, stim, sync = '', 0, 0, 0, 0, dict(), False, False
    un_choices, difs, iter, curr_cond, dif_h, stims, response, resp_ready = [], [], [], dict(), [], dict(), [], False
    required_fields, default_key, conditions, cond_tables, quit, running = [], dict(), [], [], False, False

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
        self.running = False
        self.conditions, self.iter, self.quit, self.curr_cond, self.dif_h, self.stims, self.curr_trial = [], [], False, dict(), [], dict(),0
        if "setup_conf_idx" not in self.default_key: self.default_key["setup_conf_idx"] = 0
        self.params = {**self.default_key, **session_params}
        self.logger = logger
        self.logger.log_session({**self.default_key, **session_params, 'experiment_type': self.cond_tables[0]},
                                log_protocol=True)
        self.beh = BehaviorClass()
        self.beh.setup(self)
        self.interface = self.beh.interface
        self.session_timer = Timer()
        np.random.seed(0)   # fix random seed for repeatability, it can be overidden in the conf file

    def start(self):
        states = dict()
        for state in self.__class__.__subclasses__():  # Initialize states
            states.update({state().__class__.__name__: state(self)})
        state_control = self.StateMachine(states)
        self.interface.set_running_state(True)
        state_control.run()

    def stop(self):
        self.release()
        self.stim.exit()
        self.beh.exit()
        self.logger.ping(0)
        if self.sync:
            while self.interface.is_recording():
                print('Waiting for recording to end...')
                time.sleep(1)
        self.logger.closeDatasets()
        self.running = False

    def release(self):
        if self.interface.camera:
            if self.interface.camera.recording.is_set(): self.interface.camera.stop_rec()
            self.interface.camera_Process.join()

    def is_stopped(self):
        self.quit = self.quit or self.logger.setup_status in ['stop', 'exit']
        if self.quit and self.logger.setup_status not in ['stop', 'exit']:
            self.logger.update_setup_info({'status': 'stop'})
        if self.quit: self.running = False
        return self.quit

    def make_conditions(self, stim_class, conditions, stim_periods=None):
        stim_name = stim_class.__class__.__name__
        if stim_name not in self.stims:
            stim_class.init(self)
            stim_name = stim_class.__class__.__name__
            self.stims[stim_name] = stim_class
        conditions.update({'stimulus_class': stim_name})
        if not stim_periods:
            conditions = self.stims[stim_name].make_conditions(factorize(conditions))
        else:
            cond = {}
            for i in range(len(stim_periods)):
                cond[stim_periods[i]] = self.stims[stim_name].make_conditions(conditions=factorize(conditions[stim_periods[i]]))
                conditions[stim_periods[i]] = []
            all_cond = [cond[stim_periods[i]] for i in range(len(stim_periods))]
            for comb in list(itertools.product(*all_cond)):
                for i in range(len(stim_periods)): conditions[stim_periods[i]].append(comb[i])
            conditions = factorize(conditions)

        conditions = self.log_conditions(**self.beh.make_conditions(conditions))
        for cond in conditions:
            assert np.all([field in cond for field in self.required_fields])
            cond.update({**self.default_key, **self.params, **cond, 'experiment_class': self.cond_tables[0]})
        cond_tables = ['Condition.' + table for table in self.cond_tables]
        conditions = self.log_conditions(conditions, condition_tables=['Condition'] + cond_tables)
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
        if not self.curr_cond or self.logger.thread_end.is_set():
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
        if not self.running:
            self.running = True

    def name(self): return type(self).__name__

    def log_conditions(self, conditions, condition_tables=['Condition'], schema='experiment', hsh='cond_hash', priority=2):
        fields_key, hash_dict = list(), dict()
        for ctable in condition_tables:
            table = rgetattr(eval(schema), ctable)
            fields_key += list(table().heading.names)
        for cond in conditions:
            insert_priority = priority
            key = {sel_key: cond[sel_key] for sel_key in fields_key if sel_key != hsh and sel_key in cond}  # find all dependant fields and generate hash
            cond.update({hsh: make_hash(key)})
            hash_dict[cond[hsh]] = cond[hsh]
            for ctable in condition_tables:  # insert dependant condition tables
                core = [field for field in rgetattr(eval(schema), ctable).primary_key if field != hsh]
                fields = [field for field in rgetattr(eval(schema), ctable).heading.names]
                if not np.all([np.any(np.array(k) == list(cond.keys())) for k in fields]):
                    if self.logger.manual_run: print('skipping ', ctable)
                    continue # only insert complete tuples
                if core and hasattr(cond[core[0]], '__iter__'):
                    for idx, pcond in enumerate(cond[core[0]]):
                        cond_key = {k: cond[k] if type(cond[k]) in [int, float, str] else cond[k][idx] for k in fields}
                        self.logger.put(table=ctable, tuple=cond_key, schema=schema, priority=insert_priority)
                else: self.logger.put(table=ctable, tuple=cond.copy(), schema=schema, priority=insert_priority)
                insert_priority += 1
        return conditions

    def log_recording(self, key):
        recs = self.logger.get(schema='recording', table='Recording', key=self.logger.trial_key, fields=['rec_idx'])
        rec_idx = 1 if not recs else max(recs)+1
        self.logger.log('Recording', data={**key, 'rec_idx': rec_idx}, schema='recording')

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
        elif self.params['trial_selection'] == 'biased':
            idx = [~np.isnan(ch).any() for ch in self.beh.choice_history]
            choice_h = np.asarray(self.beh.choice_history)
            anti_bias = self._anti_bias(choice_h[idx], self.un_choices)
            selected_conditions = [i for (i, v) in zip(self.conditions, self.choices == anti_bias) if v]
            self.curr_cond = np.random.choice(selected_conditions)
        elif self.params['trial_selection'] == 'staircase':
            idx = np.logical_or(~np.isnan(self.beh.reward_history), ~np.isnan(self.beh.punish_history))
            rew_h = np.asarray(self.beh.reward_history); rew_h = rew_h[idx]
            choice_h = np.int64(np.asarray(self.beh.choice_history)[idx])
            choice_h = [[c, d] for c, d in zip(choice_h, np.asarray(self.dif_h)[idx])]
            if self.iter == 1 or np.size(self.iter) == 0:
                if (self.beh.choice_history[-1:][0]>0 if np.size(self.beh.choice_history)!=0 else True):
                    self.iter = self.params['staircase_window']
                    perf = np.nanmean(np.greater(rew_h[-self.params['staircase_window']:], 0))
                    if   perf >= self.params['stair_up']   and self.cur_dif < max(self.difs):  self.cur_dif += 1
                    elif perf < self.params['stair_down'] and self.cur_dif > 1 and self.cur_dif > min(self.difs):
                        self.cur_dif -= 1
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
class Session(dj.Manual):
    definition = """
    # Session info
    animal_id                        : smallint UNSIGNED            # animal id
    session                          : smallint UNSIGNED            # session number
    ---
    user_name                        : varchar(16)                  # user performing the experiment
    setup=null                       : varchar(256)                 # computer id
    experiment_type                  : varchar(128)
    session_tmst=CURRENT_TIMESTAMP   : timestamp                    # session timestamp
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
        # Trial state timestamps
        -> Trial
        time			    : int 	            # time from session start (ms)
        state               : varchar(64)
        """

    def getGroups(self):
        mts_flag = (np.unique((Condition & self).fetch('experiment_class')) == ['MatchToSample'])
        mp_flag = (np.unique((Condition & self).fetch('experiment_class')) == ['MatchPort']) #only olfactory so far
        print(mts_flag, mp_flag)

        if mts_flag:
            conditions = self * ((stimulus.StimCondition.Trial() & 'period = "Cue"').proj('stim_hash', stime = 'start_time') & self) *\
                         stimulus.Panda.Object() * ((behavior.BehCondition.Trial().proj(btime = 'time') & self) * behavior.MultiPort.Response())
            uniq_groups, groups_idx = np.unique(
                [cond.astype(int) for cond in
                 conditions.fetch('obj_id', 'response_port', order_by=('trial_idx'))],
                axis=1, return_inverse=True)
        elif mp_flag: #only olfactory so far
            conditions = self * (stimulus.StimCondition.Trial().proj('stim_hash', stime = 'start_time') & self) *\
                         stimulus.Olfactory.Channel() * ((behavior.BehCondition.Trial().proj(btime = 'time') & self) * behavior.MultiPort.Response())
            uniq_groups, groups_idx = np.unique(
                [cond.astype(int) for cond in
                 conditions.fetch('odorant_id', 'response_port', order_by=('trial_idx'))],
                axis=1, return_inverse=True)
        else:
            print('no conditions!')
            return []

        conditions = conditions.fetch(order_by = 'trial_idx')
        condition_groups = [conditions[groups_idx == group] for group in set(groups_idx)]
        return condition_groups
    
    def plotDifficulty(self, **kwargs):
        mts_flag = (np.unique((Condition & self).fetch('experiment_class')) == ['MatchToSample'])
        mp_flag = (np.unique((Condition & self).fetch('experiment_class')) == ['MatchPort']) #only olfactory so far

        if mts_flag:
            cond_class = experiment.Condition.MatchToSample()
        elif mp_flag:
            cond_class = experiment.Condition.MatchPort()
        else:
            print('what experiments class?')
            return []

        difficulties = (self * cond_class).fetch('difficulty')
        min_difficulty = np.min(difficulties)
        
        params = {'probe_colors': [[1, 0, 0], [0, .5, 1]],
                  'trial_bins': 10,
                  'range': 0.9,
                  'xlim': (-1,),
                  'ylim': (min_difficulty - 0.6,), **kwargs}

        def plot_trials(trials, **kwargs):
            difficulties, trial_idxs = ((self & trials) * cond_class).fetch('difficulty', 'trial_idx')
            offset = ((trial_idxs - 1) % params['trial_bins'] - params['trial_bins'] / 2) * params['range'] * 0.1
            plt.scatter(trial_idxs, difficulties + offset, zorder=10, **kwargs)

        # correct trials
        correct_trials = (self & behavior.Rewards.proj(rtime = 'time')).proj()
    
        # missed trials
        missed_trials = Trial.Aborted() & self

        # incorrect trials
        incorrect_trials = (self - missed_trials - correct_trials).proj()
        
        print('correct: {}, incorrect: {}, missed: {}'.format(len(correct_trials), len(incorrect_trials),
                                                              len(missed_trials)))
        print('correct: {}, incorrect: {}, missed: {}'.format(len(np.unique(correct_trials.fetch('trial_idx'))),
                                                              len(np.unique(incorrect_trials.fetch('trial_idx'))),
                                                              len(np.unique(missed_trials.fetch('trial_idx')))))

        # plot trials
        fig = plt.figure(figsize=(10, 5), tight_layout=True)
        plot_trials(correct_trials, s=4, c=np.array(params['probe_colors'])[(correct_trials * behavior.BehCondition.Trial() * behavior.MultiPort.Response()).fetch('response_port', order_by='trial_idx') - 1])
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
class SetupConfiguration(dj.Manual,  dj.Lookup):
    definition = """
    # Setup configuration
    setup_conf_idx           : tinyint                                            # configuration version
    ---
    interface                : enum('DummyPorts','RPPorts', 'PCPorts', 'RPVR')    # The Interface class for the setup
    discription              : varchar(256)
    """

    contents = [[0, 'DummyPorts', 'Simulation'],]

    class Port(dj.Part, dj.Lookup):
        definition = """
        # Probe identity
        port                     : tinyint                      # port id
        type="Lick"              : enum('Lick','Proximity')     # port type
        -> SetupConfiguration
        ---
        ready=0                  : tinyint                      # ready flag
        response=0               : tinyint                      # response flag
        reward=0                 : tinyint                      # reward flag
        invert=0                 : tinyint                      # invert flag
        discription              : varchar(256)
        """

        contents = [[1,'Lick', 0, 0 , 1, 1, 0, 'probe'],
                    [2,'Lick', 0, 0 , 1, 1, 0, 'probe'],
                    [3,'Proximity', 0, 1 , 0, 0, 0, 'probe']]

    class Screen(dj.Part, dj.Lookup):
        definition = """
        # Screen information
        screen_idx               : tinyint
        -> SetupConfiguration
        ---
        intensity                : tinyint UNSIGNED 
        distance                 : float
        center_x                 : float
        center_y                 : float
        aspect                   : float
        size                     : float
        fps                      : tinyint UNSIGNED
        resolution_x             : smallint
        resolution_y             : smallint
        description              : varchar(256)
        fullscreen               : varchar(256)
        """

        contents = [[1,0, 64, 5.0, 0, -0.1, 1.66, 7.0, 30, 800, 480, 'Simulation', 0],]

    class Ball(dj.Part, dj.Lookup):
        definition = """
        # Ball information
        -> SetupConfiguration
        ---
        ball_radius=0.125        : float                   # in meters
        material="styrofoam"     : varchar(64)             # ball material
        coupling="bearings"      : enum('bearings','air')  # mechanical coupling
        discription              : varchar(256)
        """

    class Speaker(dj.Part, dj.Lookup):
        definition = """
        # Speaker information
        speaker_idx             : tinyint
        -> SetupConfiguration
        ---
        sound_freq=10000        : int           # in Hz
        duration=500            : int           # in ms
        volume=50               : tinyint       # 0-100 percentage
        discription             : varchar(256)
        """

    class Camera(dj.Part, dj.Lookup):
        definition = """
        # Camera information
        camera_idx               : tinyint
        -> SetupConfiguration
        ---
        fps                      : tinyint UNSIGNED
        resolution_x             : smallint
        resolution_y             : smallint
        shutter_speed            : smallint
        iso                      : smallint
        file_format              : varchar(256)
        video_aim                : enum('eye','body','openfield')
        discription              : varchar(256)
        """

@experiment.schema
class Control(dj.Lookup):
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
    # Experiment parameters
    task_idx                    : int                          # task identification number
    ---
    protocol                    : varchar(4095)                # stimuli to be presented (array of dictionaries)
    description=""              : varchar(2048)                # task description
    timestamp                   : timestamp    
    """

    contents = generate_conf_list("conf/")

@mice.schema
class MouseWeight(dj.Manual):
    definition = """
    animal_id                       : int unsigned                 # id number
    timestamp=CURRENT_TIMESTAMP     : timestamp                    # timestamp of weight
    ---
    weight                          : double(5,2)                  # weight in grams
    """
