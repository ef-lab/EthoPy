from DatabaseTables import *
from time import sleep
import numpy, socket
from utils.Timer import *
from concurrent.futures import ThreadPoolExecutor


class Probe:
    def __init__(self, logger):
        self.logger = logger
        self.probe1 = False
        self.probe2 = False
        self.ready = False
        self.timer_probe1 = Timer()
        self.timer_probe2 = Timer()
        self.timer_ready = Timer()
        self.__calc_pulse_dur(logger.reward_amount)
        self.thread = ThreadPoolExecutor(max_workers=2)

    def give_air(self, probe, duration, log=True):
        pass

    def give_liquid(self, probe, duration=False, log=True):
        pass

    def give_odor(self, odor_idx, duration, log=True):
        pass

    def lick(self):
        if self.probe1:
            self.probe1 = False
            probe = 1
            print('Probe 1 activated')
        elif self.probe2:
            self.probe2 = False
            probe = 2
            print('Probe 2 activated')
        else:
            probe = 0
        return probe

    def probe1_licked(self, channel):
        self.probe1 = True
        self.timer_probe1.start()
        self.logger.log_lick(1)
        #print('Probe 1 activated')

    def probe2_licked(self, channel):
        self.probe2 = True
        self.timer_probe2.start()
        self.logger.log_lick(2)
        #print('Probe 2 activated')

    def in_position(self):
        return True, 0

    def get_in_position(self):
        pass

    def get_off_position(self):
        pass

    def __calc_pulse_dur(self, reward_amount):  # calculate pulse duration for the desired reward amount
        self.liquid_dur = dict()
        probes = (LiquidCalibration() & dict(setup=self.logger.setup)).fetch('probe')
        for probe in list(set(probes)):
            key = dict(setup=self.logger.setup, probe=probe)
            dates = (LiquidCalibration() & key).fetch('date', order_by='date')
            key['date'] = dates[-1]  # use the most recent calibration
            pulse_dur, pulse_num, weight = (LiquidCalibration.PulseWeight() & key).fetch('pulse_dur',
                                                                                         'pulse_num',
                                                                                         'weight')
            self.liquid_dur[probe] = numpy.interp(reward_amount/1000,
                                                  numpy.divide(weight, pulse_num),
                                                  pulse_dur)

    def cleanup(self):
        pass


class RPProbe(Probe):
    def __init__(self, logger):
        super(RPProbe, self).__init__(logger)
        from RPi import GPIO
        self.setup = int(''.join(list(filter(str.isdigit, socket.gethostname()))))
        self.GPIO = GPIO
        self.GPIO.setmode(self.GPIO.BCM)
        self.GPIO.setup([17, 27, 9], self.GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        self.GPIO.setup([22, 23, 24, 25], self.GPIO.OUT, initial=self.GPIO.LOW)
        self.channels = {'air': {1: 24, 2: 25},
                         'liquid': {1: 22, 2: 23},
                         'lick': {1: 17, 2: 27},
                         'start': {1: 9}}  # 2
        self.frequency = 20
        self.GPIO.add_event_detect(self.channels['lick'][2], self.GPIO.RISING, callback=self.probe2_licked, bouncetime=200)
        self.GPIO.add_event_detect(self.channels['lick'][1], self.GPIO.RISING, callback=self.probe1_licked, bouncetime=200)
        self.GPIO.add_event_detect(self.channels['start'][1], self.GPIO.BOTH, callback=self.position_change, bouncetime=50)


    def give_liquid(self, probe, duration=False, log=True):
        if not duration:
            duration = self.liquid_dur[probe]
        self.thread.submit(self.__pulse_out, self.channels['liquid'][probe], duration)
        if log:
            self.logger.log_liquid(probe)

    def give_odor(self, delivery_idx, odor_idx, odor_duration, dutycycle, log=True):
        for i, idx in enumerate(odor_idx):
            self.thread.submit(self.__pwd_out, self.channels['air'][delivery_idx[i]], odor_duration, dutycycle[i])
        if log:
            self.logger.log_stim()

    def position_change(self, channel=0):
        if self.GPIO.input(self.channels['start'][1]):
            self.timer_ready.start()
            if not self.ready:
                self.logger.log_position(self.ready, 'Probe status')
                self.ready = True
                print('in position')
        else:
            if self.ready:
                self.logger.log_position(self.ready, 'Probe status')
                print('off position')
                self.ready = False

    def in_position(self):
        # handle missed events
        ready = self.GPIO.input(self.channels['start'][1])
        if self.ready != ready:
            self.position_change()
        if not self.ready:
            ready_time = 0
        else:
            ready_time = self.timer_ready.elapsed_time()
        return self.ready, ready_time

    def __pwd_out(self, channel, duration, dutycycle):
        pwm = self.GPIO.PWM(channel, self.frequency)
        pwm.ChangeFrequency(self.frequency)
        pwm.start(dutycycle)
        sleep(duration/1000)    # to add a  delay in seconds
        pwm.stop()

    def __pulse_out(self, channel, duration):
        self.GPIO.output(channel, self.GPIO.HIGH)
        sleep(duration/1000)
        self.GPIO.output(channel, self.GPIO.LOW)

    def cleanup(self):
        self.GPIO.remove_event_detect(self.channels['lick'][1])
        self.GPIO.remove_event_detect(self.channels['lick'][2])
        self.GPIO.remove_event_detect(self.channels['start'][1])
        self.GPIO.cleanup()
