import numpy, socket, json, os, pandas
from utils.Timer import *
from utils.Generator import *
from queue import Queue
import time as systime
import datetime
from threading import Lock
import threading
from DatabaseTables import *
dj.config["enable_python_native_blobs"] = True


class Logger:
    """ This class handles the database logging"""

    def __init__(self):
        self.last_trial = 0
        self.queue = Queue()
        self.timer = Timer()
        self.trial_start = 0
        self.curr_cond = []
        self.task_idx = []
        self.session_key = dict()
        self.setup = socket.gethostname()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        self.ip = s.getsockname()[0]
        path = os.path.dirname(os.path.abspath(__file__))
        fileobject = open(path + '/dj_local_conf.json')
        connect_info = json.loads(fileobject.read())
        conn2 = dj.Connection(connect_info['database.host'], connect_info['database.user'],
                              connect_info['database.password'])
        self.insert_schema = dj.create_virtual_module('beh.py', 'lab_behavior', connection=conn2)
        self.thread_end = threading.Event()
        self.thread_lock = Lock()
        self.thread_runner = threading.Thread(target=self.inserter)  # max insertion rate of 10 events/sec
        self.thread_runner.start()

    def cleanup(self):
        self.thread_end.set()

    def inserter(self):
        while not self.thread_end.is_set():
            if not self.queue.empty():
                self.thread_lock.acquire()
                item = self.queue.get()
                if 'update' in item:
                    eval('(self.insert_schema.' + item['table'] +
                         '() & item["tuple"])._update(item["field"],item["value"])')
                else:
                    eval('self.insert_schema.'+item['table']+'.insert1(item["tuple"], ignore_extra_fields=True, skip_duplicates=True)')
                self.thread_lock.release()
            else:
                time.sleep(.5)

    def log_setup(self):
        key = dict(setup=self.setup)
        # update values in case they exist
        if numpy.size((SetupControl() & dict(setup=self.setup)).fetch()):
            key = (SetupControl() & dict(setup=self.setup)).fetch1()
            (SetupControl() & dict(setup=self.setup)).delete_quick()

        # insert new setup
        key['ip'] = self.ip
        key['status'] = 'ready'
        SetupControl().insert1(key)

    def log_session(self, session_params, exp_type=''):
        animal_id, task_idx = (SetupControl() & dict(setup=self.setup)).fetch1('animal_id', 'task_idx')
        self.task_idx = task_idx
        self.last_trial = 0

        # create session key
        self.session_key = dict()
        self.session_key['animal_id'] = animal_id
        last_sessions = (Session() & self.session_key).fetch('session')
        if numpy.size(last_sessions) == 0:
            last_session = 0
        else:
            last_session = numpy.max(last_sessions)
        self.session_key['session'] = last_session + 1

        # get task parameters for session table
        key = dict(self.session_key.items())
        key['session_params'] = session_params
        key['setup'] = self.setup
        key['protocol'] = self.get_protocol()
        key['experiment_type'] = exp_type
        self.queue.put(dict(table='Session', tuple=key))

        # start session time
        self.timer.start()
        (SetupControl() & dict(setup=self.setup))._update('current_session', self.session_key['session'])
        (SetupControl() & dict(setup=self.setup))._update('last_trial', 0)
        (SetupControl() & dict(setup=self.setup))._update('total_liquid', 0)

    def log_conditions(self, conditions, condition_tables=['OdorCond', 'MovieCond', 'RewardCond']):
        # iterate through all conditions and insert
        for cond in conditions:
            cond_hash = make_hash(cond)
            self.queue.put(dict(table='Condition', tuple=dict(cond_hash=cond_hash, cond_tuple=cond.copy())))
            cond.update({'cond_hash': cond_hash})
            for condtable in condition_tables:
                self.queue.put(dict(table=condtable, tuple=dict(cond.items())))
        return conditions

    def init_trial(self, cond_hash):
        self.curr_cond = cond_hash
        self.trial_start = self.timer.elapsed_time()
        self.thread_lock.acquire()
        # return condition key
        return dict(cond_hash=cond_hash)

    def log_trial(self, last_flip_count=0):
        self.thread_lock.release()
        timestamp = self.timer.elapsed_time()
        trial_key = dict(self.session_key,
                         trial_idx=self.last_trial+1,
                         cond_hash=self.curr_cond,
                         start_time=self.trial_start,
                         end_time=timestamp,
                         last_flip_count=last_flip_count)
        self.queue.put(dict(table='Trial', tuple=trial_key))
        self.last_trial += 1

        # insert ping
        self.queue.put(dict(table='SetupControl', tuple=dict(setup=self.setup),
                            field='last_trial', value=self.last_trial, update=True))

    def log_liquid(self, probe, reward_amount):
        timestamp = self.timer.elapsed_time()
        self.queue.put(dict(table='LiquidDelivery', tuple=dict(self.session_key, time=timestamp, probe=probe,
                                                               reward_amount=reward_amount)))

    def log_stim(self):
        timestamp = self.timer.elapsed_time()
        self.queue.put(dict(table='StimOnset', tuple=dict(self.session_key, time=timestamp)))

    def log_lick(self, probe):
        timestamp = self.timer.elapsed_time()
        self.queue.put(dict(table='Lick', tuple=dict(self.session_key,
                                                     time=timestamp,
                                                     probe=probe)))

    def log_pulse_weight(self, pulse_dur, probe, pulse_num, weight=0):
        cal_key = dict(setup=self.setup, probe=probe, date=systime.strftime("%Y-%m-%d"))
        LiquidCalibration().insert1(cal_key, skip_duplicates=True)
        (LiquidCalibration.PulseWeight() & dict(cal_key, pulse_dur=pulse_dur)).delete_quick()
        LiquidCalibration.PulseWeight().insert1(dict(cal_key,
                                                     pulse_dur=pulse_dur,
                                                     pulse_num=pulse_num,
                                                     weight=weight))

    def log_animal_weight(self, weight):
        key = dict(animal_id=self.get_setup_info('animal_id'), weight=weight)
        Mice.MouseWeight().insert1(key)

    def log_position(self, in_position, state):
        timestamp = self.timer.elapsed_time()
        self.queue.put(dict(table='CenterPort', tuple=dict(self.session_key,
                                                            time=timestamp,
                                                            in_position=in_position,
                                                            state=state)))

    def update_setup_status(self, status):
        key = (SetupControl() & dict(setup=self.setup)).fetch1()
        in_status = key['status'] == status
        if not in_status:
            (SetupControl() & dict(setup=self.setup))._update('status', status)
        return in_status

    def update_setup_notes(self, note):
        self.queue.put(dict(table='SetupControl', tuple=dict(setup=self.setup),
                            field='notes', value=note, update=True))

    def update_state(self, state):
        self.queue.put(dict(table='SetupControl', tuple=dict(setup=self.setup),
                            field='state', value=state, update=True))

    def update_animal_id(self, animal_id):
        (SetupControl() & dict(setup=self.setup))._update('animal_id', animal_id)

    def update_task_idx(self, task_idx):
        (SetupControl() & dict(setup=self.setup))._update('task_idx', task_idx)

    def update_total_liquid(self, total_rew):
        self.queue.put(dict(table='SetupControl', tuple=dict(setup=self.setup),
                            field='total_liquid', value=total_rew, update=True))

    def update_difficulty(self, difficulty):
        self.queue.put(dict(table='SetupControl', tuple=dict(setup=self.setup),
                            field='difficulty', value=difficulty, update=True))

    def get_setup_info(self, field):
        info = (SetupControl() & dict(setup=self.setup)).fetch1(field)
        return info

    def get_session_key(self):
        return self.session_key

    def get_clip_info(self, curr_cond):
        clip_info = (MovieTables.Movie() * MovieTables.Movie.Clip() & curr_cond & self.session_key).fetch1()
        return clip_info

    def get_protocol(self):
        task_idx = (SetupControl() & dict(setup=self.setup)).fetch1('task_idx')
        protocol = (Task() & dict(task_idx=task_idx)).fetch1('protocol')
        path, filename = os.path.split(protocol)
        if not path:
            path = os.path.abspath('conf')
            protocol = path + '/' + filename
        return protocol

    def ping(self):
        lp = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.queue.put(dict(table='SetupControl', tuple=dict(setup=self.setup),
                            field='last_ping', value=lp, update=True))


