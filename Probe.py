from DatabaseTables import *
from time import sleep
import numpy, socket
from utils.Timer import *
from concurrent.futures import ThreadPoolExecutor


class Probe:
    def __init__(self, logger):
        self.logger = logger
        self.probe = 0
        self.lick_tmst = 0
        self.ready_tmst = 0
        self.ready_dur =0
        self.ready = False
        self.timer_probe1 = Timer()
        self.timer_probe2 = Timer()
        self.timer_ready = Timer()
        self.thread = ThreadPoolExecutor(max_workers=2)
        self.probes = (LiquidCalibration() & dict(setup=self.logger.setup)).fetch('probe')
        self.weight_per_pulse = dict()
        self.pulse_dur = dict()
        for probe in list(set(self.probes)):
            key = dict(setup=self.logger.setup, probe=probe)
            dates = (LiquidCalibration() & key).fetch('date', order_by='date')
            key['date'] = dates[-1]  # use the most recent calibration
            self.pulse_dur[probe], pulse_num, weight = \
                (LiquidCalibration.PulseWeight() & key).fetch('pulse_dur', 'pulse_num', 'weight')
            self.weight_per_pulse[probe] = numpy.divide(weight, pulse_num)

    def give_air(self, probe, duration, log=True):
        pass

    def give_liquid(self, probe, duration=False, log=True):
        pass

    def give_odor(self, odor_idx, duration, log=True):
        pass

    def get_last_lick(self):
        probe = self.probe
        self.probe = 0
        return probe, self.lick_tmst

    def probe1_licked(self, channel):
        self.lick_tmst = self.logger.log_lick(1)
        self.timer_probe1.start()
        self.probe = 1

    def probe2_licked(self, channel):
        self.lick_tmst = self.logger.log_lick(2)
        self.timer_probe2.start()
        self.probe = 2

    def in_position(self):
        return True, 0

    def get_in_position(self):
        pass

    def get_off_position(self):
        pass

    def create_pulse(self, probe, duration):
        pass

    def calc_pulse_dur(self, reward_amount):  # calculate pulse duration for the desired reward amount
        actual_rew = dict()
        for probe in list(set(self.probes)):
            duration = numpy.interp(reward_amount/1000,
                                                  self.weight_per_pulse[probe], self.pulse_dur[probe])
            self.create_pulse(probe, duration)
            actual_rew[probe] = numpy.max((numpy.min(self.weight_per_pulse[probe]), reward_amount/1000)) * 1000 # in uL
        return actual_rew

    def cleanup(self):
        pass


class RPProbe(Probe):
    def __init__(self, logger):
        super(RPProbe, self).__init__(logger)
        from RPi import GPIO
        import pigpio
        self.setup = int(''.join(list(filter(str.isdigit, socket.gethostname()))))
        self.GPIO = GPIO
        self.GPIO.setmode(self.GPIO.BCM)
        self.channels = {'air': {1: 24, 2: 25},
                         'liquid': {1: 22, 2: 23},
                         'lick': {1: 17, 2: 27},
                         'start': {1: 9}}  # 2
        self.frequency = 20
        self.GPIO.setup(list(self.channels['lick'].values()) + [self.channels['start'][1]],
                        self.GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        self.GPIO.setup(list(self.channels['air'].values()), self.GPIO.OUT, initial=self.GPIO.LOW)
        self.GPIO.add_event_detect(self.channels['lick'][2], self.GPIO.RISING, callback=self.probe2_licked, bouncetime=100)
        self.GPIO.add_event_detect(self.channels['lick'][1], self.GPIO.RISING, callback=self.probe1_licked, bouncetime=100)
        self.GPIO.add_event_detect(self.channels['start'][1], self.GPIO.BOTH, callback=self.position_change, bouncetime=50)
        self.Pulser = pigpio.pi()
        self.PulseGen = pigpio.pulse
        self.Pulser.set_mode(self.channels['liquid'][1], pigpio.OUTPUT)
        self.Pulser.set_mode(self.channels['liquid'][2], pigpio.OUTPUT)
        self.pulses = dict()

    def give_liquid(self, probe):
        self.thread.submit(self.pulse_out, probe)

    def give_odor(self, delivery_port, odor_id, odor_duration, dutycycle):
        for i, idx in enumerate(odor_id):
            self.thread.submit(self.__pwd_out, self.channels['air'][delivery_port[i]], odor_duration, dutycycle[i])

    def position_change(self, channel=0):
        if self.getStart():
            self.timer_ready.start()
            if not self.ready:
                self.ready = True
                self.ready_tmst = self.logger.log_position(self.ready, 'Probe status')
                print('in position')
        else:
            if self.ready:
                self.ready = False
                tmst = self.logger.log_position(self.ready, 'Probe status')
                self.ready_dur = tmst - self.ready_tmst
                print('off position')

    def in_position(self):
        # handle missed events
        ready = self.getStart()
        if self.ready != ready:
            self.position_change()
        if not self.ready:
            ready_dur = self.ready_dur
        else:
            ready_dur = self.timer_ready.elapsed_time()
        return self.ready, ready_dur, self.ready_tmst

    def __pwd_out(self, channel, duration, dutycycle):
        pwm = self.GPIO.PWM(channel, self.frequency)
        pwm.ChangeFrequency(self.frequency)
        pwm.start(dutycycle)
        sleep(duration/1000)    # to add a  delay in seconds
        pwm.stop()

    def create_pulse(self, probe, duration):
        if probe in self.pulses:
            self.Pulser.wave_delete(self.pulses[probe])
        pulse = []
        pulse.append(self.PulseGen(1 << self.channels['liquid'][probe], 0, int(duration*1000)))
        pulse.append(self.PulseGen(0, 1 << self.channels['liquid'][probe], int(duration)))
        self.Pulser.wave_add_generic(pulse)  # 500 ms flashes
        self.pulses[probe] = self.Pulser.wave_create()

    def pulse_out(self, probe):
        self.Pulser.wave_send_once(self.pulses[probe])

    def cleanup(self):
        self.GPIO.remove_event_detect(self.channels['lick'][1])
        self.GPIO.remove_event_detect(self.channels['lick'][2])
        self.GPIO.remove_event_detect(self.channels['start'][1])
        self.GPIO.cleanup()
        self.Pulser.wave_clear()

    def getStart(self):
        return not self.GPIO.input(self.channels['start'][1])
