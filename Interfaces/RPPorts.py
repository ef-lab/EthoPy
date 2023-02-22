from time import sleep
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait
from threading import Event
from core.Interface import *
from Interfaces.Camera import PiCamera
import multiprocessing as mp

class RPPorts(Interface):
    channels = {'Odor': {1: 24, 2: 25},
                'Liquid': {1: 22, 2: 23},
                'Lick': {1: 17, 2: 27},
                'Proximity': {3: 9, 1: 5, 2: 6},
                'Sound': {1: 13},
                'Sync': {'in': 21},
                'Running': 20}

    def __init__(self, **kwargs):
        super(RPPorts, self).__init__(**kwargs)
        from RPi import GPIO
        import pigpio
        self.GPIO = GPIO
        self.GPIO.setmode(self.GPIO.BCM)
        self.Pulser = pigpio.pi()
        self.PulseGen = pigpio.pulse
        self.WaveProp=pigpio.WAVE_MODE_REPEAT_SYNC
        self.thread = ThreadPoolExecutor(max_workers=2)
        self.pwm_stop_event = Event()
        self.frequency = 20
        self.ts = False
        self.pulses = dict()
        self.sound_pulses=[]
        self.wave_thread=[]

        matched_ports = set(self.rew_ports) & set(self.channels['Liquid'].keys())
        assert matched_ports == set(self.rew_ports), 'All reward ports must have assigned a liquid delivery port!'
        if 'Lick' in self.channels:
            self.GPIO.setup(list(self.channels['Lick'].values()), self.GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            if self.callbacks:
                for channel in self.channels['Lick']:
                    self.GPIO.add_event_detect(self.channels['Lick'][channel], self.GPIO.RISING,
                                               callback=self._lick_port_activated, bouncetime=100)
        if 'Proximity' in self.channels:
            self.GPIO.setup(list(self.channels['Proximity'].values()), self.GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            if self.callbacks:
                for channel in self.channels['Proximity']:
                    self.GPIO.add_event_detect(self.channels['Proximity'][channel], self.GPIO.BOTH,
                                               callback=self._position_change, bouncetime=50)
        if 'Odor' in self.channels:
            self.GPIO.setup(list(self.channels['Odor'].values()), self.GPIO.OUT, initial=self.GPIO.LOW)
        if 'Liquid' in self.channels:
            for channel in self.channels['Liquid']:
                self.Pulser.set_mode(self.channels['Liquid'][channel], pigpio.OUTPUT)
        if 'Sound' in self.channels:
            for channel in self.channels['Sound']:
                self.Pulser.set_mode(self.channels['Sound'][channel], pigpio.OUTPUT)
        if 'Running' in self.channels:
            self.GPIO.setup(self.channels['Running'], self.GPIO.OUT, initial=self.GPIO.LOW)

        if self.exp.sync:
            source_path = '/home/eflab/Sync/'
            target_path = '/mnt/lab/data/Sync/'
            self.GPIO.setup(self.channels['sync']['in'], self.GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            self.GPIO.add_event_detect(self.channels['sync']['in'], self.GPIO.BOTH,
                                       callback=self._sync_in, bouncetime=20)
            filename, self.dataset = self.logger.createDataset(source_path, target_path, dataset_name='sync_data',
                                          dataset_type=np.dtype([("sync_times", np.double)]))
            self.exp.log_recording(dict(rec_aim='sync', software='PyMouse', version='0.1',
                                           filename=filename, source_path=source_path, target_path=target_path))

        if self.exp.params['setup_conf_idx'] in self.exp.logger.get(table='SetupConfiguration.Camera',fields=['setup_conf_idx']):            
            cameras_params= self.exp.logger.get(table='SetupConfiguration.Camera',
                    key=f"setup_conf_idx={self.exp.params['setup_conf_idx']}", 
                    as_dict=True)[0]
            key_animal_id_session = f"animal_id_{self.exp.logger.get_setup_info('animal_id')}_session_{self.exp.logger.get_setup_info('session')}"
            
            self.camera = PiCamera(path = None,
                                filename = f'{key_animal_id_session}',
                                video_format=cameras_params['file_format'],
                                fps=cameras_params['fps'],
                                shutter_speed=cameras_params['shutter_speed'],
                                resolution=(cameras_params['resolution_x'],cameras_params['resolution_y']),
                                logger_timer=self.logger.logger_timer)

            self.camera_Process = mp.Process(self.camera.start_rec())
            self.camera_Process.start()
            self.exp.log_recording(dict(rec_aim = cameras_params['video_aim'],software='PyMouse', version='0.1',
                                        filename=self.camera.filename, target_path=self.camera.path))

    def give_liquid(self, port, duration=False):
        if duration: self.duration=duration[port]
        if len(self.wave_thread): 
            wait(self.wave_thread)
        self.thread.submit(self._give_pulse, port)

    def give_odor(self, delivery_port, odor_id, odor_duration, dutycycle):
        for i, idx in enumerate(odor_id):
            self.thread.submit(self.__pwd_out, self.channels['Odor'][delivery_port[i]], odor_duration, dutycycle[i])

    def give_sound(self, sound_freq=40500, duration=500, volume=100, pulse_freq=0):
        self.wave_thread.append(self.thread.submit(self.__pwm_out, self.channels['Sound'][1], sound_freq, duration, volume, pulse_freq))

    def stop_sound(self):
        self.pwm_stop_event.set()

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
        self.GPIO.output(self.channels['Running'], running_state)

    def cleanup(self):
        self.set_running_state(False)
        self.Pulser.wave_clear()
        self.Pulser.stop()
        if self.callbacks:
            if 'Lick' in self.channels:
                 for channel in self.channels['Lick']:
                     self.GPIO.remove_event_detect(self.channels['Lick'][channel])
            if 'Proximity' in self.channels:
                 for channel in self.channels['Proximity']:
                     self.GPIO.remove_event_detect(self.channels['Proximity'][channel])
        self.GPIO.cleanup()
        if self.ts:
            self.ts.stop()

    def release(self):
        if self.interface.camera:
            if self.interface.camera.recording.is_set(): self.interface.camera.stop_rec()
            self.interface.camera_Process.join()

    def in_position(self, port=0):
        position = self.position
        port = self._get_position(port)
        if not position.port and not port: return 0, 0, 0
        if position != Port(type='Proximity', port=port):
            self._position_change(self.channels['Proximity'][max(port, position.port)])
        position_dur = self.timer_ready.elapsed_time() if self.position.port else self.position_dur
        return self.position, position_dur, self.position_tmst

    def off_proximity(self):
        return self.position.type != 'Proximity'

    def _get_position(self, ports=0):
        if not ports: ports = self.proximity_ports
        elif not type(ports) is list: ports = [ports]
        for port in ports:
            in_position = self.GPIO.input(self.channels['Proximity'][port])
            if self.ports[Port(type='Proximity', port=port) == self.ports][0].invert:
                in_position = not in_position
            if in_position: return port
        return 0

    def _position_change(self, channel=0):
        port = self._channel2port(channel, 'Proximity')
        in_position = self._get_position(port.port)
        if in_position: self.timer_ready.start()
        if in_position and not self.position.port:
            self.position_tmst = self.beh.log_activity({**port.__dict__, 'in_position': 1})
            self.position = port
        elif not in_position and self.position.port:
            tmst = self.beh.log_activity({**port.__dict__, 'in_position': 0})
            self.position_dur = tmst - self.position_tmst
            self.position = Port()

    def _give_pulse(self, port):
        self.Pulser.wave_add_generic([self.PulseGen(1 << self.channels['Liquid'][port], 0, int(self.duration[port]*1000)),
                                      self.PulseGen(0, 1 << self.channels['Liquid'][port], 1)])
        pulse = self.Pulser.wave_create()
        self.Pulser.wave_send_once(pulse)
        self.Pulser.wave_clear()

    def _lick_port_activated(self, channel):
        self.resp_tmst = self.logger.logger_timer.elapsed_time()
        self.response = self._channel2port(channel, 'Lick')
        self.beh.log_activity({**self.response.__dict__, 'time': self.resp_tmst})
        return self.response, self.resp_tmst

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
        sleep(duration/1000)    # to add a  delay in seconds
        pwm.stop()

    def __pwm_out(self, channel, freq, duration, dutycycle=100, pulse_freq=0):
        self.sound_pulses=[]
        self.pwm_stop_event.clear()
        time_stimulus = Timer()
        signal_duration=round(1/freq*1e6)   #microseconds
        # Speaker has non monotonic response with ~50%dutycycle is maximum response. Thus normalize percentage by /2.
        if pulse_freq==0:
            self.sound_pulses.append(self.PulseGen(1<<channel, 0, int(dutycycle*signal_duration/200))) 
            self.sound_pulses.append(self.PulseGen(0, 1<<channel, signal_duration-int(dutycycle*signal_duration/200)))
        else: 
            for i in range(int((1/(pulse_freq*2)*1e6)/signal_duration)):
                self.sound_pulses.append(self.PulseGen(1<<channel, 0, int(dutycycle*signal_duration/200)))
                self.sound_pulses.append(self.PulseGen(0, 1<<channel, signal_duration-int(dutycycle*signal_duration/200)))
            self.sound_pulses.append(self.PulseGen(0, 1<<channel, int((1/(pulse_freq*2)*1e6))))
        self.Pulser.wave_add_generic(self.sound_pulses)
        ff=self.Pulser.wave_create()
        self.Pulser.wave_send_using_mode(ff, self.WaveProp)
        while time_stimulus.elapsed_time()<duration and not self.pwm_stop_event.is_set():
            pass
        self.Pulser.wave_tx_stop()# stop waveform
        self.Pulser.write(channel,0)
        self.Pulser.wave_clear()# clear all waveforms
