from time import sleep
import numpy as np
from utils.Timer import *
from utils.helper_functions import *
from concurrent.futures import ThreadPoolExecutor
import threading, multiprocessing, struct, time, socket


class Interface:
    port, lick_tmst, ready_dur, activity_tmst, ready_tmst, pulse_rew = 0, 0, 0, 0, 0, dict()
    ready, logging, timer_ready, weight_per_pulse, pulse_dur, channels = False, False, Timer(), dict(), dict(), dict()

    def __init__(self, exp=[], callbacks=True, logging=True):
        self.callbacks = callbacks
        self.logging = logging
        self.exp = exp
        self.logger = exp.logger
        self.ports = self.channels['liquid'].keys()

    def load_calibration(self):
        for port in list(set(self.ports)):
            self.pulse_rew[port] = dict()
            key = dict(setup=self.logger.setup, port=port)
            dates = self.logger.get(schema='behavior', table='PortCalibration', key=key, fields=['date'], order_by='date')
            if np.size(dates) < 1:
                print('No PortCalibration found!')
                self.exp.stop()
                break
            key['date'] = dates[-1]  # use the most recent calibration
            self.pulse_dur[port], pulse_num, weight = self.logger.get(schema='behavior', table='PortCalibration.Liquid',
                                                                 key=key, fields=['pulse_dur', 'pulse_num', 'weight'])
            self.weight_per_pulse[port] = np.divide(weight, pulse_num)

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

    def log_activity(self, table, key):
        self.activity_tmst = self.logger.logger_timer.elapsed_time()
        key.update({'time': self.activity_tmst, **self.logger.trial_key})
        if self.logging:
            self.logger.log('Activity', key, schema='behavior', priority=5)
            self.logger.log('Activity.' + table, key, schema='behavior')
        return self.activity_tmst

    def calc_pulse_dur(self, reward_amount):  # calculate pulse duration for the desired reward amount
        actual_rew = dict()
        for port in list(set(self.ports)):
            if reward_amount not in self.pulse_rew[port]:
                duration = np.interp(reward_amount/1000, self.weight_per_pulse[port], self.pulse_dur[port])
                self._create_pulse(port, duration)
                self.pulse_rew[port][reward_amount] = np.max((np.min(self.weight_per_pulse[port]),
                                                              reward_amount/1000)) * 1000 # in uL
            actual_rew[port] = self.pulse_rew[port][reward_amount]
        return actual_rew

    def cleanup(self):
        pass


class RPProbe(Interface):
    channels = {'air': {1: 24, 2: 25},
                'liquid': {1: 22, 2: 23},
                'lick': {1: 17, 2: 27},
                'proximity': {1: 9},
                'sound': {1: 18}}

    def __init__(self, **kwargs):
        super(RPProbe, self).__init__(**kwargs)
        from RPi import GPIO
        import pigpio
        self.GPIO = GPIO
        self.GPIO.setmode(self.GPIO.BCM)
        self.thread = ThreadPoolExecutor(max_workers=2)
        self.frequency = 20
        self.pulses = dict()
        self.GPIO.setup(list(self.channels['lick'].values()) + list(self.channels['proximity'].values()),
                        self.GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        self.GPIO.setup(list(self.channels['air'].values()), self.GPIO.OUT, initial=self.GPIO.LOW)
        self.Pulser = pigpio.pi()
        self.PulseGen = pigpio.pulse
        for channel in self.channels['liquid']:
            self.Pulser.set_mode(self.channels['liquid'][channel], pigpio.OUTPUT)
        for channel in self.channels['sound']:
            self.Pulser.set_mode(self.channels['sound'][channel], pigpio.OUTPUT)
        if self.callbacks:
            for channel in self.channels['lick']:
                self.GPIO.add_event_detect(self.channels['lick'][channel], self.GPIO.RISING,
                                           callback=self._port_licked, bouncetime=100)
            for channel in self.channels['proximity']:
                self.GPIO.add_event_detect(self.channels['proximity'][channel], self.GPIO.BOTH,
                                           callback=self._position_change, bouncetime=50)

    def setup_touch_exit(self):
        import ft5406 as TS
        self.ts = TS.Touchscreen()
        self.ts_press_event = TS.TS_PRESS
        for touch in self.ts.touches:
            touch.on_press = self._touch_handler
            touch.on_release = self._touch_handler
        self.ts.run()

    def _touch_handler(self, event, touch):
        if event == self.ts_press_event:
            if touch.x > 700 and touch.y < 50:
                print('Exiting')
                self.logger.update_setup_info({'status': 'stop'})

    def give_liquid(self, port, duration=False):
        if duration: self._create_pulse(port, duration)
        self.thread.submit(self._give_pulse, port)

    def give_odor(self, delivery_port, odor_id, odor_duration, dutycycle):
        for i, idx in enumerate(odor_id):
            self.thread.submit(self.__pwd_out, self.channels['air'][delivery_port[i]], odor_duration, dutycycle[i])

    def give_sound(self, sound_freq=40000, duration=500, dutycycle=50):
        self.thread.submit(self.__pwd_out, self.channels['air'][1], sound_freq, duration, dutycycle)

    def in_position(self):
        ready = self._get_position() # handle missed events
        if self.ready != ready: self._position_change()
        ready_dur = self.timer_ready.elapsed_time() if self.ready else self.ready_dur
        return self.ready, ready_dur, self.ready_tmst

    def cleanup(self):
        self.Pulser.wave_clear()
        if self.callbacks:
            for channel in self.channels['lick']:
                self.GPIO.remove_event_detect(self.channels['lick'][channel])
            for channel in self.channels['proximity']:
                self.GPIO.remove_event_detect(self.channels['proximity'][channel])
        self.GPIO.cleanup()

    def _create_pulse(self, port, duration):
        if port in self.pulses:
            self.Pulser.wave_delete(self.pulses[port])
        pulse = []
        pulse.append(self.PulseGen(1 << self.channels['liquid'][port], 0, int(duration*1000)))
        pulse.append(self.PulseGen(0, 1 << self.channels['liquid'][port], int(duration)))
        self.Pulser.wave_add_generic(pulse)  # 500 ms flashes
        self.pulses[port] = self.Pulser.wave_create()

    def _give_pulse(self, port):
        self.Pulser.wave_send_once(self.pulses[port])

    def _port_licked(self, channel):
        self.port = reverse_lookup(self.channels['lick'], channel)
        self.lick_tmst = self.log_activity('Lick', dict(port=self.port))

    def _position_change(self, channel=0):
        port = reverse_lookup(self.channels['proximity'], channel) if channel else 0
        position = self._get_position()
        if position: self.timer_ready.start()
        if position and not self.ready:
            self.ready = True
            self.ready_tmst = self.log_activity('Proximity', dict(port=port, in_position=self.ready))
            print('in position')
        elif position and self.ready:
            self.ready = False
            tmst = self.log_activity('Proximity', dict(port=port, in_position=self.ready))
            self.ready_dur = tmst - self.ready_tmst
            print('off position')

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

    def _get_position(self):
        return not self.GPIO.input(self.channels['proximity'][1])


class VRProbe(RPProbe):
    channels = {'odor': {1: 19, 2: 16, 3: 26, 4: 20},
                'liquid': {1: 22},
                'lick': {1: 17}}

    def start_odor(self, dutycycle=50):
        for idx, channel in enumerate(list(self.channels['odor'].values())):
            self.pwm[idx] = self.GPIO.PWM(channel, self.frequency)
            self.pwm[idx].ChangeFrequency(self.frequency)
            self.pwm[idx].start(dutycycle)

    def update_odor(self, dutycycles):  # for 2D olfactory setup
        for idx, dutycycle in enumerate(dutycycles):
            self.pwm[idx].ChangeDutyCycle(dutycycle)

    def stop_odor(self):
        for idx, channel in enumerate(list(self.channels['odor'].values())):
            self.pwm[idx].stop()

    def cleanup(self):
        for idx, channel in enumerate(list(self.channels['odor'].values())):
            self.pwm[idx].stop()
        super().cleanup()


class Ball(Interface):
    def __init__(self, logger, ball_radius=0.125, path="", target_path=False):
        from utils.Writer import Writer
        self.quit()
        self.logger = logger
        self.mouse1 = MouseReader("/dev/input/by-path/platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.1:1.0-mouse", logger)
        self.mouse2 = MouseReader("/dev/input/by-path/platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.2:1.0-mouse", logger)
        self.Writer = Writer
        self.speed = 0
        self.timestamp = 0
        self.setPosition()
        self.phi_z1 = 1  # angle of z axis (rotation)
        self.phi_z2 = self.phi_z1
        self.phi_y1 = np.pi - 0.13  # angle of y1 axis (mouse1) .6
        self.phi_y2 = self.phi_y1 + np.pi/2  # angle of y2 axis (mouse2)
        self.ball_radius = ball_radius
        self.createDataset(path, target_path)
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

            loc_x = min(self.loc_x + np.double(x), self.xmx)
            loc_y = min(self.loc_y + np.double(y), self.ymx)
            timestamp = max(tmst1, tmst2)
            self.speed = np.sqrt((loc_x - self.loc_x)**2 + (loc_y - self.loc_y)**2)/(timestamp - self.timestamp)
            self.loc_x = loc_x
            self.loc_y = loc_y
            self.timestamp = timestamp
            #print(self.loc_x, self.loc_y, self.theta/np.pi*180)
            self.append2Dataset()
            time.sleep(.1)

    def setPosition(self, xmx=1, ymx=1, x0=0, y0=0, theta0=0):
        self.loc_x = x0
        self.loc_y = y0
        self.theta = theta0
        self.xmx = xmx
        self.ymx = ymx

    def getPosition(self):
        return self.loc_x, self.loc_y, self.theta,  self.timestamp

    def getSpeed(self):
        return self.speed

    def createDataset(self, path='', target_path=False):
        self.filename = datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + ".h5"
        self.datapath = path + self.filename
        TIME_SERIES_DOUBLE = np.dtype([("loc_x", np.double),
                                       ("loc_y", np.double),
                                       ("theta", np.double),
                                       ("tmst", np.double)])

        self.dataset = self.Writer(datapath, target_path)
        self.dataset.createDataset('tracking_data', shape=(4,), dtype=TIME_SERIES_DOUBLE)

    def append2Dataset(self):
        self.dataset.append('tracking_data', [self.loc_x, self.loc_y, self.theta, self.timestamp])

    def closeDatasets(self):
        self.dataset.exit()

    def quit(self):
        try:
            self.thread_end.set()
            self.closeDatasets()
            self.mouse1.close()
            self.mouse2.close()
        except:
            print('ball not running')


class MouseReader:
    def __init__(self, path, logger, dpm=31200):
        self.logger = logger
        self.dpm = dpm
        self.queue = multiprocessing.Queue()
        self.file = open(path, "rb")
        self.thread_end = multiprocessing.Event()
        self.thread_runner = multiprocessing.Process(target=self.reader, args=(self.queue, self.dpm,))
        self.thread_runner.start()

    def reader(self, queue, dpm):
        while not self.thread_end.is_set():
            # print('Reading file')
            data = self.file.read(3)  # Reads the 3 bytes
            x, y = struct.unpack("2b", data[1:])
            queue.put({'x': x/dpm, 'y': y/dpm, 'timestamp': self.logger.session_timer.elapsed_time()})

    def close(self):
        self.thread_end.set()
        self.thread_runner.join()
