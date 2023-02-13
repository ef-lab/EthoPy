from core.Logger import *
import itertools
import matplotlib.pyplot as plt
import warnings

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
    curr_state, curr_trial, total_reward, cur_dif, flip_count, states, stim, sync, cur_dif_h = '', 0, 0, 0, 0, dict(), False, False, []
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
        self.transition_cond = ExperimentClass.TransitionMethods(transition_method=self.params['transition_method'], 
                                                                sliding=self.params['sliding'],
                                                                criterion_method=self.params['criterion_method'],
                                                                params=self.params)

        self.select_cond  = ExperimentClass.SelectConditions(experiment_class=self, selection_type=self.params['selection_type'])
        np.random.seed(0)   # fix random seed for repeatability, it can be overidden in the conf file

    def start(self):
        states = dict()
        for state in self.__class__.__subclasses__():  # Initialize states
            states.update({state().__class__.__name__: state(self)})
        state_control = self.StateMachine(states)
        self.interface.set_running_state(True)
        state_control.run()

    def stop(self):
        self.stim.exit()
        self.beh.exit()
        self.logger.ping(0)
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
        """_get_new_cond selects the condition for the trial starts 
        at prepare_trial which is called most commonly on the PreTrial

        _extended_summary_
        It is consists of 2 main steps:
        1. according to transition define the cur_block
        2. select the correct condition based on block and the type of selection 
        """
        # if the window has pass checks if the session must move on next difficulty
        self.cur_dif = self.transition_cond.select(self.beh.choice_history,
                                                    self.beh.reward_history, 
                                                    self.beh.punish_history, 
                                                    self.cur_dif, self.difs)
        self.logger.update_setup_info({'difficulty': self.cur_dif})
        self.curr_cond = self.select_cond.select()
        
    class TransitionMethods():
        def __init__(self, transition_method:str="staircase", 
                    sliding:bool=True, 
                    criterion_method:str="performace",
                    params=None):

                # implemented transition methods
                self.transition_dict = {"staircase" : self.staircase,
                                        "None"       : lambda *var: None}
                self.sliding = sliding
                self.params = params
                self.window_size = params['window_size']
                self.block_upgrade = params['block_upgrade']
                self.block_downgrade = params['block_downgrade']
                
                self.criterion_method = criterion_method
                self.transition_method = self.transition_dict.get(transition_method, self.NonImplemented)
                if transition_method!="None" and transition_method!=criterion_method: 
                    raise Exception("if transition_method!=None you must specify a criterion_method")
                    
                self.block_counter = 0 # count the the block size at every trial

        def select(self, choice_history, reward_history, punish_history, cur_dif, difs):
            # check if it's not the first trial and the trial=(reward or punish) 
            trial_choice = np.size(choice_history) and choice_history[-1:][0] > 0

            if self.window(trial_choice):
                diff_temp = cur_dif
                criterion_result = self.criterion_method(self.criterion_method, reward_history, punish_history)
                cur_dif = self.transition_method(criterion_result, cur_dif, difs)
                if diff_temp!=cur_dif and self.sliding==True: self.block_counter=0 # when change block reset counter
                print("criterion_result ",criterion_result)
            print("cur_dif ", cur_dif)
            print("self.block_counter ", self.block_counter)
            return cur_dif

        def window(self, trial_choice, *args):
            """window if the size of trials(reward or punish) are equal 
                to window size return True
            
            Args:
                trial_choice(bool): check if it's not the first trial and the trial=reward or punish 
            Returns:
                bool:
            """
            if trial_choice: self.block_counter += 1
            if self.block_counter>=self.window_size:
                if self.sliding==False: self.block_counter=0
                return True
            return False
        
        def staircase(self, criterion_result, cur_dif, difs):
            """staircase increase or decrease the difficulty based on criterion until 
                difficulty is max
            If difficukty pass 0 it cannot return. Negative values can also be used.
            Args:
                criterion_result (float): the result of the criterion 
                cur_dif (int): current difficulty
                difs (list): all the difficulties

            Returns:
                (int): the next difficulty
            """
            if   criterion_result >= self.block_upgrade   and cur_dif < max(difs): cur_dif = self.succeed_block(cur_dif, "Upgrade")
            elif criterion_result <self.block_downgrade and cur_dif > 1: cur_dif = self.succeed_block(cur_dif, "Downgrade")
            return cur_dif

        def criterion_method(self, criterion_method, reward_history, punish_history)->float:
            """criterion_method return a float based on criterion_result
            Args:
                criterion (str): 
                reward_history (list): list with rewards
                punish_history (list): list with bool if trial is punish else nan

            Raises:
                NotImplementedError: if criterion is not implemented

            Returns:
                float:
            """
            if criterion_method == "performance":
                # check the performace of the last n=window_size trials
                idx = np.logical_or(~np.isnan(reward_history), ~np.isnan(punish_history))
                rew_h  = np.asarray(reward_history)[idx]
                return np.nanmean(np.greater(rew_h[-self.window_size:], 0))
            elif criterion_method == "None":
                return True
            else:
                raise NotImplementedError("criterion_method method on TransitionMethods class is not implemented!")
        
        def succeed_block(self,cur_dif, next_type='Upgrade'):
            """this method is responsible for the next_type
            for example it can be a model respoble for this"""
            if next_type=="Upgrade":
                return cur_dif+1
            elif next_type=="Downgrade":
                return cur_dif-1

        def NonImplemented(self,*args):
            raise NotImplementedError("TransitionMethods method is Not Implemented")


    class SelectConditions():
        def __init__(self, experiment_class, selection_type):
            """__init__ 

            Args:
                experiment_class (object): 
                selection_type (str): type of selection(fix,random,antibias,block)
            """
            self.exp_cls = experiment_class
            self.select_dict = {"fix"     : self.fix,
                                "random"   : self.random,
                                "antibias" : self.antibias,
                                "block"    : self.block}
            self.select_cond_func = self.select_dict.get(selection_type, self.Custom)

        def select(self):
            return self.select_cond_func()
        
        def fix(self):
            """fix select conditions in fix order based in configuration until they finish
            """
            return [] if len(self.exp_cls.conditions) == 0 else self.exp_cls.conditions.pop()

        def random(self):
            """random select a condtion randomnly according to the difficulty
            """
            sel_conds = [i for (i, v) in zip(self.exp_cls.conditions, self.exp_cls.difs == self.exp_cls.cur_dif) if v]
            return np.random.choice(sel_conds)
            
        def antibias(self):
            """antibias select randomly from the conditions contractive to the bias of the animal
            """
            # find indexes for reward/punish only trials
            idx = np.logical_or(~np.isnan(self.exp_cls.beh.reward_history), ~np.isnan(self.exp_cls.beh.punish_history))         
            choice_h = np.int64(np.asarray(self.exp_cls.beh.choice_history)[idx])
            # create a list with choice and difficulty for previous trials
            choice_h = [[c, d] for c, d in zip(choice_h, np.asarray(self.exp_cls.dif_h)[idx])]
            #use anti_bias to select next condition
            anti_bias = self.exp_cls._anti_bias(choice_h, self.exp_cls.un_choices[self.exp_cls.un_difs == self.exp_cls.cur_dif])
 
            sel_conds = [i for (i, v) in zip(self.exp_cls.conditions, np.logical_and(self.exp_cls.choices == anti_bias,
                                                    self.exp_cls.difs == self.exp_cls.cur_dif)) if v]
            self.exp_cls.dif_h.append(self.exp_cls.cur_dif)
            return np.random.choice(sel_conds)

        def block(self):
            """block select all conditions randomly one by one and when they finish repeat
            """
            if np.size(self.exp_cls.iter) == 0 or np.size(self.exp_cls.beh.choice_history)==0: 
                self.exp_cls.iter = np.random.permutation(np.size(self.exp_cls.conditions))
            cond = self.exp_cls.conditions[self.iter[0]]
            self.exp_cls.iter = self.exp_cls.iter[1:]
            return cond

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
        time                : int               # time from session start (ms)
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
class SetupConfiguration(dj.Lookup):
    definition = """
    # Setup configuration
    setup_conf_idx           : tinyint                                            # configuration version
    ---
    interface                : enum('DummyPorts','RPPorts', 'PCPorts', 'RPVR')    # The Interface class for the setup
    discription              : varchar(256)
    """

    class Port(dj.Part):
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

    class Screen(dj.Part):
        definition = """
        # Screen information
        screen_idx               : tinyint
        -> SetupConfiguration
        ---
        intensity                : tinyint UNSIGNED 
        monitor_distance         : float
        monitor_center_x         : float
        monitor_center_y         : float
        monitor_aspect           : float
        monitor_size             : float
        fps                      : tinyint UNSIGNED
        resolution_x             : smallint
        resolution_y             : smallint
        discription              : varchar(256)
        reward_color             : tinyblob
        punish_color             : tinyblob
        ready_color              : tinyblob
        background_color         : tinyblob
        start_color              : tinyblob
        """

    class Ball(dj.Part):
        definition = """
        # Ball information
        -> SetupConfiguration
        ---
        ball_radius=0.125        : float                   # in meters
        material="styrofoam"     : varchar(64)             # ball material
        coupling="bearings"      : enum('bearings','air')  # mechanical coupling
        discription              : varchar(256)
        """

    class Speaker(dj.Part):
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

    class Camera(dj.Part):
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

    contents = [[0, 'calibrate_ports.py', 'Test calibration protocol', '2021-01-01 00:00:00'],
                [1, 'free_water.py'     , 'Test free water protocol', '2021-01-01 00:00:00'],
                [2, 'grating_test.py'   , 'Test grating discimination protocol', '2021-01-01 00:00:00']]


@mice.schema
class MouseWeight(dj.Manual):
    definition = """
    animal_id                       : int unsigned                 # id number
    timestamp=CURRENT_TIMESTAMP     : timestamp                    # timestamp of weight
    ---
    weight                          : double(5,2)                  # weight in grams
    """
