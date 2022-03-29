from time import sleep
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from core.Interface import *
from utils.helper_functions import reverse_lookup


class RPPorts(Interface):
    channels = {'odor': {1: 24, 2: 25},
                'liquid': {1: 22, 2: 23},
                'lick': {1: 17, 2: 27},
                'proximity': {1: 9},
                'sound': {1: 18},
                'sync': {'in': 21},
                'running': 20}

    def __init__(self, **kwargs):
        super(RPPorts, self).__init__(**kwargs)
        from RPi import GPIO
        import pigpio
        ports = self.logger.get(table='SetupConfiguration.Port', fields=['port'], key=self.exp.params)
        self.ports = list(set(ports) & set(self.channels['liquid'].keys()))

        self.GPIO = GPIO
        self.GPIO.setmode(self.GPIO.BCM)
        self.thread = ThreadPoolExecutor(max_workers=2)
        self.frequency = 20
        self.ts = False
        self.pulses = dict()
        if 'lick' in self.channels:
            self.GPIO.setup(list(self.channels['lick'].values()), self.GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        if 'proximity' in self.channels:
            self.GPIO.setup(list(self.channels['proximity'].values()), self.GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        if 'odor' in self.channels:
            self.GPIO.setup(list(self.channels['odor'].values()), self.GPIO.OUT, initial=self.GPIO.LOW)
        self.Pulser = pigpio.pi()
        self.PulseGen = pigpio.pulse
        if 'liquid' in self.channels:
            for channel in self.channels['liquid']:
                self.Pulser.set_mode(self.channels['liquid'][channel], pigpio.OUTPUT)
        if 'sound' in self.channels:
            for channel in self.channels['sound']:
                self.Pulser.set_mode(self.channels['sound'][channel], pigpio.OUTPUT)
        if self.callbacks:
            if 'lick' in self.channels:
                for channel in self.channels['lick']:
                    self.GPIO.add_event_detect(self.channels['lick'][channel], self.GPIO.RISING,
                                               callback=self._port_licked, bouncetime=100)
            if 'proximity' in self.channels:
                for channel in self.channels['proximity']:
                    self.GPIO.add_event_detect(self.channels['proximity'][channel], self.GPIO.BOTH,
                                               callback=self._position_change, bouncetime=50)
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
            filename = self.createDataset(source_path, target_path, dataset_name='sync_data',
                                          dataset_type=np.dtype([("sync_times", np.double)]))

            self.exp.log_recording(dict(rec_aim='sync', software='PyMouse', version='0.1',
                                           filename=filename, source_path=source_path,
                                           target_path=target_path))

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
            self.thread.submit(self.__pwd_out, self.channels['odor'][delivery_port[i]], odor_duration, dutycycle[i])

    def give_sound(self, sound_freq=40000, duration=500, dutycycle=50):
        self.thread.submit(self.__pwd_out, self.channels['sound'][1], sound_freq, duration, dutycycle)

    def in_position(self):
        ready = self._get_position() # handle missed events
        if self.ready != ready: self._position_change()
        ready_dur = self.timer_ready.elapsed_time() if self.ready else self.ready_dur
        return self.ready, ready_dur, self.ready_tmst

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
        if self.exp.sync:
            self.closeDatasets()

        if self.ts:
            self.ts.stop()

    def _create_pulse(self, port, duration):
        if port in self.pulses:
            self.Pulser.wave_delete(self.pulses[port])
        self.Pulser.wave_add_generic([self.PulseGen(1 << self.channels['liquid'][port], 0, int(duration*1000)),
                                      self.PulseGen(0, 1 << self.channels['liquid'][port], 1)])
        self.pulses[port] = self.Pulser.wave_create()

    def _give_pulse(self, port):
        self.Pulser.wave_send_once(self.pulses[port])

    def _port_licked(self, channel):
        self.port = reverse_lookup(self.channels['lick'], channel)
        self.lick_tmst = self.log_activity('Lick', dict(port=self.port))

    def _sync_in(self, channel):
        self.dataset.append('sync_data', [self.logger.logger_timer.elapsed_time()])

    def _position_change(self, channel=0):
        port = reverse_lookup(self.channels['proximity'], channel) if channel else 0
        position = self._get_position()
        if position: self.timer_ready.start()
        if position and not self.ready:
            self.ready = True
            self.ready_tmst = self.log_activity('Proximity', dict(port=port, in_position=self.ready))
            print('in position')
        elif not position and self.ready:
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