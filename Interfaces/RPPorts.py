from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import sleep

import numpy as np

from core.Interface import *


class RPPorts(Interface):
    channels = {'Odor': {1: 24, 2: 25},
                'Liquid': {1: 22, 2: 23},
                'Lick': {1: 17, 2: 27},
                'Proximity': {3: 9, 1: 5, 2: 6},
                'Sound': {1: 13},
                'Sync': {'in': 21, 'rec': 26, 'out': 16},
                'Opto': 19,
                'Status': 20}

    def __init__(self, **kwargs):
        super(RPPorts, self).__init__(**kwargs)
        import pigpio
        from RPi import GPIO
        self.GPIO = GPIO
        self.GPIO.setmode(self.GPIO.BCM)
        self.Pulser = pigpio.pi()
        self.PulseGen = pigpio.pulse
        self.WaveProp=pigpio.WAVE_MODE_REPEAT_SYNC
        self.thread = ThreadPoolExecutor(max_workers=4)
        self.frequency = 15
        self.ts = False
        self.pulses = dict()
        self.sound_pulses=[]

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
        if 'Opto' in self.channels:
            self.GPIO.setup(self.channels['Opto'], self.GPIO.OUT, initial=self.GPIO.LOW)
        if 'Liquid' in self.channels:
            for channel in self.channels['Liquid']:
                self.Pulser.set_mode(self.channels['Liquid'][channel], pigpio.OUTPUT)
                self.Pulser.set_pull_up_down(self.channels['Liquid'][channel], pigpio.PUD_DOWN)
        if 'Sound' in self.channels:
            for channel in self.channels['Sound']:
                self.Pulser.set_mode(self.channels['Sound'][channel], pigpio.OUTPUT)
        if 'Status' in self.channels:
            self.GPIO.setup(self.channels['Status'], self.GPIO.OUT, initial=self.GPIO.LOW)
        if 'Sync' in self.channels and 'out' in self.channels['Sync']:
            self.GPIO.setup(self.channels['Sync']['out'], self.GPIO.OUT, initial=self.GPIO.LOW)

        if self.exp.sync:
            self.GPIO.setup(self.channels['Sync']['rec'], self.GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            self.GPIO.setup(self.channels['Sync']['in'], self.GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            self.GPIO.add_event_detect(self.channels['Sync']['in'], self.GPIO.BOTH,
                                       callback=self._sync_in, bouncetime=20)
            self.dataset = self.logger.createDataset(dataset_name='sync',
                                                     dataset_type=np.dtype([("sync_times", np.double)]))

    def give_liquid(self, port, duration=False):
        if not duration: duration=self.duration[port]
        self.thread.submit(self._give_pulse, port, duration)

    def give_odor(self, delivery_port, odor_id, odor_duration, dutycycle):
        for i, idx in enumerate(odor_id):
            self.thread.submit(self.__pwd_out, self.channels['Odor'][delivery_port[i]], odor_duration, dutycycle[i])

    def opto_stim(self, duration, dutycycle):
        self.thread.submit(self.__pwd_out, self.channels['Opto'], duration, dutycycle)

    def sync_out(self, state=True):
        self.GPIO.output(self.channels['Sync']['out'], state)

    def give_sound(self, sound_freq=40500, volume=100, pulse_freq=0):
        self.thread.submit(self.__pulse_out, self.channels['Sound'][1], sound_freq, volume, pulse_freq)

    def stop_sound(self):
        self.Pulser.wave_tx_stop()
        self.Pulser.write(self.channels['Sound'][1], 0)
        self.Pulser.wave_clear()

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

    def set_operation_status(self, operation_status):
        if self.exp.sync:
            while not self.is_recording():
                print('Waiting for recording to start...')
                time.sleep(1)
        self.GPIO.output(self.channels['Status'], operation_status)

    def is_recording(self):
        if self.exp.sync:
            return self.GPIO.input(self.channels['Sync']['rec'])
        else:
            return False

    def cleanup(self):
        self.set_operation_status(False)
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
        if self.exp.sync:
            if 'Sync' in self.channels:
                 for channel in self.channels['Sync']:
                     self.GPIO.remove_event_detect(self.channels['Sync'][channel])
            self.closeDatasets()
        if self.ts:
            self.ts.stop()

    def in_position(self, port=0):
        """Determine if the specified port is in position and return the position data.

        Args:
            port (int, optional): The port to check the position of. Defaults to 0.

        Returns:
            tuple: A tuple containing the position data for the specified port in the following format:
                - position (Port): A Port object representing the position of the specified port.
                - position_dur (float): The duration in ms that the specified port has been in its current position.
                - position_tmst (float): The timestamp in ms that the specified port activated.

        If the specified port is not in position, the tuple will be (0, 0, 0).

        """
        # Get the current position and the position of the specified port.
        position = self.position
        port = self._get_position(port)

        # # If neither position has been set, return (0, 0, 0).
        if not position.port and not port: return 0, 0, 0

        # # If the specified port is not in the correct position, update the position and timestamp.
        if position != Port(type='Proximity', port=port):
            self._position_change(self.channels['Proximity'][max(port, position.port)])
                    
        # Calculate the duration and timestamp for the current position.
        position_dur = self.timer_ready.elapsed_time() if self.position.port else self.position_dur
        return self.position, position_dur, self.position_tmst

    def off_proximity(self):
        """checks if any proximity ports is activated

        used to make sure that none of the ports is activated before move on to the next trial
        if get_position returns 0 but position.type == Proximity means that self.position should be off
        so call _position_change to reset it to the correct value

        Returns:
            bool: True if all proximity ports are not activated
        """
        port = self._get_position()
        # port=0 means that no proximity port is activated
        if port==0:
            # # self.position.type == 'Proximity' and port=0 means that add_event_detect has lost the off of the proximity
            pos = self.position
            if pos.type == 'Proximity':
                # call position_change to reset the self.position
                self._position_change(self.channels['Proximity'][pos.port])
            return True
        else:
            return False

    def _get_position(self, ports=0):
        """get the position of the proximity ports

        _extended_summary_

        Args:
            ports (int, optional):  The port to check the position of. Defaults is 0 which means check all the ports.

        Returns:
            int: the id of the activated port else 0 
        """
        # if port is not specified check all proximity ports
        if not ports: ports = self.proximity_ports
        elif not type(ports) is list: ports = [ports]
        for port in ports:
            # find the position of the port
            in_position = self.GPIO.input(self.channels['Proximity'][port])
            # if port invert take the opposite
            if self.ports[Port(type='Proximity', port=port) == self.ports][0].invert:
                in_position = not in_position
            # return the port id if any port is in position
            if in_position: return port
        return 0

    def _position_change(self, channel=0):
        """Update the position of the animal and log the in_position event.
        
        Position_change is called in as callback at event_detect of GPIO.BOTH of the proximity channels.
        It is also called from function in_position in the case where the callback has not run but the position has changed.
        We want to log the port change and update the self.position with the activated port or reset it.
        Also we calculate 
            - position_dur (float): The duration in ms that the specified port has been in its current position.
            - position_tmst (float): The timestamp in ms that the specified port activated.
        Before we log the position we check that it has been changed, because due to the small bouncetime
        most proximity sensors(switches) will flicker back and forth between the two values before settling down.
        
        Args:
            channel (int, optional): The channel number of the proximity sensor. Defaults to 0.
        """
        # Get the port number corresponding to the proximity sensor channel
        port = self._channel2port(channel, 'Proximity')
        # Check if the animal is in position
        in_position = self._get_position(port.port)
        # Start the timer if the animal is in position
        if in_position: self.timer_ready.start()
        # Log the in_position event and update the position if there is a change in position
        if in_position and not self.position.port:
            self.position_tmst = self.beh.log_activity({**port.__dict__, 'in_position': 1})
            self.position = port
        elif not in_position and self.position.port:
            tmst = self.beh.log_activity({**port.__dict__, 'in_position': 0})
            self.position_dur = tmst - self.position_tmst
            self.position = Port()

    def _give_pulse(self, port, duration):
        self.Pulser.wave_add_generic([self.PulseGen(1 << self.channels['Liquid'][port], 0, int(duration*1000)),
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

    def __pulse_out(self, channel, freq, dutycycle=100, pulse_freq=0):
        self.sound_pulses=[]
        signal_duration=round(1/freq*1e6)   #microseconds
        # Speaker has non monotonic response with ~50%dutycycle is maximum response. Thus normalize percentage by /2.
        if dutycycle==0:
            pass
        else:
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
