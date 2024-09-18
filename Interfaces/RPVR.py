from Interfaces.RPPorts import *


class RPVR(RPPorts):
    channels = {'Odor': {1: 19, 2: 16, 3: 6, 4: 12},
                'Liquid': {1: 22},
                'Lick': {1: 17},
                'Sync': {'in': 21},
                'Status': 20,
                'Sound': {1: 13}}
    pwm = dict()

    def start_odor(self, channels, dutycycle=50, frequency=20):
        self.frequency = frequency
        self.odor_channels = channels
        for channel in channels:
            self.pwm[channel] = self.GPIO.PWM(self.channels['Odor'][channel], self.frequency)
            self.pwm[channel].ChangeFrequency(self.frequency)
            self.pwm[channel].start(dutycycle)

    def update_odor(self, dutycycles):  # for 2D olfactory setup
        for channel, dutycycle in zip(self.odor_channels, dutycycles):
            self.pwm[channel].ChangeDutyCycle(dutycycle)

    def stop_odor(self):
        for channel in self.odor_channels:
            self.pwm[channel].stop()

    def _lick_port_activated(self, channel):
        port, tmst = super()._lick_port_activated(channel)
        pos = self.exp.beh.get_position()
        self.beh.log_activity(dict(type='Position', loc_x=pos[0], loc_y=pos[1], theta=pos[2], time=tmst))

    def cleanup(self):
        for channel in self.odor_channels:
            self.pwm[channel].stop()
        super().cleanup()
