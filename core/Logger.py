import numpy, socket, json, os, pathlib, threading, subprocess, time
from queue import PriorityQueue
from datetime import datetime
from dataclasses import dataclass
from dataclasses import field as datafield
from typing import Any
import datajoint as dj
from utils.helper_functions import *
from utils.Timer import Timer
dj.config["enable_python_native_blobs"] = True

schemata = {'experiment': 'lab_experiments',
            'stimulus'  : 'lab_stimuli',
            'behavior'  : 'lab_behavior',
            'mice'      : 'lab_mice'}

for schema, value in schemata.items():
    globals()[schema] = dj.create_virtual_module(schema, value, create_tables=True, create_schema=True)


class Logger:
    trial_key, setup_info, _schemata = dict(animal_id=0, session=1, trial_idx=0), dict(), dict()
    lock, queue, ping_timer, logger_timer, total_reward, curr_state = False, PriorityQueue(), Timer(), Timer(), 0, ''

    def __init__(self, protocol=False):
        self.setup = socket.gethostname()
        self.is_pi = os.uname()[4][:3] == 'arm' if os.name == 'posix' else False
        self.setup_status = 'running' if protocol else 'ready'
        fileobject = open(os.path.dirname(os.path.abspath(__file__)) + '/../dj_local_conf.json')
        con_info = json.loads(fileobject.read())
        conn = dj.Connection(con_info['database.host'], con_info['database.user'], con_info['database.password'])
        for schema, value in schemata.items():  # separate connection for internal comminication
            self._schemata.update({schema: dj.create_virtual_module(schema, value, connection=conn)})
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
            skip = False if item.replace else True
            table = rgetattr(self._schemata[item.schema], item.table)
            self.thread_lock.acquire()
            try:
                table.insert1(item.tuple, ignore_extra_fields=item.ignore_extra_fields,
                              skip_duplicates=skip, replace=item.replace)
            except Exception as e:
                print('Failed to insert:\n', item.tuple, '\n in ', table, '\n With error:\n', e)
                if not item.error:
                    print('Will retry later')
                    item.error = True
                    item.priority = item.priority + 2
                    self.queue.put(item)
                else:
                    print('Errored again, stopping')
                    self.thread_end.set()
                    raise

            self.thread_lock.release()
            if item.block: self.queue.task_done()

    def getter(self):
        while not self.thread_end.is_set():
            self.thread_lock.acquire()
            self.setup_info = (self._schemata['experiment'].Control() & dict(setup=self.setup)).fetch1()
            self.thread_lock.release()
            self.setup_status = self.setup_info['status']
            time.sleep(1)  # update once a second

    def log(self, table, data=dict(), **kwargs):
        tmst = self.logger_timer.elapsed_time()
        self.put(table=table, tuple={**self.trial_key, 'time': tmst, **data}, **kwargs)
        return tmst

    def log_setup(self, task_idx=False):
        rel = experiment.Control() & dict(setup=self.setup)
        key = rel.fetch1() if numpy.size(rel.fetch()) else dict(setup=self.setup)
        if task_idx: key['task_idx'] = task_idx
        key = {**key, 'ip': self.get_ip(), 'status': self.setup_status}
        self.put(table='Control', tuple=key, replace=True, priority=1, block=True)

    def get_last_session(self):
        last_sessions = (experiment.Session() & dict(animal_id=self.get_setup_info('animal_id'))).fetch('session')
        return 0 if numpy.size(last_sessions) == 0 else numpy.max(last_sessions)

    def log_session(self, params, log_protocol=False):
        self.total_reward = 0
        self.trial_key = dict(animal_id=self.get_setup_info('animal_id'),
                              trial_idx=0, session=self.get_last_session() + 1)
        session_key = {**self.trial_key, **params, 'setup': self.setup,
                       'user_name': params['user'] if 'user_name' in params else 'bot'}
        self.put(table='Session', tuple=session_key, priority=1, block=True)
        if log_protocol:
            pr_name, pr_file = self.get_protocol(raw_file=True)
            git_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()
            self.put(table='Session.Protocol', tuple={**self.trial_key, 'protocol_name': pr_name,
                                                      'protocol_file': pr_file, 'git_hash': git_hash})
        self.put(table='Configuration', tuple=self.trial_key, schema='behavior', priority=2, block=True)
        self.put(table='Configuration', tuple=self.trial_key, schema='stimulus', priority=2, block=True)
        ports = (experiment.SetupConfiguration.Port & {'setup_conf_idx': params['setup_conf_idx']}
                 ).fetch(as_dict=True)
        for port in ports: self.put(table='Configuration.Port', tuple={**port, **self.trial_key}, schema='behavior')
        screens = (experiment.SetupConfiguration.Screen & {'setup_conf_idx': params['setup_conf_idx']}
                   ).fetch(as_dict=True)
        for scr in screens: self.put(table='Configuration.Screen', tuple={**scr, **self.trial_key}, schema='stimulus')
        balls = (experiment.SetupConfiguration.Ball & {'setup_conf_idx': params['setup_conf_idx']}
                 ).fetch(as_dict=True)
        for ball in balls: self.put(table='Configuration.Ball', tuple={**ball, **self.trial_key}, schema='behavior')

        key = {'session': self.trial_key['session'], 'trials': 0, 'total_liquid': 0, 'difficulty': 1}
        if 'start_time' in params:
            tdelta = lambda t: datetime.strptime(t, "%H:%M:%S") - datetime.strptime("00:00:00", "%H:%M:%S")
            key = {**key, 'start_time': tdelta(params['start_time']), 'stop_time': tdelta(params['stop_time'])}
        self.update_setup_info(key)
        self.logger_timer.start()  # start session time

    def update_setup_info(self, info):
        self.setup_info = {**(experiment.Control() & dict(setup=self.setup)).fetch1(), **info}
        self.put(table='Control', tuple=self.setup_info, replace=True, priority=1)
        self.setup_status = self.setup_info['status']
        if 'status' in info:
            while self.get_setup_info('status') != info['status']: time.sleep(.5)

    def get_setup_info(self, field):
        return (experiment.Control() & dict(setup=self.setup)).fetch1(field)

    def get(self, schema='experiment', table='Control', fields='', key='', **kwargs):
        table = rgetattr(eval(schema), table)
        return (table() & key).fetch(*fields, **kwargs)

    def get_protocol(self, task_idx=None, raw_file=False):
        if not task_idx: task_idx = self.get_setup_info('task_idx')
        if len(experiment.Task() & dict(task_idx=task_idx)) > 0:
            protocol = (experiment.Task() & dict(task_idx=task_idx)).fetch1('protocol')
            path, filename = os.path.split(protocol)
            if not path: protocol = str(pathlib.Path(__file__).parent.absolute()) + '/../conf/' + filename
            if raw_file:
                file = np.fromfile(protocol, dtype=np.int8)
                return protocol, file
            else:
                return protocol
        else:
            return False

    def update_trial_idx(self, trial_idx): self.trial_key['trial_idx'] = trial_idx

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


@dataclass(order=True)
class PrioritizedItem:
    table: str = datafield(compare =False)
    tuple: Any = datafield(compare=False)
    field: str = datafield(compare=False, default='')
    value: Any = datafield(compare=False, default='')
    schema: str = datafield(compare=False, default='experiment')
    replace: bool = datafield(compare=False, default=False)
    block: bool = datafield(compare=False, default=False)
    priority: int = datafield(default=50)
    error: bool = datafield(compare=False, default=False)
    ignore_extra_fields: bool = datafield(compare=False, default=True)

