import numpy, socket, json, os, pathlib, threading, functools
from utils.Timer import *
from utils.generator import *
from queue import PriorityQueue
import time as systime
from datetime import datetime
from dataclasses import dataclass
from dataclasses import field as datafield
from typing import Any
import datajoint as dj
from Experiment import *
dj.config["enable_python_native_blobs"] = True


class Logger:
    setup, is_pi = socket.gethostname(), os.uname()[4][:3] == 'arm'
    trial_key, schemata = dict(), dict()
    lock, queue, ping_timer, logger_timer = False, PriorityQueue(), Timer(), Timer()

    def __init__(self, protocol=False):
        self.setup_status = 'running' if protocol else 'ready'
        fileobject = open(os.path.dirname(os.path.abspath(__file__)) + '/dj_local_conf.json')
        con_info = json.loads(fileobject.read())
        conn = dj.Connection(con_info['database.host'], con_info['database.user'], con_info['database.password'])
        self.schemata['exp'] = dj.create_virtual_module('exp', 'test_experiments', connection=conn)
        self.schemata['mice'] = dj.create_virtual_module('mice', 'lab_mice', connection=conn)
        self.schemata['stim'] = dj.create_virtual_module('stim', 'lab_stimuli', connection=conn)
        self.schemata['beh'] = dj.create_virtual_module('beh', 'test_behavior', connection=conn)
        self.thread_end, self.thread_lock = threading.Event(),  threading.Lock()
        self.inserter_thread = threading.Thread(target=self.inserter)
        self.getter_thread = threading.Thread(target=self.getter)
        self.inserter_thread.start()
        self.log_setup(protocol)
        self.getter_thread.start()
        self.logger_timer.start()

    def put(self, **kwargs):
        item = PrioritizedItem(**kwargs)
        self.queue.put(item)
        if not item.block: self.queue.task_done()
        else: self.queue.join()

    def inserter(self):
        while not self.thread_end.is_set():
            if self.queue.empty():  time.sleep(.5); continue
            item = self.queue.get()
            print(item)
            ignore, skip = (False, False) if item.replace else (True, True)
            table = self.rgetattr(self.schemata[item.schema], item.table)
            self.thread_lock.acquire()
            table.insert1(item.tuple, ignore_extra_fields=ignore, skip_duplicates=skip, replace=item.replace)
            self.thread_lock.release()
            if item.block: self.queue.task_done()

    def getter(self):
        while not self.thread_end.is_set():
            self.thread_lock.acquire()
            self.setup_info = (SetupControl() & dict(setup=self.setup)).fetch1()
            self.thread_lock.release()
            self.setup_status = self.setup_info['status']
            time.sleep(1)  # update once a second

    def log(self, table, data=dict()):
        tmst = self.session_timer.elapsed_time()
        self.put(table=table, tuple={**self.trial_key, 'time': tmst, **data})
        return tmst

    def log_setup(self, task_idx=False):
        rel = SetupControl() & dict(setup=self.setup)
        key = rel.fetch1() if numpy.size(rel.fetch()) else dict(setup=self.setup)
        if task_idx: key['task_idx'] = task_idx
        key = {**key, 'ip': self.get_ip(), 'status': self.setup_status}
        self.put(table='SetupControl', tuple=key, replace=True, priority=1, block=True)

    def log_session(self, params, exp_type=''):
        self.total_reward = 0
        self.trial_key = dict(animal_id=self.get_setup_info('animal_id'), trial_idx=0)
        last_sessions = (Session() & self.trial_key).fetch('session')
        self.trial_key['session'] = 1 if numpy.size(last_sessions) == 0 else numpy.max(last_sessions) + 1
        self.put(table='Session', tuple={**self.trial_key, 'session_params': params, 'setup': self.setup,
                                         'protocol': self.get_protocol(), 'experiment_type': exp_type}, priority=1)
        key = {'session': self.trial_key['session'], 'trials': 0, 'total_liquid': 0, 'difficulty': 1}

        if 'start_time' in params:
            tdelta = lambda t: datetime.strptime(t, "%H:%M:%S") - datetime.strptime("00:00:00", "%H:%M:%S")
            key = {**key, 'start_time': tdelta(params['start_time']), 'stop_time': tdelta(params['stop_time'])}
        self.update_setup_info(key)
        self.logger_timer.start()  # start session time

    def log_conditions(self, conditions):
        for cond in conditions:
            cond_hash = make_hash(cond)
            self.put(table='Condition', tuple=dict(cond_hash=cond_hash, cond_tuple=cond.copy()), priority=5)
            cond.update({'cond_hash': cond_hash})
        return conditions

    def log_conditions2(self, conditions, condition_tables, schema):
        fields, hash_dict = list(), dict()
        for ctable in condition_tables:
            table = self.rgetattr(self.schemata[schema], ctable)
            fields += list(table().heading.names)
        for condition in conditions:
            key = {sel_key: condition[sel_key] for sel_key in fields if sel_key != 'cond_hash'}
            condition.update({'cond_hash': make_hash(key)})
            hash_dict[condition['cond_hash']] = condition['cond_hash']
            self.put(table=condition_tables[0], tuple=condition.copy(), schema=schema)
            for ctable in condition_tables[1:]:  # insert dependant condition tables
                primary_field = [field for field in self.rgetattr(self.schemata[schema], ctable).primary_key
                                 if field != 'cond_hash']
                if primary_field:
                    for idx, pcond in enumerate(condition[primary_field[0]]):
                        key = {k: v if type(v) in [int, float, str] else v[idx] for k, v in condition.items()}
                        self.put(table=ctable, tuple=key, schema=schema)
                else: self.put(table=ctable, tuple=key, schema=schema)
        return conditions, condition['cond_hash']

    def log_pulse_weight(self, pulse_dur, probe, pulse_num, weight=0):
        key = dict(setup=self.setup, probe=probe, date=systime.strftime("%Y-%m-%d"))
        self.put(table='LiquidCalibration', tuple=key, priority=5)
        self.put(table='LiquidCalibration.PulseWeight',
                 tuple=dict(key, pulse_dur=pulse_dur, pulse_num=pulse_num, weight=weight), replace=True)

    def update_setup_info(self, info):
        self.setup_info = {**(SetupControl() & dict(setup=self.setup)).fetch1(), **info}
        self.put(table='SetupControl', tuple=self.setup_info, replace=True, priority=1)
        self.setup_status = self.setup_info['status']
        if 'status' in info:
            while self.get_setup_info('status') != info['status']: time.sleep(.5)

    def get_setup_info(self, field): return (SetupControl() & dict(setup=self.setup)).fetch1(field)

    def get_protocol(self, task_idx=None):
        if not task_idx: task_idx = self.get_setup_info('task_idx')
        if len(Task() & dict(task_idx=task_idx)) > 0:
            protocol = (Task() & dict(task_idx=task_idx)).fetch1('protocol')
            path, filename = os.path.split(protocol)
            if not path: protocol = str(pathlib.Path(__file__).parent.absolute()) + '/conf/' + filename
            return protocol
        else:
            return False

    def ping(self, period=5000):
        if self.ping_timer.elapsed_time() >= period:  # occasionally update control table
            self.ping_timer.start()
            self.update_setup_info({'last_ping': str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                    'queue_size': self.queue.qsize(), 'trials': self.trial_key['trial_idx'],
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
    schema: str = datafield(compare=False, default='exp')
    replace: bool = datafield(compare=False, default=False)
    block: bool = datafield(compare=False, default=False)
    priority: int = datafield(default=50)
