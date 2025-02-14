from core.Interface import *
import json, time
from serial import Serial
import threading
from queue import PriorityQueue


class Wheel(Interface):
    thread_end, msg_queue = threading.Event(), PriorityQueue(maxsize=1)

    def __init__(self, **kwargs):
        super(Wheel, self).__init__(**kwargs)
        self.port = self.logger.get(table='SetupConfiguration', key=self.exp.params, fields=['path'])[0]
        self.baud = 115200
        self.timeout = .001
        self.offset = None
        self.no_response = False
        self.timeout_timer = time.time()
        self.wheel_dataset = self.logger.createDataset(dataset_name='wheel',
                                                 dataset_type=np.dtype([("position", np.double),
                                                                        ("tmst", np.double)]))
        self.frame_dataset = self.logger.createDataset(dataset_name='frames',
                                                 dataset_type=np.dtype([("idx", np.double),
                                                                        ("tmst", np.double)]))
        self.ser = Serial(self.port, baudrate=self.baud)
        sleep(1)
        self.thread_runner = threading.Thread(target=self._communicator)
        self.thread_runner.start()
        sleep(1)
        self.msg_queue.put(Message(type='offset', value=self.logger.logger_timer.elapsed_time()))

    def release(self):
        self.thread_end.set()
        self.ser.close()  # Close the Serial connection

    def _communicator(self):
        while not self.thread_end.is_set():
            if not self.msg_queue.empty():
                msg = self.msg_queue.get().dict()
                self._write_msg(msg)  # Send it
            msg = self._read_msg()  # Read the response
            if msg is not None:
                if msg['type'] == 'Position' and self.offset is not None:
                    self.wheel_dataset.append('wheel', [msg['value'], msg['tmst']])
                elif msg['type'] == 'Frame' and self.offset is not None:
                    self.frame_dataset.append('frames', [msg['value'], msg['tmst']])
                elif msg['type'] == 'Offset':
                    self.offset = msg['value']

    def _read_msg(self):
        """Reads a line from the serial buffer,
        decodes it and returns its contents as a dict."""
        if self.ser.in_waiting == 0:  # don't run faster than necessary
            return None

        try: # read message
            incoming = self.ser.readline().decode("utf-8")
        except:     # partial read of message, retry
            return None

        try: # decode message
            response = json.loads(incoming)
            return response
        except json.JSONDecodeError:
            print("Error decoding JSON message!")
            return None

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

