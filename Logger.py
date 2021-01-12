import numpy, socket, json, os, pathlib, threading, functools
from utils.Timer import *
from utils.Generator import *
from queue import PriorityQueue
import time as systime
from datetime import datetime
from dataclasses import dataclass
from dataclasses import field as datafield
from typing import Any
from DatabaseTables import *
dj.config["enable_python_native_blobs"] = True


class Logger:
    setup, is_pi = socket.gethostname(), os.uname()[4][:3] == 'arm'

    def __init__(self, protocol=False):
        self.curr_state, self.lock, self.queue, self.curr_trial, self.total_reward = '', False, PriorityQueue(), 0, 0
        self.ping_timer, self.session_timer = Timer(), Timer()
        self.setup_status = 'running' if protocol else 'ready'
        self.log_setup(protocol)
        fileobject = open(os.path.dirname(os.path.abspath(__file__)) + '/dj_local_conf.json')
        connect_info = json.loads(fileobject.read())
        background_conn = dj.Connection(connect_info['database.host'], connect_info['database.user'],
                                        connect_info['database.password'])
        self.schemata = dict()
        self.schemata['lab'] = dj.create_virtual_module('beh.py', 'lab_behavior', connection=background_conn)
        self.schemata['mice'] = dj.create_virtual_module('mice.py', 'lab_mice', connection=background_conn)
        self.thread_end, self.thread_lock = threading.Event(),  threading.Lock()
        self.inserter_thread = threading.Thread(target=self.inserter)
        self.getter_thread = threading.Thread(target=self.getter)
        self.inserter_thread.start()
        self.getter_thread.start()

    def put(self, **kwargs): self.queue.put(PrioritizedItem(**kwargs))

    def inserter(self):
        while not self.thread_end.is_set():
            if self.queue.empty():  time.sleep(.5); continue
            item = self.queue.get()
            ignore, skip = (False, False) if item.replace else (True, True)
            table = self.rgetattr(self.schemata[item.schema], item.table)
            self.thread_lock.acquire()
            table.insert1(item.tuple, ignore_extra_fields=ignore, skip_duplicates=skip, replace=item.replace)
            self.thread_lock.release()

    def getter(self):
        while not self.thread_end.is_set():
            self.thread_lock.acquire()
            self.setup_info = (self.schemata['lab'].SetupControl() & dict(setup=self.setup)).fetch1()
            self.thread_lock.release()
            self.setup_status = self.setup_info['status']
            time.sleep(1)  # update once a second

    def log(self, table, data=dict()):
        tmst = self.session_timer.elapsed_time()
        self.put(table=table, tuple={**self.session_key, 'trial_idx': self.curr_trial, 'time': tmst, **data})
        return tmst

    def log_setup(self, task_idx=False):
        rel = SetupControl() & dict(setup=self.setup)
        key = rel.fetch1() if numpy.size(rel.fetch()) else dict(setup=self.setup)
        if task_idx: key['task_idx'] = task_idx
        key = {**key, 'ip': self.get_ip(), 'status': self.setup_status}
        SetupControl.insert1(key, replace=True)

    def log_session(self, params, exp_type=''):
        self.curr_trial, self.total_reward, self.session_key = 0, 0, {'animal_id': self.get_setup_info('animal_id')}
        last_sessions = (Session() & self.session_key).fetch('session')
        self.session_key['session'] = 1 if numpy.size(last_sessions) == 0 else numpy.max(last_sessions) + 1
        self.put(table='Session', tuple={**self.session_key, 'session_params': params, 'setup': self.setup,
                                         'protocol': self.get_protocol(), 'experiment_type': exp_type}, priority=1)
        key = {'session': self.session_key['session'], 'trials': 0, 'total_liquid': 0, 'difficulty': 1}
        if 'start_time' in params:
            tdelta = lambda t: datetime.strptime(t, "%H:%M:%S") - datetime.strptime("00:00:00", "%H:%M:%S")
            key = {**key, 'start_time': tdelta(params['start_time']), 'stop_time': tdelta(params['stop_time'])}
        self.update_setup_info(key)
        self.session_timer.start()  # start session time

    def log_conditions(self, conditions, condition_tables=[]):
        for cond in conditions:
            cond_hash = make_hash(cond)
            self.put(table='Condition', tuple=dict(cond_hash=cond_hash, cond_tuple=cond.copy()), priority=5)
            cond.update({'cond_hash': cond_hash})
            for condtable in condition_tables:
                if condtable == 'RewardCond' and isinstance(cond['probe'], tuple):
                    for idx, probe in enumerate(cond['probe']):
                        self.put(table=condtable, tuple={'cond_hash': cond['cond_hash'],
                                                         'probe': probe, 'reward_amount': cond['reward_amount']})
                else:
                    self.put(table=condtable, tuple=dict(cond.items()))
                    if condtable == 'OdorCond':
                        for idx, port in enumerate(cond['delivery_port']):
                            self.put(table=condtable+'.Port',
                                     tuple={'cond_hash': cond['cond_hash'], 'dutycycle': cond['dutycycle'][idx],
                                            'odor_id': cond['odor_id'][idx], 'delivery_port': port})
        return conditions

    def init_trial(self, cond_hash):
        self.curr_trial += 1
        if self.lock: self.thread_lock.acquire()
        self.curr_cond, self.trial_start = cond_hash, self.session_timer.elapsed_time()
        return self.trial_start    # return trial start time

    def log_trial(self, last_flip_count=0):
        if self.lock: self.thread_lock.release()
        timestamp = self.session_timer.elapsed_time()
        self.put(table='Trial', tuple=dict(self.session_key, trial_idx=self.curr_trial, cond_hash=self.curr_cond,
                                    start_time=self.trial_start, end_time=timestamp, last_flip_count=last_flip_count))

    def log_pulse_weight(self, pulse_dur, probe, pulse_num, weight=0):
        key = dict(setup=self.setup, probe=probe, date=systime.strftime("%Y-%m-%d"))
        self.put(table='LiquidCalibration', tuple=key, priority=5)
        self.put(table='LiquidCalibration.PulseWeight',
                 tuple=dict(key, pulse_dur=pulse_dur, pulse_num=pulse_num, weight=weight))

    def update_setup_info(self, info):
        self.setup_info = {**(SetupControl() & dict(setup=self.setup)).fetch1(), **info}
        self.put(table='SetupControl', tuple=self.setup_info, replace=True, priority=1)
        self.setup_status = self.setup_info['status']
        if 'status' in info:
            while self.get_setup_info('status') != self.setup_status: time.sleep(.5)

    def get_setup_info(self, field): return (SetupControl() & dict(setup=self.setup)).fetch1(field)

    def get_protocol(self, task_idx=None):
        if not task_idx: task_idx = self.get_setup_info('task_idx')
        protocol = (Task() & dict(task_idx=task_idx)).fetch1('protocol')
        path, filename = os.path.split(protocol)
        if not path: protocol = str(pathlib.Path(__file__).parent.absolute()) + '/conf/' + filename
        return protocol

    def ping(self, period=5000):
        if self.ping_timer.elapsed_time() >= period:  # occasionally update control table
            self.ping_timer.start()
            self.update_setup_info({'last_ping': str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                    'queue_size': self.queue.qsize(), 'trials': self.curr_trial,
                                    'total_liquid': self.total_reward, 'state': self.curr_state})

    def cleanup(self):
        while not self.queue.empty(): print('Waiting for empty queue... qsize: %d' % self.queue.qsize()); time.sleep(2)
        self.thread_end.set()

    @staticmethod
    def get_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: s.connect(("8.8.8.8", 80)); IP = s.getsockname()[0]
        except Exception: IP = '127.0.0.1'
        finally: s.close()
        return IP

    @staticmethod
    def rgetattr(obj, attr, *args):
        def _getattr(obj, attr): return getattr(obj, attr, *args)
        return functools.reduce(_getattr, [obj] + attr.split('.'))


@dataclass(order=True)
class PrioritizedItem:
    table: str = datafield(compare=False)
    tuple: Any = datafield(compare=False)
    field: str = datafield(compare=False, default='')
    value: Any = datafield(compare=False, default='')
    schema: str = datafield(compare=False, default='lab')
    replace: bool = datafield(compare=False, default=False)
    priority: int = datafield(default=50)
