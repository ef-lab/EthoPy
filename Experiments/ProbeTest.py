import numpy
from core.Interface import *
from utils.TouchInterface import TouchInterface


class ProbeTest:
    def __init__(self, logger, params):
        self.params = params
        self.logger = logger
        self.size = (800, 480)     # window size
        self.screen = TouchInterface()
        self.result = dict()
        self.total_pulses=0

    def run(self):
        """ Lickspout liquid delivery test """
        self.valve = RPProbe(self.logger, callbacks=True, logging=False)
        print('Running probe test')
        for probe in self.params['probes']:
            self.total_pulses = 0
            self.result[probe] = False
            tmst = self.logger.logger_timer.elapsed_time()
            for cal_idx in range(0, numpy.size(self.params['pulsenum'])):
                self.screen.cleanup()
                pulse = 0
                while pulse < self.params['pulsenum'][cal_idx] and not self.result[probe]:
                    self.screen.cleanup()
                    msg = 'Pulse %d/%d' % (pulse + 1, self.params['pulsenum'][cal_idx])
                    self.screen.draw(msg)
                    print(msg)
                    self.valve.give_liquid(probe, self.params['duration'][cal_idx])
                    time.sleep(self.params['duration'][cal_idx] / 1000 + self.params['pulse_interval'][cal_idx] / 1000)
                    pulse += 1  # update trial
                    self.total_pulses += 1
                    self.result[probe] = self.get_response(tmst, probe)
                if self.result[probe]:
                    self.log_test(probe, self.total_pulses, 'Passed')
                    break
            if not self.result[probe]:
                self.log_test(probe, self.total_pulses, 'Failed')
        self.screen.cleanup()
        self.screen.draw('Done testing!')
        self.valve.cleanup()
        self.logger.update_setup_info({'status': 'ready'})
        time.sleep(1)
        self.screen.exit()

    def get_response(self, since=0, probe=0):
        licked_probe, tmst = self.valve.get_last_lick()
        return tmst >= since and licked_probe == probe

    def log_test(self, probe=0, pulses=0, result='Passed'):
        self.screen.cleanup()
        self.screen.draw('Probe %d %s!' % (probe, result))
        key = dict(setup=self.logger.setup, probe=probe, result=result, pulses=pulses)
        self.logger.put(table='PortCalibration', tuple=key, schema='behavior', priority=5)
        self.logger.put(table='PortCalibration.Test',  schema='behavior', replace=True, tuple=key)

        time.sleep(1)