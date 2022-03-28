from time import sleep
import numpy as np
from utils.Timer import *
from utils.helper_functions import *
from concurrent.futures import ThreadPoolExecutor
import threading, multiprocessing, struct, time, socket
from datetime import datetime


class Interface:
    port, lick_tmst, ready_dur, activity_tmst, ready_tmst, pulse_rew, ports = 0, 0, 0, 0, 0, dict(), []
    ready, logging, timer_ready, weight_per_pulse, pulse_dur, channels = False, True, Timer(), dict(), dict(), dict()

    def __init__(self, exp=[], callbacks=True, logging=True):
        self.callbacks = callbacks
        self.logging = logging
        self.exp = exp
        self.logger = exp.logger

    def load_calibration(self):
        for port in list(set(self.ports)):
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

    def give_liquid(self, port, duration=False, log=True):
        pass

    def give_odor(self, odor_idx, duration, log=True):
        pass

    def give_sound(self, sound_freq, duration, dutycycle):
        pass

    def get_last_lick(self):
        port = self.port
        self.port = 0
        return port, self.lick_tmst

    def in_position(self):
        return True, 0

    def create_pulse(self, port, duration):
        pass

    def sync_out(self, state=False):
        pass

    def set_running_state(self, running_state):
        pass

    def log_activity(self, table, key):
        self.activity_tmst = self.logger.logger_timer.elapsed_time()
        key.update({'time': self.activity_tmst, **self.logger.trial_key})
        if self.logging and self.exp.running:
            self.logger.log('Activity', key, schema='behavior', priority=10)
            self.logger.log('Activity.' + table, key, schema='behavior')
        return self.activity_tmst

    def calc_pulse_dur(self, reward_amount):  # calculate pulse duration for the desired reward amount
        actual_rew = dict()
        for port in list(set(self.ports)):
            if reward_amount not in self.pulse_rew[port]:
                duration = np.interp(reward_amount/1000, self.weight_per_pulse[port], self.pulse_dur[port])
                self._create_pulse(port, duration)
                self.pulse_rew[port][reward_amount] = np.max((np.min(self.weight_per_pulse[port]),
                                                              reward_amount/1000)) * 1000 # in uL
            actual_rew[port] = self.pulse_rew[port][reward_amount]
        return actual_rew

    def cleanup(self):
        pass

    def createDataset(self, path, target_path, dataset_name, dataset_type):
        self.filename = '%s_%d_%d_%s.h5' % (dataset_name, self.logger.trial_key['animal_id'],
                                         self.logger.trial_key['session'],
                                         datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
        self.datapath = path + self.filename
        self.dataset = self.Writer(self.datapath, target_path)
        self.dataset.createDataset(dataset_name, shape=(len(dataset_type.names),), dtype=dataset_type)
        return self.filename

    def closeDatasets(self):
        self.dataset.exit()
