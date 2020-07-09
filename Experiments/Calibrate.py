import pygame, numpy
from Probe import *
from utils.Interface import Interface


class Calibrate:
    def __init__(self, logger, params):
        self.params = params
        self.logger = logger
        self.size = (800, 480)     # window size
        self.screen = Interface()

    def run(self):
        """ Lickspout liquid delivery calibration """
        valve = RPProbe(self.logger)
        print('Running calibration')

        for cal_idx in range(0, numpy.size(self.params['pulsenum'])):
            self.screen.cleanup()
            self.screen.draw('Place zero-weighted pad under the probe', 0, 0, 800, 280)
            button = self.screen.add_button(name='OK', x=300, y=300, w=200, h=100, color=(0, 128, 0))
            while not button.is_pressed():
                time.sleep(0.2)
                if self.logger.get_setup_info('status') == 'stop':
                    valve.cleanup()
                    self.screen.exit()
                    return

            pulse = 0
            while pulse < self.params['pulsenum'][cal_idx]:
                self.screen.cleanup()
                self.screen.draw('Pulse %d/%d' % (pulse + 1, self.params['pulsenum'][cal_idx]))
                for probe in self.params['probes']:
                    valve.give_liquid(probe, self.params['duration'][cal_idx])  # release liquid
                time.sleep(self.params['duration'][cal_idx] / 1000 + self.params['pulse_interval'][cal_idx] / 1000)
                pulse += 1  # update trial
            if self.params['save']:
                for probe in self.params['probes']:
                    self.screen.cleanup()
                    self.screen.draw('Enter weight for probe %d' % probe, 0, 0, 400, 300)
                    self.screen.add_numpad()
                    button = self.screen.add_button(name='OK', x=150, y=250, w=100, h=100, color=(0, 128, 0))
                    while not button.is_pressed():
                        time.sleep(0.2)
                    self.logger.log_pulse_weight(self.params['duration'][cal_idx], probe,
                                                 self.params['pulsenum'][cal_idx], float(self.screen.numpad))  # insert
        valve.cleanup()
        self.screen.cleanup()
        self.screen.draw('Done calibrating')
        time.sleep(5)
        self.screen.exit()
        self.logger.update_setup_status('stop')
