import numpy as np
from threading import Event
from core.Interface import *
import json, time
from serial import Serial
import threading
from queue import PriorityQueue


class Arduino(Interface):
    thread_end, msg_queue, callbacks = threading.Event(), PriorityQueue(maxsize=1), True

    def __init__(self, **kwargs):
        super(Arduino, self).__init__(**kwargs)
        self.port = self.logger.get(table='SetupConfiguration', key=self.exp.params, fields=['path'])[0]
        self.baud = 115200
        self.timeout = .001
        self.no_response = False
        self.timeout_timer = time.time()
        self.ser = Serial(self.port, baudrate=self.baud)
        sleep(1)
        self.thread_runner = threading.Thread(target=self._communicator)
        self.thread_runner.start()

    def give_liquid(self, port, duration=False):
        if not duration: duration = self.duration[port]
        self.msg_queue.put(Message(type='pulse', port=port, duration=duration))

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

        # If no position has been set, return (0, 0, 0).
        if not position.port: return 0, 0, 0

        # Calculate the duration and timestamp for the current position.
        position_dur = self.timer_ready.elapsed_time() if self.position.port else self.position_dur
        return self.position, position_dur, self.position_tmst

    def off_proximity(self):
        """checks if any proximity ports are activated
        used to make sure that none of the ports is activated before move on to the next trial
        if get_position returns 0 but position.type == Proximity means that self.position should be off
        so call _position_change to reset it to the correct value
        Returns:
            bool: True if all proximity ports are not acrtivated
        """
        return(not self.position.state)

    def cleanup(self):
        self.ser.close()  # Close the Serial connection

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

    def _communicator(self):
        while not self.thread_end.is_set():
            if not self.msg_queue.empty():
                msg = self.msg_queue.get().dict()
                self._write_msg(msg)  # Send it
            msg = self._read_msg()  # Read the response
            if msg is not None and self.callbacks:
                response = self.ports[Port(type=msg['type'], port=msg['port']) == self.ports][0]
                response.state = msg['state']
                if msg['type'] == 'Proximity':
                    self._position_change(response)
                elif msg['type'] == 'Lick':
                    self._lick_port_activated(response)

    def _read_msg(self):
        """Reads a line from the serial buffer,
        decodes it and returns its contents as a dict."""
        now = time.time()
        if (now - self.timeout_timer) > 3:
            self.timeout_timer = time.time()
            return None
        elif self.ser.in_waiting == 0:  # Nothing received
            self.no_response = True
            return None
        incoming = self.ser.readline().decode("utf-8")
        resp = None
        self.no_response = False
        self.timeout_timer = time.time()
        try:
            resp = json.loads(incoming)
        except json.JSONDecodeError:
            print("Error decoding JSON message!")
        return resp

    def _write_msg(self, message=None):
        """Sends a JSON-formatted command to the serial interface."""
        try:
            json_msg = json.dumps(message)
            self.ser.write(json_msg.encode("utf-8"))
        except TypeError:
            print("Unable to serialize message.")

    def _position_change(self, response):
        """Update the position of the animal and log the in_position event.
        We want to log the port change and update the self.position with the activated port or reset it.
        Also we calculate
            - position_dur (float): The duration in ms that the specified port has been in its current position.
            - position_tmst (float): The timestamp in ms that the specified port activated.
        Args:
            channel (int, optional): The channel number of the proximity sensor. Defaults to 0.
        """
        # Check if the animal is in position
        in_position = response.state
        # Start the timer if the animal is in position
        if in_position: self.timer_ready.start()
        # Log the in_position event and update the position if there is a change in position
        if in_position and not self.position.port:
            self.position_tmst = self.beh.log_activity({**response.__dict__, 'in_position': 1})
            self.position = response
        elif not in_position and self.position.port:
            tmst = self.beh.log_activity({**response.__dict__, 'in_position': 0})
            self.position_dur = tmst - self.position_tmst
            self.position = Port()

    def _lick_port_activated(self, response):
        self.resp_tmst = self.logger.logger_timer.elapsed_time()
        self.beh.log_activity({**response.__dict__, 'time': self.resp_tmst})
        self.response = response
        return self.response, self.resp_tmst


@dataclass
class Message:
    type: str = datafield(compare=False, default='')
    port: str = datafield(compare=False, default='')
    duration: int = datafield(compare=False, default=0)

    def dict(self):
        return self.__dict__

