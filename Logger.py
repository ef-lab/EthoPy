import numpy, socket, json, os, pathlib, sys
from utils.Timer import *
from utils.Generator import *
from queue import Queue
import time as systime
from datetime import datetime, timedelta
import threading
from DatabaseTables import *
dj.config["enable_python_native_blobs"] = True


class Logger:
    """ This class handles the database logging"""

    def __init__(self, log_setup=False, protocol=False):
        self.curr_trial = 0
        self.queue = Queue()
        self.timer = Timer()
        self.trial_start = 0
        self.curr_cond = []
        self.task_idx = []
        self.session_key = dict()
        self.setup_status = 'ready'
        self.is_pi = os.uname()[4][:3] == 'arm'
        self.setup = socket.gethostname()
        self.lock = False
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        self.ip = s.getsockname()[0]
        if log_setup: self.log_setup(protocol)
        path = os.path.dirname(os.path.abspath(__file__))
        fileobject = open(path + '/dj_local_conf.json')
        connect_info = json.loads(fileobject.read())
        insert_conn = dj.Connection(connect_info['database.host'], connect_info['database.user'],
                              connect_info['database.password'])
        self.insert_schema = dj.create_virtual_module('beh.py', 'lab_behavior', connection=insert_conn)
        self.thread_end = threading.Event()
        self.thread_lock = threading.Lock()
        self.inserter_thread = threading.Thread(target=self.inserter)  # max insertion rate of 10 events/sec
        self.inserter_thread.start()
        self.getter_thread = threading.Thread(target=self.getter)  # max insertion rate of 10 events/sec
        self.getter_thread.start()

    def cleanup(self):
        while not self.queue.empty():
            print('Waiting for que to empty... # %d' % self.queue.qsize())
            time.sleep(2)
        self.thread_end.set()

    def inserter(self):
        while not self.thread_end.is_set():
            if self.queue.empty():  time.sleep(.5); continue
            self.thread_lock.acquire()
            item = self.queue.get()
            try:
                if 'update' in item:
                    eval('(self.insert_schema.' + item['table'] +
                         '() & item["tuple"])._update(item["field"],item["value"])')
                else:
                    eval('self.insert_schema.' + item['table'] +
                         '.insert1(item["tuple"], ignore_extra_fields=True, skip_duplicates=True)')
            except:
                self.thread_end.set()
                print("Database error with the following key:")
                print(item)
                time.sleep(2)
                self.setup_status = 'exit'
                sys.exit(0)
            self.thread_lock.release()

    def getter(self):
        while not self.thread_end.is_set():
            self.thread_lock.acquire()
            self.setup_status = (self.insert_schema.SetupControl() & dict(setup=self.setup)).fetch1('status')
            self.thread_lock.release()
            time.sleep(1)  # update once a second

    def log(self, table, data=dict()):
        tmst = self.timer.elapsed_time()
        self.queue.put(dict(table=table, tuple={**self.session_key, 'trial_idx': self.curr_trial, 'time': tmst, **data}))
        return tmst

    def log_setup(self, protocol=False):
        key = dict(setup=self.setup)
        # update values in case they exist
        if numpy.size((SetupControl() & dict(setup=self.setup)).fetch()):
            key = (SetupControl() & dict(setup=self.setup)).fetch1()
            (SetupControl() & dict(setup=self.setup)).delete_quick()
        if protocol:
            self.setup_status = 'running'
            key['task_idx'] = protocol
        SetupControl().insert1({**key, 'ip': self.ip, 'status': self.setup_status})

    def log_session(self, session_params, exp_type=''):
        animal_id, task_idx = (SetupControl() & dict(setup=self.setup)).fetch1('animal_id', 'task_idx')
        self.task_idx = task_idx
        self.curr_trial = 0

        # create session key
        self.session_key = {'animal_id': animal_id}
        last_sessions = (Session() & self.session_key).fetch('session')
        self.session_key['session'] = 1 if numpy.size(last_sessions) == 0 else numpy.max(last_sessions) + 1
        self.queue.put(dict(table='Session', tuple={**self.session_key,
                                                    'session_params': session_params,
                                                    'setup': self.setup,
                                                    'protocol': self.get_protocol(),
                                                    'experiment_type': exp_type}))
        # start session time
        self.timer.start()
        self.update_setup_info('current_session', self.session_key['session'])
        self.update_setup_info('last_trial', 0)
        self.update_setup_info('total_liquid', 0)
        if 'start_time' in session_params:
            self.update_setup_info('start_time', session_params['start_time'], nowait=True)
            self.update_setup_info('stop_time', session_params['stop_time'], nowait=True)

    def log_conditions(self, conditions, condition_tables=[]):
        # iterate through all conditions and insert
        for cond in conditions:
            cond_hash = make_hash(cond)
            self.queue.put(dict(table='Condition', tuple=dict(cond_hash=cond_hash, cond_tuple=cond.copy())))
            cond.update({'cond_hash': cond_hash})
            for condtable in condition_tables:
                if condtable == 'RewardCond' and isinstance(cond['probe'], tuple):
                    for idx, probe in enumerate(cond['probe']):
                        self.queue.put(dict(table=condtable, tuple={'cond_hash': cond['cond_hash'],
                                                                    'probe': probe,
                                                                    'reward_amount': cond['reward_amount']}))
                else:
                    self.queue.put(dict(table=condtable, tuple=dict(cond.items())))
                    if condtable == 'OdorCond':
                        for idx, port in enumerate(cond['delivery_port']):
                            self.queue.put(dict(table=condtable+'.Port',
                                                tuple={'cond_hash': cond['cond_hash'],
                                                       'dutycycle': cond['dutycycle'][idx],
                                                       'odor_id': cond['odor_id'][idx],
                                                       'delivery_port': port}))
        return conditions

    def init_trial(self, cond_hash):
        self.curr_cond = cond_hash
        if self.lock: self.thread_lock.acquire()
        self.curr_trial += 1
        self.trial_start = self.timer.elapsed_time()
        return self.trial_start    # return trial start time

    def log_trial(self, last_flip_count=0):
        if self.lock: self.thread_lock.release()
        timestamp = self.timer.elapsed_time()
        trial_key = dict(self.session_key, trial_idx=self.curr_trial, cond_hash=self.curr_cond,
                         start_time=self.trial_start, end_time=timestamp, last_flip_count=last_flip_count)
        self.queue.put(dict(table='Trial', tuple=trial_key))

        # insert ping
        self.queue.put(dict(table='SetupControl', tuple=dict(setup=self.setup),
                            field='last_trial', value=self.curr_trial, update=True))

    def log_abort(self):
        self.queue.put(dict(table='AbortedTrial', tuple=dict(self.session_key, trial_idx=self.curr_trial)))

    def log_liquid(self, probe, reward_amount):
        timestamp = self.timer.elapsed_time()
        self.queue.put(dict(table='LiquidDelivery', tuple=dict(self.session_key, time=timestamp, probe=probe,
                                                               reward_amount=reward_amount)))

    def log_stim(self, period='Trial'):
        timestamp = self.timer.elapsed_time()
        self.queue.put(dict(table='StimOnset', tuple=dict(self.session_key, time=timestamp, period=period)))

    def log_lick(self, probe):
        timestamp = self.timer.elapsed_time()
        self.queue.put(dict(table='Lick', tuple=dict(self.session_key, time=timestamp, probe=probe)))
        return timestamp

    def log_touch(self, loc):
        timestamp = self.timer.elapsed_time()
        self.queue.put(dict(table='Touch', tuple=dict(self.session_key, time=timestamp, loc_x=loc[0], loc_y=loc[1])))
        return timestamp

    def log_pulse_weight(self, pulse_dur, probe, pulse_num, weight=0):
        cal_key = dict(setup=self.setup, probe=probe, date=systime.strftime("%Y-%m-%d"))
        LiquidCalibration().insert1(cal_key, skip_duplicates=True)
        (LiquidCalibration.PulseWeight() & dict(cal_key, pulse_dur=pulse_dur)).delete_quick()
        LiquidCalibration.PulseWeight().insert1(dict(cal_key, pulse_dur=pulse_dur,
                                                     pulse_num=pulse_num, weight=weight))

    def log_animal_weight(self, weight):
        key = dict(animal_id=self.get_setup_info('animal_id'), weight=weight)
        Mice.MouseWeight().insert1(key)

    def log_position(self, in_position, state):
        timestamp = self.timer.elapsed_time()
        self.queue.put(dict(table='CenterPort', tuple=dict(self.session_key, time=timestamp,
                                                           in_position=in_position, state=state)))
        return timestamp

    def update_setup_info(self, field, value, nowait=False):
        if nowait:
            (SetupControl() & dict(setup=self.setup))._update(field, value)
        else:
            self.queue.put(dict(table='SetupControl', tuple=dict(setup=self.setup),
                                field=field, value=value, update=True))

    def get_setup_info(self, field):
        return (SetupControl() & dict(setup=self.setup)).fetch1(field)

    def get_clip_info(self, key):
        clip_info = (Stimuli.Movie() * Stimuli.Movie.Clip() & key & self.session_key).fetch1()
        return clip_info

    def get_object(self, obj_id):
        return (Stimuli.Objects() & ('obj_id=%d' % obj_id)).fetch1()

    def get_protocol(self, task_idx=None):
        if not task_idx:
            task_idx = (SetupControl() & dict(setup=self.setup)).fetch1('task_idx')
        protocol = (Task() & dict(task_idx=task_idx)).fetch1('protocol')
        path, filename = os.path.split(protocol)
        if not path:
            path = pathlib.Path(__file__).parent.absolute()
            protocol = str(path) + '/conf/' + filename
        return protocol

    def ping(self):
        lp = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.queue.put(dict(table='SetupControl', tuple=dict(setup=self.setup),
                            field='last_ping', value=lp, update=True))
        self.queue.put(dict(table='SetupControl', tuple=dict(setup=self.setup),
                            field='queue_size', value=self.queue.qsize(), update=True))


