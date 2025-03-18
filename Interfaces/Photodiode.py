from core.Interface import *
import json, time
from serial import Serial
import threading
from queue import PriorityQueue


class Photodiode(Interface):
    thread_end, msg_queue = threading.Event(), PriorityQueue(maxsize=1)

    def __init__(self, **kwargs):
        super(Photodiode, self).__init__(**kwargs)
        self.port = self.exp.logger.get(table='SetupConfiguration', key=self.exp.params, fields=['path'])[0]
        self.baud = 115200
        self.timeout = .001
        self.offset = None
        self.no_response = False
        self.timeout_timer = time.time()
        self.dataset = self.exp.logger.createDataset(dataset_name='fliptimes',
                                                 dataset_type=np.dtype([("phd_level", np.double),
                                                                        ("tmst", np.double)]))
        self.ser = Serial(self.port, baudrate=self.baud)
        sleep(1)
        self.thread_runner = threading.Thread(target=self._communicator)
        self.thread_runner.start()
        sleep(1)
        print('logger timer:', self.exp.logger.logger_timer.elapsed_time())
        self.msg_queue.put(Message(type='offset', value=self.exp.logger.logger_timer.elapsed_time()))

    def cleanup(self):
        self.thread_end.set()
        self.ser.close()  # Close the Serial connection

    def _communicator(self):
        while not self.thread_end.is_set():
            if not self.msg_queue.empty():
                msg = self.msg_queue.get().dict()
                self._write_msg(msg)  # Send it
            msg = self._read_msg()  # Read the response
            if msg is not None:
                if msg['type'] == 'Level' and self.offset is not None:
                    print(msg['value'], msg['tmst'])
                    self.dataset.append('fliptimes', [msg['value'], msg['tmst']])
                elif msg['type'] == 'Offset':
                    self.offset = msg['value']
                    print('offset:', self.offset)

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


@dataclass
class Message:
    type: str = datafield(compare=False, default='')
    value: int = datafield(compare=False, default=0)

    def dict(self):
        return self.__dict__

