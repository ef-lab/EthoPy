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
            self.screen.draw('Place zero-weighted pad', 0, 0, 300, 480, (0, 128, 0), 40)
            button = self.screen.add_button(name='OK', x=500, y=300, w=100, h=100, color=(0, 128, 0))
            while not button.is_pressed():
                time.sleep(0.2)

            pulse = 0
            while pulse < self.params['pulsenum'][cal_idx]:
                self.screen.clear()
                self.screen.draw('Pulse %d/%d' % (pulse + 1, self.params['pulsenum'][cal_idx]))
                for probe in self.params['probes']:
                    valve.give_liquid(probe, self.params['duration'][cal_idx], False)  # release liquid
                time.sleep(self.params['duration'][cal_idx] / 1000 + self.params['pulse_interval'][cal_idx] / 1000)
                pulse += 1  # update trial
            if self.params['save']:
                for probe in self.params['probes']:
                    self.screen.clear()
                    self.screen.draw('Enter weight for probe %d' % probe, 0, 0, 400, 480, (0, 128, 0), 40)
                    self.screen.add_numpad()
                    button = self.screen.add_button(name='OK', x=500, y=300, w=100, h=100)
                    while not button.is_pressed():
                        time.sleep(0.2)
                    self.logger.log_pulse_weight(self.params['duration'][cal_idx], probe,
                                                 self.params['pulsenum'][cal_idx], float(self.screen.numpad))  # insert
        valve.cleanup()
        self.screen.draw('Done calibrating')
        self.screen.exit()
