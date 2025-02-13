"""
This module defines a Logger class used for managing data handling in an experimental setup.

It includes functionalities for logging experimental data, managing database connections,
controlling the flow of data from source to target locations, and supporting both manual
and automatic running modes. The Logger class manages threads for data insertion and setup
status updates.
"""
import importlib
import inspect
import json
import logging
import os
import pathlib
import platform
import pprint
import socket
import subprocess
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from dataclasses import field as datafield
from datetime import datetime
from os import environ
from queue import PriorityQueue
from typing import Any, Dict, List, Optional, Tuple, Union

import datajoint as dj
import numpy as np

from utils.helper_functions import create_virtual_modules, rgetattr
from utils.logging import setup_logging
from utils.Timer import Timer
from utils.Writer import Writer

# read the configuration from the local_conf.json
try:
    with open("local_conf.json", "r", encoding="utf-8") as f:
        config = json.load(f)
except FileNotFoundError:
    logging.error("Configuration file 'local_conf.json' not found.")
    raise
except json.JSONDecodeError:
    logging.error("Configuration file 'local_conf.json' is not a valid JSON.")
    raise
# set the datajoint parameters
dj.config.update(config["dj_local_conf"])
dj.logger.setLevel(dj.config["datajoint.loglevel"])

# Hides the Pygame welcome message
environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# Schema mappings
SCHEMATA = config["SCHEMATA"]

VERSION = "0.1"


def set_connection():
    """
    Establishes connections to database, creates virtual modules based on the provided
    schemata and assigns them to global variables. It also initializes the `public_conn`
    global variable.

    Globals:
        experiment: The virtual module for experiment.
        stimulus: The virtual module for stimulus.
        behavior: The virtual module for behavior.
        recording: The virtual module for recording.
        mice: The virtual module for mice.
        public_conn: The connection object for public access.

    Returns:
        None
    """
    global experiment, stimulus, behavior, recording, mice, public_conn
    virtual_modules, public_conn = create_virtual_modules(SCHEMATA)
    experiment = virtual_modules["experiment"]
    stimulus = virtual_modules["stimulus"]
    behavior = virtual_modules["behavior"]
    recording = virtual_modules["recording"]
    mice = virtual_modules["mice"]


set_connection()


class Logger:
    """
    Logger class for managing logging and data handling in an experimental setup.

    This class is designed to handle the logging of experimental data, manage database connections,
    and control the flow of data from source to target locations. It supports both manual and
    automatic running modes of a session, integrates with a Python logging setup, and manages
    threads for data insertion and setup status updates.

    Attributes:
        DEFAULT_SOURCE_PATH (str): Default path where data are saved locally.
        DEFAULT_TARGET_PATH (bool): Default target path where data will be moved after the session
        ends.
        setup (str): The hostname of the machine running the experiment.
        is_pi (bool): Flag indicating if the current machine is a Raspberry Pi.
        task_idx (int): Task index resolved from protocol parameters.
        protocol_path (str): Path to the protocol file.
        manual_run (bool): Flag indicating if the experiment is run manually.
        setup_status (str): Current status of the setup (e.g. 'running', 'ready').
        private_conn (Connection): Connection for internal database communication.
        writer (Writer): Writer class instance for handling data writing.
        rec_fliptimes (bool): Flag indicating if flip times should be recorded.
        trial_key (dict): Dictionary containing identifiers for the current trial.
        setup_info (dict): Dictionary containing setup information.
        datasets (dict): Dictionary containing datasets.
        lock (bool): Lock flag for thread synchronization.
        queue (PriorityQueue): Queue for managing data insertion order.
        ping_timer (Timer): Timer for managing pings.
        logger_timer (Timer): Timer for managing logging intervals.
        total_reward (int): Total reward accumulated.
        curr_state (str): Current state of the logger.
        thread_exception (Exception): Exception caught in threads, if any.
        source_path (str): Path where data are saved.
        target_path (str): Path where data will be moved after the session ends.
        thread_end (Event): Event to signal thread termination.
        thread_lock (Lock): Lock for thread synchronization.
        inserter_thread (Thread): Thread for inserting data into the database.
        getter_thread (Thread): Thread for periodically updating setup status.

    Methods:
        __init__(protocol=False): Initializes the Logger instance.
        _check_if_raspberry_pi(): Checks if the current machine is a Raspberry Pi.
        _resolve_protocol_parameters(protocol): Resolves protocol parameters.
        _set_path_from_local_conf(key, default): Sets path from local configuration.
        _initialize_schemata(): Initializes database schemata.
        _inserter(): Inserts data into the database.
        _log_setup_info(setup, status): Logs setup information.
        _get_setup_status(): Get setup status.
    """
    DEFAULT_SOURCE_PATH = os.path.join(os.path.expanduser("~"), "EthoPy_Files/")
    DEFAULT_TARGET_PATH = False

    def __init__(self, protocol=False):
        self.setup = socket.gethostname()
        self.is_pi = self._check_if_raspberry_pi()

        self.task_idx, self.protocol_path = self._resolve_protocol_parameters(protocol)

        # if the protocol path or task id is defined we consider that it runs manually
        self.manual_run = True if self.protocol_path else False
        # set the python logging
        setup_logging(self.manual_run)

        # if manual true run the experiment else set it to ready state
        self.setup_status = 'running' if self.manual_run else 'ready'

        # separate connection for internal communication
        self._schemata, self.private_conn = create_virtual_modules(
            SCHEMATA, create_tables=False, create_schema=False
        )

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
        self.thread_exception = None
        self.update_status = threading.Event()
        self.update_status.clear()

        # source path is the local path that data are saved
        self.source_path = self._set_path_from_local_conf("source_path", self.DEFAULT_SOURCE_PATH)
        # target path is the path that data will be moved after the session ends
        self.target_path = self._set_path_from_local_conf("target_path", self.DEFAULT_TARGET_PATH)

        # inserter_thread read the queue and insert the data in the database
        self.thread_end, self.thread_lock = threading.Event(), threading.Lock()
        self.inserter_thread = threading.Thread(target=self._inserter)
        self.inserter_thread.start()

        # _log_setup_info needs to run after the inserter_thread is started
        self._log_setup_info(self.setup, self.setup_status)

        # before starting the getter thread we need to _log_setup_info
        self.update_thread = threading.Thread(target=self._sync_control_table)
        self.update_thread.start()
        self.logger_timer.start()

    def _resolve_protocol_parameters(
            self, protocol: Union[str, int, None]) -> Tuple[Optional[int], Optional[str]]:
        """
        Parses the input protocol to determine its type and corresponding path.

        This method checks if the input protocol is a digit or a string. If it's a digit,
        it assumes the protocol is an ID and finds its corresponding path from Task table.
        If it's a string, it assumes the protocol is already a path. If the protocol
        is None or doesn't match these conditions, it returns None for both the protocol
        ID and path.

        Args:
            protocol (str|int|None): The input protocol, which can be an ID (digit) or a
        path (string).

        Returns:
            tuple: A tuple containing the protocol ID (int|None) and the protocol path (str|None).
        """
        if isinstance(protocol, int):
            return protocol, self._find_protocol_path(protocol)
        elif isinstance(protocol, str) and protocol.isdigit():
            protocol_id = int(protocol)
            return protocol_id, self._find_protocol_path(protocol_id)
        elif protocol:
            return None, protocol
        else:
            return None, None

    def get_protocol(self):
        """
        This method gets the protocol path.

        If the run is not manual, it fetches the task index from the setup info.
        It then finds the protocol path based on the task index and updates the protocol path.
        In the case the run is manual the protocol_path has been defined in Logger __init__.
        If the protocol path is not found, it raises a FileNotFoundError

        Returns:
            bool: True if the protocol path was successfully updated, False otherwise.
        """
        # find the protocol_path based on the task_id from the control table
        if not self.manual_run:
            self.task_idx = self.get_setup_info('task_idx')
            self.protocol_path = self._find_protocol_path(self.task_idx)
        # checks if the file exist
        if not os.path.isfile(self.protocol_path):
            error_msg = f"Protocol file does not exist at {self._protocol_path}"
            logging.error(error_msg)
            raise FileNotFoundError(error_msg)
        logging.info("Protocol path: %s", self.protocol_path)
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
        Set the protocol path.
        if protocol_path has only filename set the protocol_path at the conf directory.

        Args:
            protocol_path (str): The protocol path.
        """

        if protocol_path:
            path, filename = os.path.split(protocol_path)
            if not path:
                protocol_path = os.path.join(
                    str(pathlib.Path(__file__).parent.absolute()), "..", "conf", filename
                    )
        else:
            protocol_path = None
        self._protocol_path = protocol_path

    def _find_protocol_path(self, task_idx=None):
        """find the protocol path from the task index"""
        if task_idx:
            task_query = experiment.Task() & dict(task_idx=task_idx)
            if len(task_query) > 0:
                return task_query.fetch1("protocol")
            else:
                error_msg = f"There is no task_idx:{task_idx} in the tables Tasks"
                logging.info(error_msg)
                raise FileNotFoundError(error_msg)
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

    def _set_path_from_local_conf(self, path_key: str, default_path: str = None) -> str:
        """
        Get the path from the local_conf or create a new directory at the default path.

        Args:
            path_key (str): The key to look up in the configuration.
            default_path (str): The path to use if the key is not in the configuration.

        Returns:
            str: The path from the configuration or the default path.
        """
        path = config.get(path_key, default_path)
        if path:
            os.makedirs(path, exist_ok=True)
            logging.info("Set %s to directory: %s", path_key, path)
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

        This method creates a `PrioritizedItem` from the given keyword arguments and puts it into
        the queue. After putting an item in the queue, it checks the 'block' attribute of the item.
        If 'block' is False, it marks the item as processed by calling `task_done()`. This is useful
        in scenarios where items are processed asynchronously, and the queue needs to be notified
        that a task is complete. If 'block' is True, it waits for all items in the queue to be
        processed by calling `join()`.

        Args:
            **kwargs (Any): The keyword arguments used to create a `PrioritizedItem` and put it in the
        queue.
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

    def _handle_insert_error(self, item, table, exception, queue):
        """
        Handles an error by logging the error message, set the item.error=True, increase priority
        and add the item again in the queue for re-trying to insert later.

        Args:
            item : Description of parameter `item`.
            table : Description of parameter `table`.
            exception (Exception): The exception that was raised.
            thread_end : Description of parameter `thread_end`.
            queue : Description of parameter `queue`.
        """
        logging.warning(
            "Failed to insert:\n%s in %s\n With error:%s\nWill retry later",
            item.tuple, table, exception, exc_info=True,)
        item.error = True
        item.priority = item.priority + 2
        queue.put(item)

    @contextmanager
    def acquire_lock(self, lock):
        """
        Acquire a lock, yield control, and release the lock.

        This context manager ensures that the given lock is acquired before
        entering the block of code and released after exiting the block, even
        if an exception is raised within the block.

        Args:
            lock: The lock object to acquire and release.
        """
        lock.acquire()
        try:
            yield
        finally:
            lock.release()

    def _inserter(self):
        """
        This method continuously inserts items from the queue into their respective tables in
        the database.

        It runs in a loop until the thread_end event is set. In each iteration, it checks if
        the queue is empty. If it is, it sleeps for 0.5 seconds and then continues to the next
        iteration.
        If the queue is not empty, it gets an item from the queue, acquires the thread lock,
        and tries to insert the item into it's table.
        If an error occurs during the insertion, it handles the error. After the insertion,
        it releases the thread lock. If the item was marked to block, it marks the task as done.

        Returns:
            None
        """
        while not self.thread_end.is_set():
            if self.queue.empty():
                time.sleep(0.5)
                continue
            item = self.queue.get()
            table = rgetattr(self._schemata[item.schema], item.table)
            with self.acquire_lock(self.thread_lock):
                try:
                    self._insert_item(item, table)
                    self._validate_item(item, table)
                except Exception as insert_error:
                    if item.error:
                        self.thread_end.set()
                        logging.error("Second time failed to insert:\n %s in %s With error:\n %s",
                                      item.tuple, table, insert_error, exc_info=True)
                        self.thread_exception = insert_error
                        break
                    self._handle_insert_error(item, table, insert_error, self.queue)
            if item.block:
                self.queue.task_done()

    def _sync_control_table(self, update_period: float = 5000) -> None:
        """
        Synchronize the Control table by continuously fetching the setup status
        from the experiment schema and periodically updating the setup info.

        Runs in a loop until the thread_end event is set.

        Args:
            update_period (float): Time in milliseconds between Control table updates.
        """
        while not self.thread_end.is_set():
            with self.thread_lock:
                if self.update_status.is_set():
                    continue
                try:
                    self._fetch_setup_info()
                    self._update_setup_info(update_period)
                except Exception as error:
                    logging.exception("Error during Control table sync: %s", error)
                    self.thread_exception = error

            time.sleep(1)  # Cycle once a second

    def _fetch_setup_info(self) -> None:
        self.setup_info = (
            self._schemata["experiment"].Control() & {"setup": self.setup}
        ).fetch1()
        self.setup_status = self.setup_info["status"]

    def _update_setup_info(self, update_period: float) -> None:
        """
        Update the setup information if the elapsed time exceeds the update period.

        This method checks if the elapsed time since the last ping exceeds the given
        update period. If it does, it resets the ping timer and updates the setup
        information with the current state, queue size, trial index, total liquid reward,
        and the current timestamp. The updated information is then stored in the "Control"
        table with a priority of 1.
        """
        if self.ping_timer.elapsed_time() >= update_period:
            self.ping_timer.start()
            info = {
                "last_ping": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "queue_size": self.queue.qsize(),
                "trials": self.trial_key["trial_idx"],
                "total_liquid": self.total_reward,
                "state": self.curr_state,
            }
            self.setup_info.update(info)
            self.put(table="Control", tuple=self.setup_info, replace=True, priority=1)

    def log(self, table, data=None, **kwargs):
        """
        This method logs the given data into the specified table in the experiment database.

        It first gets the elapsed time from the logger timer and adds it to the data dictionary.
        It then puts the data into the specified table.

        Args:
            table (str): The name of the table in the experiment database.
            data (dict, optional): The data to be logged. Defaults to an empty dictionary.
            **kwargs: Additional keyword arguments to be passed to the put method.

        Returns:
            float: The elapsed time from the logger timer.
        """
        tmst = self.logger_timer.elapsed_time()
        data = data or {}  # if data is None or False use an empty dictionary
        self.put(table=table, tuple={**self.trial_key, "time": tmst, **data}, **kwargs)
        if table == "Trial.StateOnset":
            logging.info("State: %s", data["state"])
        return tmst

    def _log_setup_info(self, setup, setup_status='running'):
        """
        This method logs the setup information into the Control table in the experiment database.

        It first fetches the control information for the current setup. If no control information
        is found, it creates a new dictionary with the setup information.It then adds the IP and
        status information to the key.

        The method finally puts the key into the Control table, replacing any existing entry.
        Because it blocks the queue until the operation is complete it needs the inserter_thread
        to be running.

        Args:
            task (int, optional): The task index. Defaults to None.

        Returns:
            None
        """
        rel = experiment.Control() & dict(setup=setup)
        key = rel.fetch1() if np.size(rel.fetch()) else dict(setup=setup)
        key = {**key, "ip": self.get_ip(), "status": setup_status}
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
        # Initializes session parameters and logs the session start.
        self.logger_timer.start()  # Start session time
        self._init_session_params(params)

        # Save the protocol file, name and the git_hash in the database.
        if log_protocol:
            self._log_protocol_details()

        # update the configuration tables of behavior/stimulus schemas
        self._log_session_configs(params)

        #  Init the informations(e.g. trial_id=0, session) in control table
        self._init_control_table(params)



    def _init_session_params(self, params: Dict[str, Any]) -> None:
        """
        Initializes session parameters and logs the session start.

        This method initializes the session parameters by setting the total reward to zero
        and creating a trial key with the animal ID, trial index set to zero, and the session
        number incremented by one from the last session. It logs the trial key and creates a
        session key by merging the trial key with the provided session parameters, setup
        information, and a default or provided user name. The session key is then logged and
        stored in the database.

        Args:
            params (Dict[str, Any]): A dictionary containing parameters for initializing the
            session. This includes any additional information that should be merged into the
            session key.
        """
        self.total_reward = 0
        self.trial_key = {"animal_id": self.get_setup_info("animal_id"),
                          "trial_idx": 0,
                          "session": self._get_last_session() + 1}
        logging.info("\n%s\n%s\n%s", "#" * 70, self.trial_key, "#" * 70)
        # Creates a session key by merging trial key with session parameters.
        # TODO: Read the user name from the Control Table
        session_key = {**self.trial_key, **params, "setup": self.setup,
                       "user_name": params.get("user_name", "bot"),
                       "logger_tmst": self.logger_timer.start_time}
        logging.info("session_key:\n%s", pprint.pformat(session_key))
        # Logs the new session id to the database
        self.put(table="Session", tuple=session_key, priority=1, validate=True, block=True)

    @staticmethod
    def get_inner_classes_list(outer_class):
        """
        Retrieve a list of names of all inner classes defined within an outer class.

        Args:
            outer_class: The class object of the outer class containing the inner classes.

        Returns:
            A list of strings, each representing the fully qualified name of an inner class
            defined within the outer class.
        """
        outer_class_dict_values = outer_class.__dict__.values()
        inner_classes = [value for value in outer_class_dict_values if isinstance(value, type)]
        return [outer_class.__name__+'.'+cls.__name__ for cls in inner_classes]

    def _log_session_configs(self, params) -> None:
        """
        Logs the parameters of a session into the appropriate schema tables.

        This method performs several key operations to ensure that the configuration of a session,
        including behavior and stimulus settings, is accurately logged into the database.It involves
        the following steps:
        1. Identifies the relevant modules (e.g., core.Behavior, core.Stimulus) that contain
        Configuration classes.
        2. Derives schema names from these modules, assuming the schema name matches the class
        name in lowercase.
        3. Logs the session and animal_id into the Configuration tables of the identified schemas.
        4. Creates a dictionary mapping each schema to its respective Configuration class's
        inner classes.
        5. Calls a helper method to log the configuration of sub-tables for each schema.
        """
        # modules that have a Configuration classes
        _modules = ['core.Behavior', 'core.Stimulus']
        # consider that the module have the same name as the schema but in lower case
        # (e.g for class Behaviour the schema is the behavior)
        _schemas = [_module.split('.')[1].lower() for _module in _modules]

        # Logs the session and animal_id in configuration tables of behavior/stimulus.
        for schema in _schemas:
            self.put(table="Configuration", tuple=self.trial_key, schema=schema, priority=2,
                     validate=True, block=True,)

        # create a dict with the configuration as key and the subclasses as values
        conf_table_schema = {}
        for _schema, _module in zip(_schemas, _modules):
            conf = importlib.import_module(_module).Configuration
            # Find the inner classes of the class Configuration
            conf_table_schema[_schema] = self.get_inner_classes_list(conf)

        # update the sub tables of Configuration table
        for schema, config_tables in conf_table_schema.items():
            self._log_sub_tables_config(params, config_tables, schema)

    def _log_sub_tables_config(
        self, params: Dict[str, Any], config_tables: List, schema: str
    ) -> None:
        """
        This method iterates over a list of configuration tables, retrieves the configuration data
        for each table based on the provided parameters, and then logs this data into the respective
        table within the given schema.

        Args:
            params (Dict[str, Any]): Parameters for the setup conf.
            config_table (str): The part table to be recorded (e.g., Port, Screen).
            schema (str): The schema for the configuration.
        """
        for config_table in config_tables:
            configuration_data = (
                getattr(experiment.SetupConfiguration, config_table.split('.')[1])
                & {"setup_conf_idx": params["setup_conf_idx"]}
            ).fetch(as_dict=True)
            # put the configuration data in the configuration table
            # it can be a list of configurations (e.g have two ports with different ids)
            for conf in configuration_data:
                self.put(
                    table=config_table,
                    tuple={**conf, **self.trial_key},
                    schema=schema,
                )

    def _init_control_table(self, params: Dict[str, Any]) -> None:
        """
        Set the control table informations for the setup.

        This method sets various parameters related to the session setup, including
        session ID, number of trials, total liquid, difficulty level, and state. It also
        optionally sets start and stop times if they are provided in the `params` argument.

        The start and stop times are expected to be in "%H:%M:%S" format. If they are provided,
        this method calculates the time delta from "00:00:00" for each and updates the setup
        information accordingly.

        Args:
            params (Dict[str, Any]): A dictionary containing parameters for the session setup.
                This may include 'start_time' and 'stop_time' among other setup parameters.
        """
        key = {
            "session": self.trial_key["session"],
            "trials": 0,
            "total_liquid": 0,
            "difficulty": 1,
            "state": "",
        }
        # TODO in the case the task is the path of the config there is no update in Control table
        if self.task_idx and isinstance(self.task_idx, int):
            key["task_idx"] = self.task_idx
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

    def check_connection(self, host="8.8.8.8", port=53, timeout=0.1):
        """
        Check if the internet connection is available by attempting to connect to a
        specified host and port.

        Args:
            host (str): The host to connect to. Defaults to '8.8.8.8' (Google DNS).
            port (int): The port to connect on. Defaults to 53 (DNS service).
            timeout (int): The timeout in seconds for the connection attempt.
            Defaults to 0.1 seconds.

        Returns:
            bool: True if the connection is successful, False otherwise.
        """
        try:
            socket.setdefaulttimeout(timeout)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                return True
        except socket.error:
            return False

    def update_setup_info(self, info: Dict[str, Any], key: Optional[Dict[str, Any]] = None):
        """
        This method updates the setup information in Control table with the provided info and key.

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
        if self.thread_exception:
            self.thread_exception = None
            raise Exception("Thread exception occurred: %s", self.thread_exception)
        if key is None:
            key = dict()

        if not public_conn.is_connected:
            set_connection()

        block = True if "status" in info else False
        if block:
            self.update_status.set()
            caller = inspect.stack()[1]
            caller_info = (f"Function called by {caller.function} "
                           f"in {caller.filename} at line {caller.lineno}")
            logging.info("Update status is set %s\n%s", info['status'], caller_info)

        self.setup_info = {**(experiment.Control() & {**{"setup": self.setup}, **key}).fetch1(),
                           **info}

        if 'notes' in info and len(info['notes']) > 255:
            info['notes'] = info['notes'][:255]

        self.put(
            table="Control",
            tuple=self.setup_info,
            replace=True,
            priority=1,
            block=block,
            validate=block,
        )
        self.setup_status = self.setup_info["status"]
        self.update_status.clear()

    def _log_protocol_details(self) -> None:
        """
        Save the protocol file,name and the git_hash in the database.
        """
        git_hash = (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
            .decode("ascii")
            .strip()
        )
        logging.info("Git hash: %s", git_hash)
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
        """
        Retrieve specific setup information from an experiment control table.

        Args:
            field: The name of the field to fetch from the experiment control setup.

        Returns:
            The value of the specified field from the experiment control setup.
        """
        return (experiment.Control() & dict(setup=self.setup)).fetch1(field)

    def get(self, schema='experiment', table='Control',
            fields: Optional[List] = None, key: Optional[Dict] = None,
            **kwargs):
        """
        Fetches data from a specified table in a schema.

        Args:
            schema (str): The schema to fetch data from. Defaults to "experiment".
            table (str): The table to fetch data from. Defaults to "Control".
            fields (dict): The fields to fetch. Defaults to "".
            key (dict): The key used to fetch data. Defaults to an empty dict.
            **kwargs: Additional keyword arguments.

        Returns:
            The fetched data.
        """
        if key is None:
            key = dict()
        if fields is None:
            fields = []
        table = rgetattr(eval(schema), table)
        return (table() & key).fetch(*fields, **kwargs)

    def get_table_keys(self, schema='experiment', table='Control', 
                       key: Optional[Dict] = None, key_type=Optional[str]):
        """
        Retrieve the primary key of a specified table within a given schema.

        Args:
            schema (str): The schema name where the table is located. Default is 'experiment'.
            table (str): The table name from which to retrieve the keys. Default is 'Control'.
            key (dict): A dict with the key to filter the table. Default is an empty dictionary.

        Returns:
            list: The primary key of the specified table.
        """
        if key is None:
            key = []
        table = rgetattr(eval(schema), table)
        if key_type == 'primary':
            return (table() & key).primary_key
        return (table() & key).heading.names

    def update_trial_idx(self, trial_idx):
        """
        Updates the trial index in the trial_key dictionary and check if there is any
        exception in the threads.

        Args:
            trial_idx (int): The new trial index to be updated.
        """
        self.trial_key['trial_idx'] = trial_idx
        logging.info("\nTrial idx: %s",  self.trial_key['trial_idx'])
        if self.thread_exception:
            self.thread_exception = None
            raise Exception("Thread exception occurred: %s", self.thread_exception)

    def cleanup(self):
        """
        Waits for the logging queue to be empty and signals the logging thread to end.

        This method checks if the logging queue is empty, and if not, it waits until it
        becomes empty. Once the queue is empty, it sets the thread_end event to signal
        the logging thread to terminate.
        """
        while not self.queue.empty() and not self.thread_end.is_set():
            logging.info('Waiting for empty queue... qsize: %d', self.queue.qsize())
            time.sleep(1)
        self.thread_end.set()

        if not self.queue.empty():
            logging.warning('Clean up finished but queue size is: %d', self.queue.qsize())

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
            filename = (f"{dataset_name}_{self.trial_key['animal_id']}_"
                        f"{self.trial_key['session']}_"
                        f"{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.h5")
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
        """
        Logs a new recording entry with an incremented recording index.

        This method retrieves the current recordings associated with the trial,
        calculates the next recording index (rec_idx) by finding the maximum
        recording index and adding one, and logs the new recording entry with
        the provided recording key (rec_key) and the calculated recording index.

        Args:
        - rec_key (dict): A dictionary containing the key information for the recording entry.

        The method assumes the existence of a `get` method to retrieve existing recordings
        and a `log` method to log the new recording entry.
        """
        recs = self.get(
            schema="recording",
            table="Recording",
            key=self.trial_key,
            fields=["rec_idx"],
        )
        rec_idx = 1 if not recs else max(recs) + 1
        self.log('Recording', data={**rec_key, 'rec_idx': rec_idx}, schema='recording')

    def closeDatasets(self):
        """
        Closes all datasets managed by this instance.

        Iterates through the datasets dictionary, calling the `exit` method on each dataset
        object to properly close them.
        """
        for _, dataset in self.datasets.items():
            dataset.exit()

    @staticmethod
    def get_ip():
        """
        Retrieves the local IP address of the machine.

        Attempts to establish a dummy connection to a public DNS server (8.8.8.8) to determine
        the local network IP address of the machine. If the connection fails, defaults to
        localhost (127.0.0.1).

        Returns:
            str: The local IP address.
        """
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
