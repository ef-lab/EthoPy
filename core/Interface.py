from time import sleep
import numpy as np
from utils.Timer import *
from utils.helper_functions import *
from concurrent.futures import ThreadPoolExecutor
import threading, multiprocessing, struct, time, socket
from datetime import datetime
from dataclasses import dataclass, fields, astuple
from dataclasses import field as datafield


class Interface:
    port, resp_tmst, ready_dur, activity_tmst, ready_tmst, pulse_rew, ports, response = 0, 0, 0, 0, 0, dict(), [], []
    ready, timer_ready, weight_per_pulse, pulse_dur, channels = False, Timer(), dict(), dict(), dict()

    def __init__(self, exp=[], beh=[], callbacks=True):
        self.callbacks = callbacks
        self.beh = beh
        self.exp = exp
        self.logger = exp.logger
        self.position = Port()
        self.position_tmst = 0

        # get port information
        for port in self.logger.get(table='SetupConfiguration.Port', key=self.exp.params, as_dict=True):
            self.ports.append(Port(**port))
        self.ports = np.array(self.ports)
        self.rew_ports = np.array([p.port for p in self.ports if p.reward])

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

    def set_running_state(self, running_state):
        pass

    def cleanup(self):
        pass

    def load_calibration(self):
        for port in list(set(self.rew_ports)):
            self.pulse_rew[port] = dict()
            key = dict(setup=self.logger.setup, port=port)
            dates = self.logger.get(schema='behavior', table='PortCalibration.Liquid',
                                    key=key, fields=['date'], order_by='date')
            if np.size(dates) < 1:
                print('No PortCalibration found!')
                self.exp.quit = True
                break
            key['date'] = dates[-1]  # use the most recent calibration
            self.pulse_dur[port], pulse_num, weight = self.logger.get(schema='behavior', table='PortCalibration.Liquid',
                                                                 key=key, fields=['pulse_dur', 'pulse_num', 'weight'])
            self.weight_per_pulse[port] = np.divide(weight, pulse_num)

    def calc_pulse_dur(self, reward_amount):  # calculate pulse duration for the desired reward amount
        actual_rew = dict()
        for port in self.rew_ports:
            if reward_amount not in self.pulse_rew[port]:
                duration = np.interp(reward_amount/1000, self.weight_per_pulse[port], self.pulse_dur[port])
                self._create_pulse(port, duration)
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

    def __init__(self, **kwargs):
        names = set([f.name for f in fields(self)])
        for k, v in kwargs.items():
            if k in names: setattr(self, k, v)
