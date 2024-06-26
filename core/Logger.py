import json
import os
import pathlib
import platform
import pprint
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from dataclasses import field as datafield
from datetime import datetime
from os import environ
from queue import PriorityQueue
from typing import Any, Dict, Optional

import datajoint as dj
import numpy as np

from utils.helper_functions import rgetattr
from utils.Timer import Timer
from utils.Writer import Writer

with open("local_conf.json", "r", encoding="utf-8") as f:
    config = json.load(f)
dj.config.update(config["dj_local_conf"])
dj.logger.setLevel(dj.config["datajoint.loglevel"])


environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# Schema mappings
SCHEMATA = config["SCHEMATA"]

# Create virtual modules
virtual_modules = {
    name: dj.create_virtual_module(name, schema, create_tables=True, create_schema=True)
    for name, schema in SCHEMATA.items()
}
experiment = virtual_modules["experiment"]
stimulus = virtual_modules["stimulus"]
behavior = virtual_modules["behavior"]
recording = virtual_modules["recording"]
mice = virtual_modules["mice"]

VERSION = "0.1"

class Logger:
    DEFAULT_SOURCE_PATH = os.path.expanduser("~") + "/EthoPy_Files/"
    DEFAULT_TARGET_PATH = False

    def __init__(self, protocol=False):
        self.setup = socket.gethostname()
        self.is_pi = self._check_if_raspberry_pi()

        self.task_idx, self.protocol_path = self._parse_protocol(protocol)

        # if the protocol path or task id is defined means that it runs manually
        self.manual_run = True if self.protocol_path else False

        self.setup_status = 'running' if self.manual_run else 'ready'

        # separate connection for internal communication
        self.private_conn = dj.Connection(
            dj.config["database.host"],
            dj.config["database.user"],
            dj.config["database.password"],
        )
        self._schemata = self._initialize_schemata()

        self.writer = Writer
        self.rec_fliptimes = True
        self.trial_key = {'animal_id': 0, 'session': 1, 'trial_idx': 0}
        self.setup_info = {}
        self.datasets = {}
        self.lock = False
        self.queue = PriorityQueue()
        self.ping_timer = Timer()
        self.logger_timer = Timer()
        self.total_reward = 0
        self.curr_state = ""

        # set up paths
        self.source_path = self._get_path("source_path", self.DEFAULT_SOURCE_PATH)
        self.target_path = self._get_path("target_path", self.DEFAULT_TARGET_PATH)

        self.thread_end, self.thread_lock = threading.Event(), threading.Lock()
        self.inserter_thread = threading.Thread(target=self._inserter)
        self.getter_thread = threading.Thread(target=self._update_setup_status_periodically)
        self.inserter_thread.start()
        self._log_setup(self.task_idx)
        self.getter_thread.start()
        self.logger_timer.start()

    def _parse_protocol(self, protocol):
        if protocol and protocol.isdigit():
            return int(protocol), self._find_protocol_path(int(protocol))
        elif protocol and isinstance(protocol, str):
            return None, protocol
        return None, None

    def update_protocol(self):
        """
        This method updates the protocol path.

        If the run is not manual, it fetches the task index from the setup info.
        It then checks if there is a task with this index in the experiment's Task table.
        If there is no such task, it returns False.
        Otherwise, it fetches the protocol associated with this task and updates the protocol path.

        Returns:
            bool: True if the protocol path was successfully updated, False otherwise.
        """
        # find the protocol_path based on the task_id from the control table
        if not self.manual_run:
            task_idx = self.get_setup_info('task_idx')
            if not len(experiment.Task() & dict(task_idx=task_idx)) > 0:
                return False
            protocol = (experiment.Task() & dict(task_idx=task_idx)).fetch1('protocol')
            self.protocol_path = protocol
        # checks if the file exist
        if not os.path.isfile(self.protocol_path):
            print(f"Protocol file {self.protocol_path} not found!")
            return False
        return True

    @property
    def protocol_path(self) -> str:
        """
        Get the protocol path.

        Returns:
            str: The protocol path.
        """
        return self._protocol_path

    @protocol_path.setter
    def protocol_path(self, protocol_path: str):
        """
        Set the protocol path. if protocol_path has only filename
        set the protocol_path at the conf directory.

        Args:
            protocol_path (str): The protocol path.
        """

        if protocol_path is not None:
            path, filename = os.path.split(protocol_path)
            if not path:
                protocol_path = (
                    str(pathlib.Path(__file__).parent.absolute()) + "/../conf/" + filename
                )
        self._protocol_path = protocol_path

    def _find_protocol_path(self, task_idx=None):
        """find the protocol path from the task index"""
        if task_idx:
            return (experiment.Task() & dict(task_idx=task_idx)).fetch1("protocol")
        else:
            return False

    def _initialize_schemata(self) -> Dict[str, dj.VirtualModule]:
        return {
            schema: dj.create_virtual_module(
                schema, value, connection=self.private_conn
            )
            for schema, value in SCHEMATA.items()
        }

    def _check_if_raspberry_pi(self) -> bool:
        system = platform.uname()
        return (
            system.machine.startswith("arm") or system.machine == "aarch64"
            if system.system == "Linux"
            else False
        )

    def _get_path(self, path_key: str, default_path: str = None) -> str:
        """
        Get the path from the configuration or create a new directory at the default path.

        Args:
        path_key (str): The key to look up in the configuration.
        default_path (str): The path to use if the key is not in the configuration.

        Returns:
        str: The path from the configuration or the default path.
        """
        path = config.get(path_key, default_path)
        if path:
            os.makedirs(path, exist_ok=True)
            print(f"Setting storage directory: {path}")
        return path

    def setup_schema(self, extra_schema: Dict[str, Any]) -> None:
        """
        Set up additional schema.

        Args:
        extra_schema (Dict[str, Any]): The additional schema to set up.
        """
        for schema, value in extra_schema.items():
            globals()[schema] = dj.create_virtual_module(
                schema, value, create_tables=True, create_schema=True
            )
            self._schemata.update(
                {
                    schema: dj.create_virtual_module(
                        schema, value, connection=self.private_conn
                    )
                }
            )

    def put(self, **kwargs: Any) -> None:
        """
        Put an item in the queue.

        Parameters:
        **kwargs (Any): The item to put in the queue.
        """
        item = PrioritizedItem(**kwargs)
        self.queue.put(item)
        if not item.block:
            self.queue.task_done()
        else:
            self.queue.join()

    def _insert_item(self, item, table):
        """
        Inserts an item into the specified table.

        Args:
            item: The item to be inserted.
            table: The table to insert the item into.

        Returns:
            None
        """
        table.insert1(
            item.tuple,
            ignore_extra_fields=item.ignore_extra_fields,
            skip_duplicates=False if item.replace else True,
            replace=item.replace,
        )

    def _validate_item(self, item, table):
        """
        Validates an item against a table.
        """
        if item.validate:  # validate tuple exists in database
            key = {k: v for (k, v) in item.tuple.items() if k in table.primary_key}
            if "status" in item.tuple.keys():
                key["status"] = item.tuple["status"]
            while not len(table & key) > 0:
                time.sleep(0.5)

    def _handle_error(self, item, table, e, thread_end, queue):
        """
        Handles an error by logging the error message and add the item again in the queue
        and re-trying again later.

        Parameters:
        item : Description of parameter `item`.
        table : Description of parameter `table`.
        e (Exception): The exception that was raised.
        thread_end : Description of parameter `thread_end`.
        queue : Description of parameter `queue`.
        """
        str_error = f"Failed to insert:\n{item.tuple}\n in {table}\n With error:\n{e}"
        if item.error:
            thread_end.set()
            raise str_error + "\nSecond time..."
        print(str_error+"\nWill retry later")
        item.error = True
        item.priority = item.priority + 2
        queue.put(item)

    def _inserter(self):
        """
        This method continuously inserts items from the queue into their respective tables in
        the database.

        It runs in a loop until the thread_end event is set. In each iteration, it checks if
        the queue is empty.If it is, it sleeps for 0.5 seconds and then continues to the next
        iteration.
        If the queue is not empty, it gets an item from the queue, acquires the thread lock,
        and tries to insert the item into it's table.
        If an error occurs during the insertion, it handles the error.
        After the insertion, it releases the thread lock.
        If the item was marked to block, it marks the task as done.

        Returns:
            None
        """
        while not self.thread_end.is_set():
            if self.queue.empty():
                time.sleep(0.5)
                continue
            item = self.queue.get()
            table = rgetattr(self._schemata[item.schema], item.table)
            self.thread_lock.acquire()
            try:
                self._insert_item(item, table)
                self._validate_item(item, table)
            except ValueError as e:
                if item.error:
                    self.thread_end.set()
                    raise Exception(
                        f"Second time failed to insert:\n {item.tuple} in {table} With error:\n {e}"
                    ) from e        
                self._handle_error(item, table, e, self.thread_end, self.queue)
            self.thread_lock.release()
            if item.block:
                self.queue.task_done()

    def _update_setup_status_periodically(self):
        """
        This method continuously updates the setup information and status from the experiment
        database.

        It runs in a loop until the thread_end event is set. In each iteration, it acquires the
        thread lock,fetches the setup information from the Control table in the experiment database,
        releases the thread lock, and updates the setup status. It then sleeps for 1 second before
        the next iteration.

        Returns:
            None
        """
        while not self.thread_end.is_set():
            self.thread_lock.acquire()
            self.setup_info = (
                self._schemata["experiment"].Control() & dict(setup=self.setup)
            ).fetch1()
            self.thread_lock.release()
            self.setup_status = self.setup_info["status"]
            time.sleep(1)  # update once a second

    def log(self, table, data=None, **kwargs):
        """
        This method logs the given data into the specified table in the experiment database.

        It first gets the elapsed time from the logger timer and adds it to the data dictionary.
        It then puts the data into the specified table. If the manual_run flag is set and the
        table is "Trial.StateOnset",
        it prints the state.

        Args:
            table (str): The name of the table in the experiment database.
            data (dict, optional): The data to be logged. Defaults to an empty dictionary.
            **kwargs: Additional keyword arguments to be passed to the put method.

        Returns:
            float: The elapsed time from the logger timer.
        """
        tmst = self.logger_timer.elapsed_time()
        data = data or {}
        self.put(table=table, tuple={**self.trial_key, "time": tmst, **data}, **kwargs)
        if self.manual_run and table == "Trial.StateOnset":
            print("State: ", data["state"])
        return tmst

    def _log_setup(self, task=None):
        """
        This method logs the setup information into the Control table in the experiment database.

        It first fetches the control information for the current setup. If no control information
        is found, it creates a new dictionary with the setup information. If a task is provided and
        it is an integer, it adds the task index to the key. It then adds the IP and status
        information to the key.

        The method finally puts the key into the Control table, replacing any existing entry with
        the same key. It blocks until the operation is complete and validates the operation.

        Args:
            task (int, optional): The task index. Defaults to None.

        Returns:
            None
        """
        rel = experiment.Control() & dict(setup=self.setup)
        key = rel.fetch1() if np.size(rel.fetch()) else dict(setup=self.setup)
        if task and isinstance(task, int):
            key["task_idx"] = task
        key = {**key, "ip": self.get_ip(), "status": self.setup_status}
        self.put(
            table="Control",
            tuple=key,
            replace=True,
            priority=1,
            block=True,
            validate=True,
        )

    def _get_last_session(self):
        """
        This method fetches the last session for a given animal_id from the experiment.Session.

        It first fetches all sessions for the given animal_id. If no sessions are found,
        it returns 0.
        If sessions are found, it returns the maximum session number, which corresponds to
        the last session.

        Returns:
            int: The last session number or 0 if no sessions are found.
        """
        last_sessions = (
            experiment.Session() & dict(animal_id=self.get_setup_info("animal_id"))
        ).fetch("session")
        return 0 if np.size(last_sessions) == 0 else np.max(last_sessions)

    def log_session(self, params: Dict[str, Any], log_protocol: bool = False) -> None:
        """
        Logs a session with the given parameters and optionally logs the protocol.

        Args:
            params (Dict[str, Any]): Parameters for the session.
            log_protocol (bool): Whether to log the protocol information.
        """
        self._initialize_session()
        session_key = self._create_session_key(params)
        self._log_session_entry(session_key)

        if log_protocol:
            self._log_protocol_details()

        self._log_session_configs(params)
        self._set_setup_status(params)

        self.logger_timer.start()  # Start session time

    def _initialize_session(self) -> None:
        """
        Initializes session attributes.

        Args:
            params (Dict[str, Any]): Parameters for the session.
        """
        self.total_reward = 0
        self.trial_key = {
            "animal_id": self.get_setup_info("animal_id"),
            "trial_idx": 0,
            "session": self._get_last_session() + 1,
        }

    def _create_session_key(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a session key by merging trial key with session parameters.

        Args:
            params (Dict[str, Any]): Parameters for the session.

        Returns:
            Dict[str, Any]: The complete session key.
        """
        return {
            **self.trial_key,
            **params,
            "setup": self.setup,
            "user_name": params.get("user_name", "bot"),
        }

    def _log_session_entry(self, session_key: Dict[str, Any]) -> None:
        """
        Logs the session entry to the database.

        Args:
            session_key (Dict[str, Any]): The session key to log.
        """
        if self.manual_run:
            print("Logging Session:")
            pprint.pprint(session_key)
        self.put(
            table="Session", tuple=session_key, priority=1, validate=True, block=True
        )

    def _log_session_configs(self, params) -> None:
        """
        Logs the session and animal_id in configuration tables of behavior/stimulus.
        """

        # Logs the session and animal_id in configuration tables of behavior/stimulus.
        _schemas = ['behavior', 'stimulus']
        for schema in _schemas:
            self.put(
                table="Configuration",
                tuple=self.trial_key,
                schema=schema,
                priority=2,
                validate=True,
                block=True,
            )

        conf_table_schema = {
            "Port": "behavior",
            "Screen": "stimulus",
            "Ball": "behavior",
            "Speaker": "stimulus",
        }
        for config_table, schema in conf_table_schema.items():
            self._log_part_table_config(params, config_table, schema)

    def _log_part_table_config(
        self, params: Dict[str, Any], config_table: str, schema: str
    ) -> None:
        """
        Logs individual configuration type to the database.

        Args:
            params (Dict[str, Any]): Parameters for the session.
            config_table (str): The part table to be recorded (e.g., Port, Screen).
            schema (str): The schema for the configuration.
        """
        configuration_data = (
            getattr(experiment.SetupConfiguration, config_table)
            & {"setup_conf_idx": params["setup_conf_idx"]}
        ).fetch(as_dict=True)
        for conf in configuration_data:
            self.put(
                table=f"Configuration.{config_table}",
                tuple={**conf, **self.trial_key},
                schema=schema,
            )

    def _set_setup_status(self, params: Dict[str, Any]) -> None:
        """
        Sets the setup status and updates setup information.

        Args:
            params (Dict[str, Any]): Parameters for the session.
        """
        key = {
            "session": self.trial_key["session"],
            "trials": 0,
            "total_liquid": 0,
            "difficulty": 1,
            "state": "",
        }
        # if in the start_time is defined in the configuration use this
        # otherwise use the Control table
        if "start_time" in params:
            def tdelta(t):
                return datetime.strptime(t, "%H:%M:%S") - datetime.strptime(
                    "00:00:00", "%H:%M:%S"
                )
            key.update(
                {
                    "start_time": str(tdelta(params["start_time"])),
                    "stop_time": str(tdelta(params["stop_time"])),
                }
            )

        self.update_setup_info({**key, "status": self.setup_info["status"]})

    def update_setup_info(self, info: Dict[str, Any], key: Optional[Dict[str, Any]] = None):
        """
        This method updates the setup information with the provided info and key.

        It first fetches the existing setup information from the experiment's Control table,
        then updates it with the provided info. If 'status' is in the provided info, it blocks
        and validates the update operation.

        Args:
            info (dict): The information to update the setup with.
            key (dict, optional): Additional keys to fetch the setup information with.
            Defaults to an empty dict.

        Side Effects:
            Updates the setup_info attribute with the new setup information.
            Updates the setup_status attribute with the new status.
        """
        if key is None:
            key = dict()
        self.setup_info = {
            **(experiment.Control() & {**{"setup": self.setup}, **key}).fetch1(),
            **info,
        }
        block = True if "status" in info else False
        self.put(
            table="Control",
            tuple=self.setup_info,
            replace=True,
            priority=1,
            block=block,
            validate=block,
        )
        self.setup_status = self.setup_info["status"]

    def _log_protocol_details(self) -> None:
        """
        Save the protocol file,name and the git_hash in the database.
        """
        git_hash = (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
            .decode("ascii")
            .strip()
        )
        self.put(
            table="Session.Protocol",
            tuple={
                **self.trial_key,
                "protocol_name": self.protocol_path,
                "protocol_file": np.fromfile(self.protocol_path, dtype=np.int8),
                "git_hash": git_hash,
            },
        )

    def get_setup_info(self, field):
        return (experiment.Control() & dict(setup=self.setup)).fetch1(field)

    def get(self, schema='experiment', table='Control', fields='', key=dict(), **kwargs):
        """
        Fetches data from a specified table in a schema.

        Parameters:
        schema (str): The schema to fetch data from. Defaults to "experiment".
        table (str): The table to fetch data from. Defaults to "Control".
        fields (str): The fields to fetch. Defaults to "".
        key (dict): The key used to fetch data. Defaults to an empty dict.
        **kwargs: Additional keyword arguments.

        Returns:
        The fetched data.
        """
        table = rgetattr(eval(schema), table)
        return (table() & key).fetch(*fields, **kwargs)

    def update_trial_idx(self, trial_idx):
        """
        Updates the trial index in the trial_key dictionary.

        Args:
            trial_idx (int): The new trial index to be updated.
        """
        self.trial_key['trial_idx'] = trial_idx

    def ping(self, period=5000):
        """
        Sends a periodic ping to update setup information.

        This method updates the setup information at a specified interval (period).
        It records the current time, queue size,trial index, total liquid dispensed,
        and the current state of the system.

        Args:
            period (int, optional): The period in milliseconds between pings. Defaults to 5000.
        """
        if self.ping_timer.elapsed_time() >= period:  # occasionally update control table
            self.ping_timer.start()
            self.update_setup_info(
                {
                    "last_ping": str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    "queue_size": self.queue.qsize(),
                    "trials": self.trial_key["trial_idx"],
                    "total_liquid": self.total_reward,
                    "state": self.curr_state,
                }
            )

    def cleanup(self):
        while not self.queue.empty():
            print('Waiting for empty queue... qsize: %d' % self.queue.qsize())
            time.sleep(1)
        self.thread_end.set()

    def createDataset(
                    self,
                    dataset_name: str,
                    dataset_type: type,
                    filename: Optional[str] = None,
                    log: Optional[bool] = True,
                ) -> Any:
        """
        Create a dataset and return the dataset object.
        Args:
            target_path (str): The target path for the dataset.
            dataset_name (str): The name of the dataset.
            dataset_type (type): The datatype of the dataset.
            filename (str, optional): The filename for the h5 file. If not provided, 
            a default filename will be generated based on the dataset name, animal ID, 
            session, and current timestamp.
            log (bool, optional): If True call the log_recording
        Returns:
            Tuple[str, Any]: A tuple containing the filename and the dataset object.
        """
        folder = (f"Recordings/{self.trial_key['animal_id']}"
                  f"_{self.trial_key['session']}/")
        path = self.source_path + folder
        if not os.path.isdir(path):
            os.makedirs(path)  # create path if necessary

        if not os.path.isdir(self.target_path):
            print('No target directory set! Autocopying will not work.')
            target_path = False
        else:
            target_path = self.target_path + folder
            if not os.path.isdir(target_path):
                os.makedirs(target_path)

        # Generate filename if not provided
        if filename is None:
            filename = "%s_%d_%d_%s.h5" % (
                dataset_name,
                self.trial_key["animal_id"],
                self.trial_key["session"],
                datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            )

        if filename not in self.datasets:
            # create h5 file if not exists
            self.datasets[filename] = self.writer(path + filename, target_path)

        # create new dataset in the h5 files
        self.datasets[filename].createDataset(
            dataset_name, shape=(1,), dtype=dataset_type
        )

        if log:
            rec_key = dict(
                rec_aim=dataset_name,
                software="EthoPy",
                version=VERSION,
                filename=filename,
                source_path=path,
                target_path=target_path,
            )
            self.log_recording(rec_key)

        return self.datasets[filename]

    def log_recording(self, rec_key):
        recs = self.get(
            schema="recording",
            table="Recording",
            key=self.trial_key,
            fields=["rec_idx"],
        )        
        rec_idx = 1 if not recs else max(recs) + 1
        self.log('Recording', data={**rec_key, 'rec_idx': rec_idx}, schema='recording')

    def closeDatasets(self):
        for dataset in self.datasets:
            self.datasets[dataset].exit()

    @staticmethod
    def get_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip


@dataclass(order=True)
class PrioritizedItem:
    table: str = datafield(compare=False)
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
