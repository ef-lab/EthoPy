import numpy, socket
from utils.Timer import *
from Database import *
from queue import Queue
import time as systime
import datetime
from threading import Lock
import threading


class Logger:
    """ This class handles the database logging"""

    def __init__(self):
        self.session_key = dict()
        self.setup = socket.gethostname()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        self.ip = s.getsockname()[0]
        print(self.ip)
        self.init_params()
        self.thread_runner = threading.Timer(0.1, self.inserter)  # max insertion rate of 10 events/sec
        self.thread_runner.start()
        self.thread_lock = Lock()

    def init_params(self):
        self.last_trial = 0
        self.queue = Queue()
        self.timer = Timer()
        self.trial_start = 0
        self.curr_cond = []
        self.task_idx = []
        self.reward_amount = []

    def log_session(self):
        """Logs session"""
        pass

    def log_conditions(self, condition_table):
        """Logs conditions"""
        pass

    def start_trial(self, cond_idx):
        self.trial_start = self.timer.elapsed_time()

    def log_trial(self, last_flip_count=0):
        """Log experiment trial"""
        pass

    def log_setup(self):
        """Log setup information"""
        pass

    def update_setup_state(self, state):
        pass

    def get_setup_state(self):
        pass

    def get_setup_task(self):
        pass

    def get_session_key(self):
        return self.session_key

    def ping(self):
        """update timestamp"""
        pass

    def inserter(self):
        if not self.queue.empty():
            self.thread_lock.acquire()
            item = self.queue.get()
            item['table'].insert1(item['tuple'], ignore_extra_fields=True)
            self.thread_lock.release()


class RPLogger(Logger):
    """ This class handles the database logging for Raspberry pi"""

    def __init__(self):
        self.session_key = dict()
        self.setup = socket.gethostname()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        self.ip = s.getsockname()[0]
        print(self.ip)
        self.init_params()
        self.thread_runner = threading.Timer(0.1, self.inserter)  # max insertion rate of 10 events/sec
        self.thread_runner.start()
        self.thread_lock = Lock()

    def init_params(self):
        self.last_trial = 0
        self.queue = Queue()
        self.timer = Timer()
        self.trial_start = 0
        self.curr_cond = []
        self.task_idx = []
        self.reward_amount = []


    def get_protocol(self):
        self.thread_lock.acquire()
        task_idx = (SetupControl() & dict(setup=self.setup)).fetch1('task_idx')
        protocol = (Task() & dict(task_idx=task_idx)).fetch1('protocol')
        self.thread_lock.release()
        return protocol

    def log_session(self, task_params):
        self.thread_lock.acquire()
        animal_id, task_idx = (SetupControl() & dict(setup=self.setup)).fetch1('animal_id', 'task_idx')
        self.task_idx = task_idx

        # create session key
        self.session_key['animal_id'] = animal_id
        last_sessions = (Session() & self.session_key).fetch('session_id')
        if numpy.size(last_sessions) == 0:
            last_session = 0
        else:
            last_session = numpy.max(last_sessions)
        self.session_key['session_id'] = last_session + 1

        # get task parameters for session table
        key = dict(self.session_key.items() | task_params.items())
        key['setup'] = self.setup
        self.queue.put(dict(table=Session(), tuple=key))
        self.reward_amount = task_params['reward_amount']/1000  # convert to ml

        # start session time
        self.timer.start()
        (SetupControl() & dict(setup=self.setup))._update('current_session', self.session_key['session_id'])
        (SetupControl() & dict(setup=self.setup))._update('last_trial', 0)
        (SetupControl() & dict(setup=self.setup))._update('total_liquid', 0)
        self.thread_lock.release()

    def log_conditions(self, condition_table, conditions):
        self.thread_lock.acquire()

        # make sure condition_table is a list
        if numpy.size(condition_table) < 2:
            condition_table = [condition_table]

        # iterate through all conditions and insert
        cond_idx = 0
        probes = numpy.empty(numpy.size(conditions))
        for cond in conditions:
            cond_idx += 1
            cond.update({'cond_idx': cond_idx})
            self.queue.put(dict(table=Condition(), tuple=dict(self.session_key, cond_idx=cond_idx)))
            if 'probe' in cond:
                probes[cond_idx-1] = cond['probe']
                self.queue.put(dict(table=RewardCond(), tuple=dict(self.session_key,
                                                                   cond_idx=cond_idx,
                                                                   probe=probes[cond_idx-1])))
            for condtable in condition_table:
                condtable = eval(condtable)
                self.queue.put(dict(table=condtable(), tuple=dict(cond.items() | self.session_key.items(),
                                                                    cond_idx=cond_idx)))
        self.thread_lock.release()
        return numpy.array(probes)

    def start_trial(self, cond_idx):
        self.curr_cond = cond_idx
        self.trial_start = self.timer.elapsed_time()

        # return condition key
        return dict(self.session_key, cond_idx=cond_idx)

    def log_trial(self, last_flip_count=0):

        timestamp = self.timer.elapsed_time()
        trial_key = dict(self.session_key,
                         trial_idx=self.last_trial+1,
                         cond_idx=self.curr_cond,
                         start_time=self.trial_start,
                         end_time=timestamp,
                         last_flip_count=last_flip_count)
        self.queue.put(dict(table=Trial(), tuple=trial_key))
        self.last_trial += 1

        # insert ping
        self.thread_lock.acquire()
        (SetupControl() & dict(setup=self.setup))._update('last_trial', self.last_trial)
        self.thread_lock.release()
        self.ping()


    def log_liquid(self, probe):
        self.thread_lock.acquire()
        timestamp = self.timer.elapsed_time()
        self.queue.put(dict(table=LiquidDelivery(), tuple=dict(self.session_key, time=timestamp, probe=probe)))
        rew = (LiquidDelivery & self.session_key).__len__()*(Session() & self.session_key).fetch1('reward_amount')/1000
        (SetupControl() & dict(setup=self.setup))._update('total_liquid', rew)
        self.thread_lock.release()

    def log_stim(self):
        timestamp = self.timer.elapsed_time()
        self.queue.put(dict(table=StimDelivery(), tuple=dict(self.session_key, time=timestamp)))

    def log_lick(self, probe):
        timestamp = self.timer.elapsed_time()
        self.queue.put(dict(table=Lick(), tuple=dict(self.session_key,
                                                     time=timestamp,
                                                     probe=probe)))

    def log_pulse_weight(self, pulse_dur, probe, pulse_num, weight=0):
        self.thread_lock.acquire()
        cal_key = dict(setup=self.setup, probe=probe, date=systime.strftime("%Y-%m-%d"))
        LiquidCalibration().insert1(cal_key, skip_duplicates=True)
        (LiquidCalibration.PulseWeight() & dict(cal_key, pulse_dur=pulse_dur)).delete_quick()
        LiquidCalibration.PulseWeight().insert1(dict(cal_key,
                                                     pulse_dur=pulse_dur,
                                                     pulse_num=pulse_num,
                                                     weight=weight))
        self.thread_lock.release()

    def log_setup(self):
        self.thread_lock.acquire()
        key = dict(setup=self.setup)

        # update values in case they exist
        if numpy.size((SetupControl() & dict(setup=self.setup)).fetch()):
            key = (SetupControl() & dict(setup=self.setup)).fetch1()
            (SetupControl() & dict(setup=self.setup)).delete_quick()

        # insert new setup
        key['ip'] = self.ip
        key['state'] = 'ready'
        SetupControl().insert1(key)
        self.thread_lock.release()

    def update_setup_state(self, state):
        self.thread_lock.acquire()
        key = (SetupControl() & dict(setup=self.setup)).fetch1()
        in_state = key['state'] == state
        if not in_state:
            (SetupControl() & dict(setup=self.setup))._update('state', state)
        self.thread_lock.release()
        return in_state

    def update_setup_notes(self, note):
        self.thread_lock.acquire()
        (SetupControl() & dict(setup=self.setup))._update('notes', note)
        self.thread_lock.release()

    def get_setup_state(self):
        self.thread_lock.acquire()
        state = (SetupControl() & dict(setup=self.setup)).fetch1('state')
        self.thread_lock.release()
        return state

    def get_setup_task(self):
        self.thread_lock.acquire()
        task = (SetupControl() & dict(setup=self.setup)).fetch1('task')
        self.thread_lock.release()
        return task

    def get_session_key(self):
        return self.session_key

    def get_clip_info(self, curr_cond):
        self.thread_lock.acquire()
        clip_info = (MovieTables.Movie() * MovieTables.Movie.Clip() & curr_cond & self.session_key).fetch1()
        self.thread_lock.release()
        return clip_info

    def sleep(self):
        now = datetime.now()
        start = self.params['start_time'] + now.replace(hour=0, minute=0, second=0)
        stop = self.params['stop_time'] + now.replace(hour=0, minute=0, second=0)
        if stop < start:
            stop = stop + timedelta(days=1)
        if now < start or now > stop:


    def ping(self):
        self.thread_lock.acquire()
        if numpy.size((SetupControl() & dict(setup=self.setup)).fetch()):
            lp = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            (SetupControl() & dict(setup=self.setup))._update('last_ping', lp)
        self.thread_lock.release()


