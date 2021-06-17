from time import sleep
import numpy as np
from utils.Timer import *
from utils.helper_functions import *
from concurrent.futures import ThreadPoolExecutor
import threading, multiprocessing, struct, time, socket


class Interface:
    def __init__(self, logger):
        self.logger = logger
        self.port = 0
        self.lick_tmst = 0
        self.ready_tmst = 0
        self.ready_dur = 0
        self.ready = False
        self.logging = False
        self.timer_ready = Timer()
        self.weight_per_pulse = dict()
        self.pulse_dur = dict()

    def give_air(self, port, duration, log=True):
        pass

    def give_liquid(self, port, duration=False, log=True):
        pass

    def give_odor(self, odor_idx, duration, log=True):
        pass

    def give_sound(self, sound_freq, duration, dutycycle):
        pass

    def get_last_lick(self):
        port = self.port
        self.port = 0
        return port, self.lick_tmst

    def in_position(self):
        return True, 0

    def create_pulse(self, port, duration):
        pass

    def calc_pulse_dur(self, reward_amount):  # calculate pulse duration for the desired reward amount
        actual_rew = dict()
        for port in list(set(self.ports)):
            duration = np.interp(reward_amount/1000, self.weight_per_pulse[port], self.pulse_dur[port])
            self.create_pulse(port, duration)
            actual_rew[port] = np.max((np.min(self.weight_per_pulse[port]), reward_amount/1000)) * 1000 # in uL
        return actual_rew

    def cleanup(self):
        pass


class RPProbe(Interface):
    def __init__(self, logger, callbacks=True, logging=True):
        super(RPProbe, self).__init__(logger)
        from RPi import GPIO
        import pigpio
        self.setup_name = int(''.join(list(filter(str.isdigit, socket.gethostname()))))
        self.GPIO = GPIO
        self.logging = logging
        self.GPIO.setmode(self.GPIO.BCM)
        self.channels = {'air': {1: 24, 2: 25},
                         'liquid': {1: 22, 2: 23},
                         'lick': {1: 17, 2: 27},
                         'proximity': {1: 9},
                         'sound': {1: 18}}
        self.thread = ThreadPoolExecutor(max_workers=2)
        self.ports = self.channels['liquid'].keys()
        for port in list(set(self.ports)):
            key = dict(setup=self.logger.setup, port=port)
            dates = logger.get(schema='behavior', table='PortCalibration', key=key, fields=['date'], order_by='date')
            if not dates: break
            key['date'] = dates[-1]  # use the most recent calibration
            self.pulse_dur[port], pulse_num, weight = \
                logger.get(schema='behavior', table='PortCalibration.Liquid', key=key, fields=['pulse_dur', 'pulse_num', 'weight'])
            self.weight_per_pulse[port] = np.divide(weight, pulse_num)

        self.callbacks = callbacks
        self.frequency = 20
        self.pulses = dict()
        self.GPIO.setup(list(self.channels['lick'].values()) + [self.channels['proximity'][1]],
                        self.GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        self.GPIO.setup(list(self.channels['air'].values()), self.GPIO.OUT, initial=self.GPIO.LOW)
        self.Pulser = pigpio.pi()
        self.PulseGen = pigpio.pulse
        self.Pulser.set_mode(self.channels['liquid'][1], pigpio.OUTPUT)
        self.Pulser.set_mode(self.channels['liquid'][2], pigpio.OUTPUT)
        self.Pulser.set_mode(self.channels['sound'][1], pigpio.OUTPUT)
        if callbacks:
            self.GPIO.add_event_detect(self.channels['lick'][2], self.GPIO.RISING,
                                       callback=self.port_licked, bouncetime=100)
            self.GPIO.add_event_detect(self.channels['lick'][1], self.GPIO.RISING,
                                       callback=self.port_licked, bouncetime=100)
            self.GPIO.add_event_detect(self.channels['proximity'][1], self.GPIO.BOTH,
                                       callback=self.position_change, bouncetime=50)

    def give_liquid(self, port):
        self.thread.submit(self.pulse_out, port)

    def give_odor(self, delivery_port, odor_id, odor_duration, dutycycle):
        for i, idx in enumerate(odor_id):
            self.thread.submit(self.__pwd_out, self.channels['air'][delivery_port[i]], odor_duration, dutycycle[i])

    def give_sound(self, sound_freq=40000, duration=500, dutycycle=50):
        self.thread.submit(self.__pwd_out, self.channels['air'][1], sound_freq, duration, dutycycle)

    def port_licked(self, channel):
        self.port = reverse_lookup(self.channels['lick'], channel)
        self.lick_tmst = self.logger.log('Response.Lick', dict(port=self.port), schema='behavior') \
            if self.logging else self.logger.logger_timer.elapsed_time()

    def position_change(self, channel=0):
        port = 3
        if self.getStart():
            self.timer_ready.start()
            if not self.ready:
                self.ready = True
                self.ready_tmst = self.logger.log('Response.Proximity', dict(port=port, in_position=self.ready),
                                                  schema='behavior')
                print('in position')
        else:
            if self.ready:
                self.ready = False
                tmst = self.logger.log('Response.Proximity', dict(port=port, in_position=self.ready), schema='behavior')
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

    def __pwm_out(self, channel, freq, duration, dutycycle=50):
        self.Pulser.hardware_PWM(channel, freq, dutycycle*10000)
        sleep(duration/1000)    # to add a  delay in seconds
        self.Pulser.hardware_PWM(channel, 0, 0)

    def create_pulse(self, port, duration):
        if port in self.pulses:
            self.Pulser.wave_delete(self.pulses[port])
        pulse = []
        pulse.append(self.PulseGen(1 << self.channels['liquid'][port], 0, int(duration*1000)))
        pulse.append(self.PulseGen(0, 1 << self.channels['liquid'][port], int(duration)))
        self.Pulser.wave_add_generic(pulse)  # 500 ms flashes
        self.pulses[port] = self.Pulser.wave_create()

    def pulse_out(self, port):
        self.Pulser.wave_send_once(self.pulses[port])

    def getStart(self):
        return not self.GPIO.input(self.channels['proximity'][1])

    def cleanup(self):
        self.Pulser.wave_clear()
        if self.callbacks:
            self.GPIO.remove_event_detect(self.channels['lick'][1])
            self.GPIO.remove_event_detect(self.channels['lick'][2])
            self.GPIO.remove_event_detect(self.channels['proximity'][1])
        self.GPIO.cleanup()


class VRProbe(Interface):
    def __init__(self, logger):
        super(VRProbe, self).__init__(logger)
        from RPi import GPIO
        import pigpio
        self.setup = int(''.join(list(filter(str.isdigit, socket.gethostname()))))
        self.GPIO = GPIO
        self.GPIO.setmode(self.GPIO.BCM)
        self.channels = {'odor': {1: 6, 2: 13, 3: 19, 4: 26},
                         'liquid': {1: 22},
                         'lick': {1: 17}}
        self.thread = ThreadPoolExecutor(max_workers=2)
        self.frequency = 10
        self.GPIO.setup(list(self.channels['lick'].values()) + [self.channels['proximity'][1]],
                        self.GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        self.GPIO.setup(list(self.channels['odor'].values()), self.GPIO.OUT, initial=self.GPIO.LOW)
        self.GPIO.add_event_detect(self.channels['lick'][1], self.GPIO.RISING, callback=self.port1_licked, bouncetime=100)
        self.Pulser = pigpio.pi()
        self.PulseGen = pigpio.pulse
        self.Pulser.set_mode(self.channels['liquid'][1], pigpio.OUTPUT)
        self.pulses = dict()

    def give_liquid(self, port):
        self.thread.submit(self.pulse_out, port)

    def start_odor(self, dutycycle=50):
        for idx, channel in enumerate(self.channels['odor']):
            self.pwm[idx] = self.GPIO.PWM(channel, self.frequency)
            self.pwm[idx].ChangeFrequency(self.frequency)
            self.pwm[idx].start(dutycycle)

    def update_odor(self, dutycycles):  # for 2D olfactory setup
        for idx, dutycycle in enumerate(dutycycles):
            self.pwm[idx].ChangeDutyCycle(dutycycle)

    def create_pulse(self, port, duration):
        if port in self.pulses:  self.Pulser.wave_delete(self.pulses[port])
        pulse = [self.PulseGen(1 << self.channels['liquid'][port], 0, int(duration*1000)),
                 self.PulseGen(0, 1 << self.channels['liquid'][port], int(duration))]
        self.Pulser.wave_add_generic(pulse)  # 500 ms flashes
        self.pulses[port] = self.Pulser.wave_create()

    def pulse_out(self, port):
        self.Pulser.wave_send_once(self.pulses[port])

    def cleanup(self):
        self.pwm[self.channels['air']].stop()
        self.GPIO.remove_event_detect(self.channels['lick'][1])
        self.GPIO.remove_event_detect(self.channels['proximity'][1])
        self.GPIO.cleanup()
        self.Pulser.wave_clear()


class Ball(Interface):
    def __init__(self, xmx=1, ymx=1, x0=0, y0=0, theta0=0, ball_radius=0.125):
        self.mouse1 = MouseReader("/dev/input/by-path/platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.3:1.0-mouse")
        self.mouse2 = MouseReader("/dev/input/by-path/platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.4:1.0-mouse")
        self.loc_x = x0
        self.loc_y = y0
        self.theta = theta0
        self.xmx = xmx
        self.ymx = ymx
        self.timestamp = 0
        self.phi_z1 = 1  # angle of z axis (rotation)
        self.phi_z2 = self.phi_z1
        self.phi_y1 = np.pi - 0.13  # angle of y1 axis (mouse1) .6
        self.phi_y2 = self.phi_y1 + np.pi/2  # angle of y2 axis (mouse2)
        self.ball_radius = ball_radius
        self.thread_end = threading.Event()
        self.thread_runner = threading.Thread(target=self.readMouse)
        self.thread_runner.start()

    def readMouse(self):
        while not self.thread_end.is_set():
            x1, y1, x2, y2, tmst1, tmst2 = 0, 0, 0, 0, time.time(), time.time()
            while not self.mouse1.queue.empty():
                data1 = self.mouse1.queue.get()
                x1 += data1['x']; y1 += data1['y']; tmst1 = data1['timestamp']

            while not self.mouse2.queue.empty():
                data2 = self.mouse2.queue.get()
                x2 += data2['x']; y2 += data2['y']; tmst2 = data2['timestamp']

            theta_contamination1 = y2*(np.sin(self.phi_z1)**2)
            theta_contamination2 = -y1*(np.sin(self.phi_z2)**2)

            theta_step1 = (x1 - theta_contamination1)/(np.sin(self.phi_z1)**2)/self.ball_radius
            theta_step2 = (x2 - theta_contamination2)/(np.sin(self.phi_z2)**2)/self.ball_radius

            xm = y2 * np.cos(self.phi_y1) - y1 * np.sin(self.phi_y1)
            ym = y2 * np.sin(self.phi_y1) + y1 * np.cos(self.phi_y1)

            self.theta += (theta_step2 + theta_step1)/2
            self.theta = np.mod(self.theta, 2*np.pi)

            x = -xm*np.sin(self.theta) - ym*np.cos(self.theta)
            y = -xm*np.cos(self.theta) + ym*np.sin(self.theta)

            self.loc_x = min(self.loc_x + np.double(x), self.xmx)
            self.loc_y = min(self.loc_y + np.double(y), self.ymx)
            self.timestamp = max(tmst1, tmst2)
            time.sleep(.1)

    def getPosition(self):
        return self.loc_x, self.loc_y, self.theta,  self.timestamp

    def quit(self):
        self.thread_end.set()
        self.mouse1.close()
        self.mouse2.close()


class MouseReader:
    def __init__(self, path, dpm=31200):
        self.dpm = dpm
        self.queue = multiprocessing.Queue()
        self.file = open(path, "rb")
        self.thread_end = multiprocessing.Event()
        self.thread_runner = multiprocessing.Process(target=self.reader, args=(self.queue, self.dpm,))
        self.thread_runner.start()

    def reader(self, queue, dpm):
        while not self.thread_end.is_set():
            data = self.file.read(3)  # Reads the 3 bytes
            x, y = struct.unpack("2b", data[1:])
            queue.put({'x': x/dpm, 'y': y/dpm, 'timestamp': time.time()})

    def close(self):
        self.thread_end.set()
        self.thread_runner.join()
