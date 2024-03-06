import numpy, socket, json, os, pathlib, threading, subprocess, time, platform
from queue import PriorityQueue
from datetime import datetime
from dataclasses import dataclass
from dataclasses import field as datafield
from typing import Any
import datajoint as dj
from utils.helper_functions import *
from utils.Timer import Timer
from utils.Writer import Writer
from typing import Optional, Tuple, Dict

dj.config["enable_python_native_blobs"] = True

schemata = {'experiment': 'lab_experiments',
            'stimulus'  : 'lab_stimuli',
            'behavior'  : 'lab_behavior',
            'recording' : 'lab_recordings',
            'mice'      : 'lab_mice'}

for schema, value in schemata.items():  # separate connection for internal comminication
    globals()[schema] = dj.create_virtual_module(schema, value, create_tables=True, create_schema=True)


class Logger:
    trial_key, setup_info, _schemata, datasets = dict(animal_id=0, session=1, trial_idx=0), dict(), dict(), dict()
    lock, queue, ping_timer, logger_timer, total_reward, curr_state = False, PriorityQueue(), Timer(), Timer(), 0, ''

    def __init__(self, protocol=False):
        self.setup = socket.gethostname()
        system = platform.uname()
        if isinstance(protocol, str):
            if not os.path.isfile(protocol): protocol = int(protocol)
        self.protocol = protocol
        self.is_pi = system.machine.startswith("arm") or system.machine=='aarch64' if system.system == 'Linux' else False
        self.manual_run = True if protocol else False
        self.setup_status = 'running' if self.manual_run else 'ready'
        con_info = dj.conn.connection.conn_info
        self.private_conn = dj.Connection(con_info['host'], con_info['user'], con_info['passwd'])
        for schema, value in schemata.items():  # separate connection for internal comminication
            self._schemata.update({schema: dj.create_virtual_module(schema, value, connection=self.private_conn)})
        self.thread_end, self.thread_lock = threading.Event(),  threading.Lock()
        self.inserter_thread = threading.Thread(target=self.inserter)
        self.getter_thread = threading.Thread(target=self.getter)
        self.inserter_thread.start()
        self.log_setup(protocol)
        self.getter_thread.start()
        self.logger_timer.start()
        self.Writer = Writer

    def setup_schema(self, extra_schema):
        for schema, value in extra_schema.items():
            globals()[schema] = dj.create_virtual_module(schema, value, create_tables=True, create_schema=True)
            self._schemata.update({schema: dj.create_virtual_module(schema, value, connection=self.private_conn)})

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
                if item.validate:  # validate tuple exists in database
                    key = {k: v for (k, v) in item.tuple.items() if k in table.primary_key}
                    if 'status' in item.tuple.keys(): key['status'] = item.tuple['status']
                    while not len(table & key) > 0: time.sleep(.5)
            except Exception as e:
                if item.error: self.thread_end.set(); raise
                print('Failed to insert:\n', item.tuple, '\n in ', table, '\n With error:\n', e, '\nWill retry later')
                item.error = True
                item.priority = item.priority + 2
                self.queue.put(item)
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
        if self.manual_run and table == 'Trial.StateOnset': print('State: ', data['state'])
        return tmst

    def log_setup(self, task=False):
        rel = experiment.Control() & dict(setup=self.setup)
        key = rel.fetch1() if numpy.size(rel.fetch()) else dict(setup=self.setup)
        if task and isinstance(task, int): key['task_idx'] = task
        key = {**key, 'ip': self.get_ip(), 'status': self.setup_status}
        self.put(table='Control', tuple=key, replace=True, priority=1, block=True, validate=True)
        
    def log_recording(self, key: Dict[str, any]):
        """
        Logs a recording.

        Args:
            key (dict): A dictionary containing information about the recording.

        Returns:
            None
        """
        recs = self.get(
            schema="recording",
            table="Recording",
            key=self.trial_key,
            fields=["rec_idx"],
        )
        rec_idx = 1 if not recs else max(recs) + 1
        self.log("Recording", data={**key, "rec_idx": rec_idx}, schema="recording", block=True)

    def get_last_session(self):
        last_sessions = (experiment.Session() & dict(animal_id=self.get_setup_info('animal_id'))).fetch('session')
        return 0 if numpy.size(last_sessions) == 0 else numpy.max(last_sessions)

    def log_session(self, params, log_protocol=False):
        self.total_reward = 0
        self.trial_key = dict(animal_id=self.get_setup_info('animal_id'),
                              trial_idx=0, session=self.get_last_session() + 1)
        session_key = {**self.trial_key, **params, 'setup': self.setup,
                       'user_name': params['user'] if 'user_name' in params else 'bot'}
        if self.manual_run: print('Logging Session: ', session_key)
        self.put(table='Session', tuple=session_key, priority=1, validate=True, block=True)
        if log_protocol:
            pr_name, pr_file = self.get_protocol(raw_file=True)
            git_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()
            self.put(table='Session.Protocol', tuple={**self.trial_key, 'protocol_name': pr_name,
                                                      'protocol_file': pr_file, 'git_hash': git_hash})
        self.put(table='Configuration', tuple=self.trial_key, schema='behavior', priority=2, validate=True, block=True)
        self.put(table='Configuration', tuple=self.trial_key, schema='stimulus', priority=2, validate=True, block=True)
        ports = (experiment.SetupConfiguration.Port & {'setup_conf_idx': params['setup_conf_idx']}
                 ).fetch(as_dict=True)
        for port in ports:
            self.put(table='Configuration.Port', tuple={**port, **self.trial_key}, schema='behavior')
        screens = (experiment.SetupConfiguration.Screen & {'setup_conf_idx': params['setup_conf_idx']}
                   ).fetch(as_dict=True)
        for scr in screens:
            self.put(table='Configuration.Screen', tuple={**scr, **self.trial_key}, schema='stimulus')
        balls = (experiment.SetupConfiguration.Ball & {'setup_conf_idx': params['setup_conf_idx']}
                 ).fetch(as_dict=True)
        for ball in balls:
            self.put(table='Configuration.Ball', tuple={**ball, **self.trial_key}, schema='behavior')
        speakers = (experiment.SetupConfiguration.Speaker & {'setup_conf_idx': params['setup_conf_idx']}
                 ).fetch(as_dict=True)
        for spk in speakers:
            self.put(table='Configuration.Speaker', tuple={**spk, **self.trial_key}, schema='stimulus')

        key = {'session': self.trial_key['session'], 'trials': 0, 'total_liquid': 0, 'difficulty': 1, 'state': ''}
        if 'start_time' in params:
            tdelta = lambda t: datetime.strptime(t, "%H:%M:%S") - datetime.strptime("00:00:00", "%H:%M:%S")
            key = {**key,'start_time': str(tdelta(params['start_time'])), 'stop_time': str(tdelta(params['stop_time']))}
        self.update_setup_info({**key, "status":self.setup_info['status']})
        self.logger_timer.start()  # start session time

    def update_setup_info(self, info, key=dict()):
        self.setup_info = {**(experiment.Control() & {**{'setup': self.setup}, **key}).fetch1(), **info}
        block = True if 'status' in info else False
        self.put(table='Control', tuple=self.setup_info, replace=True, priority=1, block=block, validate=block)
        self.setup_status = self.setup_info['status']

    def get_setup_info(self, field):
        return (experiment.Control() & dict(setup=self.setup)).fetch1(field)

    def get(self, schema='experiment', table='Control', fields='', key=dict(), **kwargs):
        table = rgetattr(eval(schema), table)
        return (table() & key).fetch(*fields, **kwargs)

    def get_protocol(self, task_idx=None, raw_file=False):
        if not task_idx and not isinstance(self.protocol, str):
            task_idx = self.get_setup_info('task_idx')
            if not len(experiment.Task() & dict(task_idx=task_idx)) > 0: return False
            protocol = (experiment.Task() & dict(task_idx=task_idx)).fetch1('protocol')
        else:
            protocol = self.protocol
        path, filename = os.path.split(protocol)
        if not path: protocol = str(pathlib.Path(__file__).parent.absolute()) + '/../conf/' + filename
        if raw_file:
            return protocol, np.fromfile(protocol, dtype=np.int8)
        else:
            return protocol

    def update_trial_idx(self, trial_idx): self.trial_key['trial_idx'] = trial_idx

    def ping(self, period=5000):
        if self.ping_timer.elapsed_time() >= period:  # occasionally update control table
            self.ping_timer.start()
            self.update_setup_info({'last_ping': str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                    'queue_size': self.queue.qsize(), 'trials': self.trial_key['trial_idx'],
                                    'total_liquid': self.total_reward, 'state': self.curr_state})

    def cleanup(self):
        while not self.queue.empty(): print('Waiting for empty queue... qsize: %d' % self.queue.qsize()); time.sleep(1)
        self.thread_end.set()

    def createDataset(
            self,
            path: str,
            target_path: str,
            dataset_name: str,
            dataset_type: type,
            filename: Optional[str] = None,
        ) -> Tuple[str, Any]:
            """
            Create a dataset and return the filename and dataset object.

            Args:
                path (str): The path where the dataset will be saved.
                target_path (str): The target path for the dataset.
                dataset_name (str): The name of the dataset.
                dataset_type (type): The datatype of the dataset.
                filename (str, optional): The filename for the dataset. If not provided, a default filename will be generated based on the dataset name, animal ID, session, and current timestamp.

            Returns:
                Tuple[str, Any]: A tuple containing the filename and the dataset object.

            """
            # Generate filename if not provided
            if filename is None:
                filename = "%s_%d_%d_%s.h5" % (
                    dataset_name,
                    self.trial_key["animal_id"],
                    self.trial_key["session"],
                    datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                )

            # Create dataset
            self.datasets[dataset_name] = self.Writer(path + filename, target_path)
            self.datasets[dataset_name].createDataset(
                dataset_name, shape=(1,), dtype=dataset_type
            )

            # Return filename and dataset object
            return filename, self.datasets[dataset_name]

    def closeDatasets(self):
        for dataset in self.datasets:
            self.datasets[dataset].exit()

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
    validate: bool = datafield(compare=False, default=False)
    priority: int = datafield(default=50)
    error: bool = datafield(compare=False, default=False)
    ignore_extra_fields: bool = datafield(compare=False, default=True)

