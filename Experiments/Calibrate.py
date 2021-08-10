import numpy
import time as systime
from core.Interface import *
from utils.TouchInterface import TouchInterface


class Experiment:
    def setup(self, logger, params):
        self.params = params
        self.logger = logger
        self.size = (800, 480)     # window size
        self.screen = TouchInterface()

    def run(self):
        """ Lickspout liquid delivery calibration """
        self.valve = RPProbe(exp=self, callbacks=False)
        print('Running calibration')
        if self.params['save']:
            pressure, exit_flag = self.button_input('Enter air pressure (PSI)')
            self.screen.cleanup()
            if exit_flag:
                self.screen.draw('Exiting!')
                time.sleep(.5)
                self.exit()
                return
        for cal_idx in range(0, numpy.size(self.params['pulsenum'])):
            self.screen.cleanup()
            if self.params['save']:
                self.screen.draw('Place zero-weighted pad under the port', 0, 0, 800, 280)
                button = self.screen.add_button(name='OK', x=300, y=300, w=200, h=100, color=(0, 128, 0))
                while not button.is_pressed():
                    time.sleep(0.2)
                    if self.logger.setup_status == 'stop':
                        self.exit()
                        return
            pulse = 0
            while pulse < self.params['pulsenum'][cal_idx]:
                self.screen.cleanup()
                msg = 'Pulse %d/%d' % (pulse + 1, self.params['pulsenum'][cal_idx])
                self.screen.draw(msg)
                print('\r' + msg, end='')
                for port in self.params['ports']:
                    try:
                        self.valve.give_liquid(port, self.params['duration'][cal_idx])
                    except Exception as e:
                        self.screen.draw('ERROR:', str(e))
                        time.sleep(1)
                        self.exit()
                    time.sleep(self.params['duration'][cal_idx] / 1000 + self.params['pulse_interval'][cal_idx] / 1000)
                pulse += 1  # update trial
            if self.params['save']:
                for port in self.params['ports']:
                    value, exit_flag = self.button_input('Enter weight for port %d' % port)
                    if value and not exit_flag:
                        self.log_pulse_weight(self.params['duration'][cal_idx], port,
                                                     self.params['pulsenum'][cal_idx], value, pressure)
                    elif exit_flag:
                        self.exit()
                        return
        self.exit()

    def exit(self):
        self.screen.cleanup()
        self.screen.draw('Done calibrating')
        self.valve.cleanup()
        self.logger.update_setup_info({'status': 'ready'})
        time.sleep(2)
        self.screen.exit()

    def button_input(self, message):
        self.screen.cleanup()
        self.screen.draw(message, 0, 0, 400, 300)
        self.screen.add_numpad()
        button = self.screen.add_button(name='OK', x=150, y=250, w=100, h=100, color=(0, 128, 0))
        exit_button = self.exit_input()
        exit_flag = False
        while not button.is_pressed() or self.screen.numpad == '':
            time.sleep(0.2)
            if exit_button.is_pressed(): exit_flag = True; value = None; break
        if self.screen.numpad and not exit_flag:
            value = float(self.screen.numpad)
        return value, exit_flag

    def exit_input(self):
        exit_button = self.screen.add_button(name='X', x=750, y=0, w=50, h=50, color=(25, 25, 25))
        return exit_button

    def log_pulse_weight(self, pulse_dur, port, pulse_num, weight=0, pressure=0):
        key = dict(setup=self.logger.setup, port=port, date=systime.strftime("%Y-%m-%d"), pressure=pressure)
        self.logger.put(table='PortCalibration', tuple=key, schema='behavior', priority=5,
                        ignore_extra_fields=True, validate=True, block=True, replace=True)
        self.logger.put(table='PortCalibration.Liquid',  schema='behavior', replace=True, ignore_extra_fields=True,
                        tuple=dict(key, pulse_dur=pulse_dur, pulse_num=pulse_num, weight=weight))
