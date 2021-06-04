import pygame, numpy
from Interface import *
from utils.TouchInterface import TouchInterface


class ProbeTest:
    def __init__(self, logger, params):
        self.params = params
        self.logger = logger
        self.size = (800, 480)     # window size
        self.screen = TouchInterface()
        self.result = dict()

    def run(self):
        """ Lickspout liquid delivery test """
        self.valve = RPProbe(self.logger, callbacks=True, logging=False)
        print('Running probe test')
        for probe in self.params['probes']:
            self.result[probe] = False
            tmst = self.logger.logger_timer.elapsed_time()
            for cal_idx in range(0, numpy.size(self.params['pulsenum'])):
                self.screen.cleanup()
                self.valve.create_pulse(probe, self.params['duration'][cal_idx])
                pulse = 0
                while pulse < self.params['pulsenum'][cal_idx] and not self.result[probe]:
                    self.screen.cleanup()
                    msg = 'Pulse %d/%d' % (pulse + 1, self.params['pulsenum'][cal_idx])
                    self.screen.draw(msg)
                    print(msg)
                    self.valve.create_pulse(probe, self.params['duration'][cal_idx])
                    self.valve.pulse_out(probe)  # release liquid
                    time.sleep(self.params['duration'][cal_idx] / 1000 + self.params['pulse_interval'][cal_idx] / 1000)
                    pulse += 1  # update trial
                    if self.get_response(tmst):
                        self.result[probe] = True
                        self.screen.cleanup()
                        self.screen.draw('Probe %d test passed!' % probe)
                        self.logger.log('ProbeTest', dict(setup=self.logger.setup, probe=probe, result='Passed'))
                        time.sleep(1)
                if self.result[probe]:
                    break
            if not self.result[probe]:
                self.screen.draw('Probe %d test failed!' % probe)
                self.logger.log('ProbeTest', dict(setup=self.logger.setup, probe=probe, result='Failed'))
                time.sleep(1)
        self.screen.cleanup()
        self.screen.draw('Done testing!')
        self.valve.cleanup()
        self.logger.update_setup_info({'status': 'ready'})
        time.sleep(2)
        self.screen.exit()

    def get_response(self, since=0):
        licked_probe, tmst = self.valve.get_last_lick()
        if tmst >= since and licked_probe:
            self.licked_probe = licked_probe
        else:
            self.licked_probe = 0
        return self.licked_probe > 0
