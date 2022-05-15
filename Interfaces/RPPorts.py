from time import sleep
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from core.Interface import *


class RPPorts(Interface):
    channels = {'odor': {1: 24, 2: 25},
                'liquid': {1: 22, 2: 23},
                'lick': {1: 17, 2: 27},
                'proximity': {1: 9},
                'sound': {1: 19},
                'sync': {'in': 21},
                'running': 20}

    def __init__(self, **kwargs):
        super(RPPorts, self).__init__(**kwargs)
        from RPi import GPIO
        import pigpio
        self.GPIO = GPIO
        self.GPIO.setmode(self.GPIO.BCM)
        self.Pulser = pigpio.pi()
        self.PulseGen = pigpio.pulse
        self.thread = ThreadPoolExecutor(max_workers=2)
        self.frequency = 20
        self.ts = False
        self.pulses = dict()

        matched_ports = self.rew_ports & set(self.channels['liquid'].keys())
        assert(matched_ports == self.rew_ports, 'All reward ports must have assigned a liquid delivery port!')

        if 'lick' in self.channels:
            self.GPIO.setup(list(self.channels['lick'].values()), self.GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            if not self.callbacks: return
            for channel in self.channels['lick']:
                self.GPIO.add_event_detect(self.channels['lick'][channel], self.GPIO.RISING,
                                           callback=self._lick_port_activated, bouncetime=100)
        if 'proximity' in self.channels:
            self.GPIO.setup(list(self.channels['proximity'].values()), self.GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            if not self.callbacks: return
            for channel in self.channels['proximity']:
                self.GPIO.add_event_detect(self.channels['proximity'][channel], self.GPIO.BOTH,
                                           callback=self._position_change, bouncetime=50)
        if 'odor' in self.channels:
            self.GPIO.setup(list(self.channels['odor'].values()), self.GPIO.OUT, initial=self.GPIO.LOW)
        if 'liquid' in self.channels:
            for channel in self.channels['liquid']:
                self.Pulser.set_mode(self.channels['liquid'][channel], pigpio.OUTPUT)
        if 'sound' in self.channels:
            for channel in self.channels['sound']:
                self.Pulser.set_mode(self.channels['sound'][channel], pigpio.OUTPUT)
        if 'running' in self.channels:
            self.GPIO.setup(self.channels['running'], self.GPIO.OUT, initial=self.GPIO.LOW)

        if self.exp.sync:
            from utils.Writer import Writer
            self.Writer = Writer
            source_path = '/home/eflab/Sync/'
            target_path = '/mnt/lab/data/Sync/'
            self.GPIO.setup(self.channels['sync']['in'], self.GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            self.GPIO.add_event_detect(self.channels['sync']['in'], self.GPIO.BOTH,
                                       callback=self._sync_in, bouncetime=20)
            filename, self.dataset = self.logger.createDataset(source_path, target_path, dataset_name='sync_data',
                                          dataset_type=np.dtype([("sync_times", np.double)]))
            self.exp.log_recording(dict(rec_aim='sync', software='PyMouse', version='0.1',
                                           filename=filename, source_path=source_path, target_path=target_path))

    def give_liquid(self, port, duration=False):
        if duration: self._create_pulse(port, duration)
        self.thread.submit(self._give_pulse, port)

    def give_odor(self, delivery_port, odor_id, odor_duration, dutycycle):
        for i, idx in enumerate(odor_id):
            self.thread.submit(self.__pwd_out, self.channels['odor'][delivery_port[i]], odor_duration, dutycycle[i])

    def give_sound(self, sound_freq=40500, duration=500, volume=100):
        self.thread.submit(self.__pwm_out, self.channels['sound'][1], sound_freq, duration, volume)

    def setup_touch_exit(self):
        try:
            import ft5406 as TS
            self.ts = TS.Touchscreen()
            self.ts_press_event = TS.TS_PRESS
            for touch in self.ts.touches:
                touch.on_press = self._touch_handler
                touch.on_release = self._touch_handler
            self.ts.run()
        except:
            self.ts = False
            print('Cannot create a touch exit!')

    def set_running_state(self, running_state):
        self.GPIO.output(self.channels['running'], running_state)

    def cleanup(self):
        self.set_running_state(False)
        self.logging = False
        self.Pulser.wave_clear()
        self.Pulser.stop()
        if self.callbacks:
            if 'lick' in self.channels:
                 for channel in self.channels['lick']:
                     self.GPIO.remove_event_detect(self.channels['lick'][channel])
            if 'proximity' in self.channels:
                 for channel in self.channels['proximity']:
                     self.GPIO.remove_event_detect(self.channels['proximity'][channel])
        self.GPIO.cleanup()
        if self.ts:
            self.ts.stop()

    def in_position(self, port):
        port = Port(type='proximity', port=self._get_position(port))  # handle missed events
        if self.position != port: self._position_change(self.channels['proximity'][port.port])
        position_dur = self.timer_ready.elapsed_time() if self.position else self.position_dur
        return self.position, position_dur, self.position_tmst

    def _get_position(self, ports=0):
        if not ports: ports = self.channels['proximity']
        else: ports = [ports.port]
        for port in ports:
            in_position = self.GPIO.input(self.channels['proximity'][port])
            if self.ports[Port(type='Proximity', port=port) == self.ports][0].invert:
                in_position = not in_position
            if in_position: return port
        return 0

    def _position_change(self, channel=0):
        port = self._get_position(self._channel2port(channel, 'Proximity'))
        if port: self.timer_ready.start()
        if port and not self.position:
            self.position_tmst = self.beh.log_activity({**port.__dict__, 'in_position': 1})
            print('in position ', port)
        elif not port and self.position:
            tmst = self.beh.log_activity({**port.__dict__, 'in_position': 0})
            self.position_dur = tmst - self.position_tmst
            print('off position ', port)
        self.position = port

    def _create_pulse(self, port, duration):
        if port in self.pulses:
            self.Pulser.wave_delete(self.pulses[port])
        self.Pulser.wave_add_generic([self.PulseGen(1 << self.channels['liquid'][port], 0, int(duration*1000)),
                                      self.PulseGen(0, 1 << self.channels['liquid'][port], 1)])
        self.pulses[port] = self.Pulser.wave_create()

    def _give_pulse(self, port):
        self.Pulser.wave_send_once(self.pulses[port])

    def _lick_port_activated(self, channel):
        self.resp_tmst = self.beh.log_activity({**self._channel2port(channel, 'Lick').__dict__})
        return self.resp_tmst

    def _sync_in(self, channel):
        self.dataset.append('sync_data', [self.logger.logger_timer.elapsed_time()])

    def _touch_handler(self, event, touch):
        if event == self.ts_press_event:
            if touch.x > 700 and touch.y < 50:
                print('Exiting')
                self.logger.update_setup_info({'status': 'stop'})

    def __pwd_out(self, channel, duration, dutycycle):
        pwm = self.GPIO.PWM(channel, self.frequency)
        pwm.ChangeFrequency(self.frequency)
        pwm.start(dutycycle)
        self.pi.hardware_clock(channel, 40500)
        sleep(duration/1000)    # to add a  delay in seconds
        self.pi.hardware_clock(channel, 0)
        pwm.stop()

    def __pwm_out(self, channel, freq, duration, dutycycle=50):
        self.Pulser.hardware_PWM(channel, freq, dutycycle*5000)
        sleep(duration/1000)    # to add a  delay in seconds
        self.Pulser.hardware_PWM(channel, 0, 0)
