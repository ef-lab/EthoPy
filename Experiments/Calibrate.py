import pygame, numpy
from Interface import *
from utils.TouchInterface import TouchInterface


class Calibrate:
    def __init__(self, logger, params):
        self.params = params
        self.logger = logger
        self.size = (800, 480)     # window size
        self.screen = TouchInterface()

    def run(self):
        """ Lickspout liquid delivery calibration """
        valve = RPProbe(self.logger, callbacks=False)
        print('Running calibration')
        try:
            for cal_idx in range(0, numpy.size(self.params['pulsenum'])):
                self.screen.cleanup()
                if self.params['save']:
                    self.screen.draw('Place zero-weighted pad under the probe', 0, 0, 800, 280)
                    button = self.screen.add_button(name='OK', x=300, y=300, w=200, h=100, color=(0, 128, 0))
                    while not button.is_pressed():
                        time.sleep(0.2)
                        if self.logger.setup_status == 'stop':
                            valve.cleanup()
                            self.screen.exit()
                            return
                for probe in self.params['probes']:
                    valve.create_pulse(probe, self.params['duration'][cal_idx])
                pulse = 0
                while pulse < self.params['pulsenum'][cal_idx]:
                    self.screen.cleanup()
                    msg = 'Pulse %d/%d' % (pulse + 1, self.params['pulsenum'][cal_idx])
                    self.screen.draw(msg)
                    print(msg)
                    for probe in self.params['probes']:
                        valve.create_pulse(probe, self.params['duration'][cal_idx])
                        valve.pulse_out(probe)  # release liquid
                        time.sleep(self.params['duration'][cal_idx] / 1000 + self.params['pulse_interval'][cal_idx] / 1000)
                    pulse += 1  # update trial
                if self.params['save']:
                    for probe in self.params['probes']:
                        self.screen.cleanup()
                        self.screen.draw('Enter weight for probe %d' % probe, 0, 0, 400, 300)
                        self.screen.add_numpad()
                        button = self.screen.add_button(name='OK', x=150, y=250, w=100, h=100, color=(0, 128, 0))
                        exit_button = self.screen.add_button(name='X', x=750, y=0, w=50, h=50, color=(25, 25, 25));
                        exit_flag = False
                        while not button.is_pressed() or self.screen.numpad == '':
                            time.sleep(0.2)
                            if exit_button.is_pressed(): exit_flag = True; break
                        if self.screen.numpad and not exit_flag:
                            self.logger.log_pulse_weight(self.params['duration'][cal_idx], probe,
                                                         self.params['pulsenum'][cal_idx], float(self.screen.numpad))  # insert
            self.screen.cleanup()
            self.screen.draw('Done calibrating')
        except:
            self.screen.cleanup()
            self.screen.draw('Error calibrating!')

        valve.cleanup()
        self.logger.update_setup_info({'status': 'ready'})
        time.sleep(2)
        self.screen.exit()

