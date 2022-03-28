from core.Interface import *
from Interfaces.RPPorts import *

class RPVR(RPPorts):
    channels = {'odor': {1: 19, 2: 16, 3: 6, 4: 12},
                'liquid': {1: 22},
                'lick': {1: 17},
                'sync': {'in': 21},
                'running': 20}
    pwm = dict()

    def start_odor(self, channels, dutycycle=50, frequency=20):
        self.frequency = frequency
        self.odor_channels = channels
        for channel in channels:
            self.pwm[channel] = self.GPIO.PWM(self.channels['odor'][channel], self.frequency)
            self.pwm[channel].ChangeFrequency(self.frequency)
            self.pwm[channel].start(dutycycle)

    def update_odor(self, dutycycles):  # for 2D olfactory setup
        for channel, dutycycle in zip(self.odor_channels, dutycycles):
            self.pwm[channel].ChangeDutyCycle(dutycycle)

    def stop_odor(self):
        for channel in self.odor_channels:
            self.pwm[channel].stop()

    def cleanup(self):
        for channel in self.odor_channels:
            self.pwm[channel].stop()
        super().cleanup()
