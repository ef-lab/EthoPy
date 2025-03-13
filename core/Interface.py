import multiprocessing
import socket
import struct
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import astuple, dataclass, fields
from dataclasses import field as datafield
from datetime import datetime
from importlib import import_module
from time import sleep

import datajoint as dj
import numpy as np

from core.Logger import experiment, interface  # pylint: disable=W0611, # noqa: F401
from utils.helper_functions import *
from utils.Timer import *


class Interface:
    port, resp_tmst, ready_dur, activity_tmst, ready_tmst, pulse_rew, ports, response, duration = 0, 0, 0, 0, 0, dict(), [], [], dict()
    ready, timer_ready, weight_per_pulse, pulse_dur, channels, position_dur = False, Timer(), dict(), dict(), dict(),0

    def __init__(self, exp=[], beh=[], callbacks=True):
        self.callbacks = callbacks
        self.beh = beh
        self.exp = exp
        self.logger = exp.logger
        self.position = Port()
        self.position_tmst = 0
        self.camera = None

        # get port information
        for port in self.logger.get(schema='interface', table='SetupConfiguration.Port', key=self.exp.params, as_dict=True):
            self.ports.append(Port(**port))
        self.ports = np.array(self.ports)
        self.proximity_ports = np.array([p.port for p in self.ports if p.type == 'Proximity'])
        self.rew_ports = np.array([p.port for p in self.ports if p.reward])

        # check is the setup idx has a camera and initialize it
        if self.exp.params["setup_conf_idx"] in self.logger.get(
            schema='interface', table="SetupConfiguration.Camera", fields=["setup_conf_idx"]
        ):
            camera_params = self.logger.get(
                schema='interface',
                table="SetupConfiguration.Camera",
                key=f"setup_conf_idx={self.exp.params['setup_conf_idx']}",
                as_dict=True,
            )[0]
            _camera = getattr(
                import_module("Interfaces.Camera"), camera_params["discription"]
            )
            self.camera = _camera(
                filename=(f"{self.logger.trial_key['animal_id']}"
                          f"_{self.logger.trial_key['session']}"),
                logger=self.logger,
                logger_timer = self.logger.logger_timer,
                video_aim = camera_params.pop('video_aim'),
                **camera_params,
            )

    def give_liquid(self, port, duration=False, log=True):
        pass

    def give_odor(self, odor_idx, duration, log=True):
        pass

    def give_sound(self, sound_freq, duration, dutycycle):
        pass

    def in_position(self):
        return True, 0

    def create_pulse(self, port, duration):
        pass

    def sync_out(self, state=False):
        pass

    def set_operation_status(self, operation_status):
        pass

    def cleanup(self):
        pass

    def release(self):
        if self.camera:
            print("Release camear"*10)
            if self.camera.recording.is_set(): self.camera.stop_rec()

    def load_calibration(self):
        for port in list(set(self.rew_ports)):
            self.pulse_rew[port] = dict()
            key = dict(setup=self.logger.setup, port=port)
            dates = self.logger.get(schema='interface', table='PortCalibration.Liquid',
                                    key=key, fields=['date'], order_by='date')
            if np.size(dates) < 1:
                print('No PortCalibration found!')
                self.exp.quit = True
                break
            key['date'] = dates[-1]  # use the most recent calibration
            self.pulse_dur[port], pulse_num, weight = self.logger.get(schema='interface', table='PortCalibration.Liquid',
                                                                 key=key, fields=['pulse_dur', 'pulse_num', 'weight'])
            self.weight_per_pulse[port] = np.divide(weight, pulse_num)

    def calc_pulse_dur(self, reward_amount):  # calculate pulse duration for the desired reward amount
        actual_rew = dict()
        for port in self.rew_ports:
            if reward_amount not in self.pulse_rew[port]:
                self.duration[port] = np.interp(reward_amount/1000, self.weight_per_pulse[port], self.pulse_dur[port])
                self.pulse_rew[port][reward_amount] = np.max((np.min(self.weight_per_pulse[port]),
                                                              reward_amount/1000)) * 1000 # in uL
            actual_rew[port] = self.pulse_rew[port][reward_amount]
        return actual_rew

    def _channel2port(self, channel, category='Proximity'):
        port = reverse_lookup(self.channels[category], channel) if channel else 0
        if port: port = self.ports[Port(type=category, port=port) == self.ports][0]
        return port


@dataclass
class Port:
    port: int = datafield(compare=True, default=0, hash=True)
    type: str = datafield(compare=True, default='', hash=True)
    ready: bool = datafield(compare=False, default=False)
    reward: bool = datafield(compare=False, default=False)
    response: bool = datafield(compare=False, default=False)
    invert: bool = datafield(compare=False, default=False)
    state: bool = datafield(compare=False, default=False)

    def __init__(self, **kwargs):
        names = set([f.name for f in fields(self)])
        for k, v in kwargs.items():
            if k in names: setattr(self, k, v)


@interface.schema
class SetupConfiguration(dj.Lookup, dj.Manual):
    """DataJoint table for configuring the setup interfaces.

    The user can define all harware configuration by defining only the setup index.
    """

    definition = """
    # Setup configuration
    setup_conf_idx           : tinyint      # configuration version
    ---
    interface                : enum('DummyPorts','RPPorts', 'PCPorts', 'RPVR')
    discription              : varchar(256)
    """

    contents = [
        [0, "DummyPorts", "Simulation"],
    ]

    class Port(dj.Lookup, dj.Part):
        """Port configuration table."""

        definition = """
        # Probe identityrepeat_n = 1

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

        contents = [
            [1, "Lick", 0, 0, 1, 1, 0, "probe"],
            [2, "Lick", 0, 0, 1, 1, 0, "probe"],
            [3, "Proximity", 0, 1, 0, 0, 0, "probe"],
        ]

    class Screen(dj.Lookup, dj.Part):
        """Screen configuration table."""

        definition = """
        # Screen information
        screen_idx               : tinyint
        -> SetupConfiguration
        ---
        intensity                : tinyint UNSIGNED
        distance                 : float
        center_x                 : float
        center_y                 : float
        aspect                   : float
        size                     : float
        fps                      : tinyint UNSIGNED
        resolution_x             : smallint
        resolution_y             : smallint
        description              : varchar(256)
        fullscreen               : tinyint
        """

        contents = [
            [1, 0, 64, 5.0, 0, -0.1, 1.66, 7.0, 30, 800, 480, "Simulation", 0],
        ]

    class Ball(dj.Lookup, dj.Part):
        """Ball configuration table."""

        definition = """
        # Ball information
        -> SetupConfiguration
        ---
        ball_radius=0.125        : float                   # in meters
        material="styrofoam"     : varchar(64)             # ball material
        coupling="bearings"      : enum('bearings','air')  # mechanical coupling
        discription              : varchar(256)
        """

    class Speaker(dj.Lookup, dj.Part):
        """Speaker configuration table."""

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

    class Camera(dj.Lookup, dj.Part):
        """Camera configuration table."""

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


@interface.schema
class Configuration(dj.Manual):
    """DataJoint table for saving setup configurations for each session."""

    definition = """
    # Session behavior configuration info
    -> experiment.Session
    """

    class Port(dj.Part):
        """Port configuration table."""

        definition = """
        # Probe identity
        -> Configuration
        port                     : tinyint                      # port id
        type="Lick"              : varchar(24)                 # port type
        ---
        ready=0                  : tinyint                      # ready flag
        response=0               : tinyint                      # response flag
        reward=0                 : tinyint                      # reward flag
        discription              : varchar(256)
        """

    class Ball(dj.Part):
        """Ball configuration table."""

        definition = """
        # Ball information
        -> Configuration
        ---
        ball_radius=0.125        : float                   # in meters
        material="styrofoam"     : varchar(64)             # ball material
        coupling="bearings"      : enum('bearings','air')  # mechanical coupling
        discription              : varchar(256)
        """

    class Screen(dj.Part):
        """Screen configuration table."""

        definition = """
        # Screen information
        -> Configuration
        screen_idx               : tinyint
        ---
        intensity                : tinyint UNSIGNED
        distance         : float
        center_x         : float
        center_y         : float
        aspect           : float
        size             : float
        fps                      : tinyint UNSIGNED
        resolution_x             : smallint
        resolution_y             : smallint
        description              : varchar(256)
        """

    class Speaker(dj.Part):
        """Speaker configuration table."""

        definition = """
        # Speaker information
        speaker_idx             : tinyint
        -> Configuration
        ---
        sound_freq=10000        : int           # in Hz
        duration=500            : int           # in ms
        volume=50               : tinyint       # 0-100 percentage
        discription             : varchar(256)
        """


@interface.schema
class PortCalibration(dj.Manual):
    """Liquid delivery calibration sessions for each port with water availability."""

    definition = """
    # Liquid delivery calibration sessions for each port with water availability
    setup                        : varchar(256)  # Setup name
    port                         : tinyint       # port id
    date                         : date # session date (only one per day is allowed)
    """

    class Liquid(dj.Part):
        """Datajoint table for volume per pulse duty cycle estimation."""

        definition = """
        # Data for volume per pulse duty cycle estimation
        -> PortCalibration
        pulse_dur                    : int       # duration of pulse in ms
        ---
        pulse_num                    : int       # number of pulses
        weight                       : float     # weight of total liquid released in gr
        timestamp=CURRENT_TIMESTAMP  : timestamp # timestamp
        pressure=0                   : float     # air pressure (PSI)
        """

    class Test(dj.Part):
        """Datajoint table for Lick Test."""

        definition = """
        # Lick timestamps
        setup                        : varchar(256)                 # Setup name
        port                         : tinyint                      # port id
        timestamp=CURRENT_TIMESTAMP  : timestamp
        ___
        result=null                  : enum('Passed','Failed')
        pulses=null                  : int
        """
