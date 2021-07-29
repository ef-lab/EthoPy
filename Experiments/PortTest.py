import numpy
from core.Interface import *
from utils.TouchInterface import TouchInterface
import time as systime


class PortTest:
    def __init__(self, logger, params):
        self.params = params
        self.logger = logger
        self.size = (800, 480)     # window size
        self.screen = TouchInterface()
        self.result = dict()
        self.total_pulses=0

    def run(self):
        """ Lickspout liquid delivery test """
        self.valve = RPProbe(exp=self, callbacks=True, logging=False)
        print('Running port test')
        for port in self.params['ports']:
            self.total_pulses = 0
            self.result[port] = False
            tmst = self.logger.logger_timer.elapsed_time()
            for cal_idx in range(0, numpy.size(self.params['pulsenum'])):
                self.screen.cleanup()
                pulse = 0
                while pulse < self.params['pulsenum'][cal_idx] and not self.result[port]:
                    self.screen.cleanup()
                    msg = 'Pulse %d/%d' % (pulse + 1, self.params['pulsenum'][cal_idx])
                    self.screen.draw(msg)
                    print(msg)
                    self.valve.give_liquid(port, self.params['duration'][cal_idx])
                    time.sleep(self.params['duration'][cal_idx] / 1000 + self.params['pulse_interval'][cal_idx] / 1000)
                    pulse += 1  # update trial
                    self.total_pulses += 1
                    self.result[port] = self.get_response(tmst, port)
                if self.result[port]:
                    self.log_test(port, self.total_pulses, 'Passed')
                    break
            if not self.result[port]:
                self.log_test(port, self.total_pulses, 'Failed')
        self.screen.cleanup()
        self.screen.draw('Done testing!')
        self.valve.cleanup()
        self.logger.update_setup_info({'status': 'ready'})
        time.sleep(1)
        self.screen.exit()

    def get_response(self, since=0, port=0):
        licked_port, tmst = self.valve.get_last_lick()
        return tmst >= since and licked_port == port

    def log_test(self, port=0, pulses=0, result='Passed'):
        self.screen.cleanup()
        self.screen.draw('Probe %d %s!' % (port, result))
        key = dict(setup=self.logger.setup, port=port, result=result, pulses=pulses, date=systime.strftime("%Y-%m-%d"),
                   timestamp=systime.strftime("%Y-%m-%d %H:%M:%S"))
        self.logger.put(table='PortCalibration', tuple=key, schema='behavior', priority=5)
        self.logger.put(table='PortCalibration.Test',  schema='behavior', replace=True, tuple=key)
        time.sleep(1)