from core.Interface import *
from concurrent.futures import ThreadPoolExecutor
from utils.Timer import Timer


class PCPorts(Interface):

    def __init__(self, **kwargs):
        super(PCPorts, self).__init__(**kwargs)
        import serial
        self.thread = ThreadPoolExecutor(max_workers=4)
        serial_port = 'COM1'
        self.serial = serial.serial_for_url(serial_port)
        self.serial.dtr = False
        self.timer = Timer()
        self.frequency = 10

    def sync_out(self, state=True):
        self.serial.dtr = state

    def opto_stim(self, duration, dutycycle):
        self.thread.submit(self.__pwd_out, duration, dutycycle)

    def __pwd_out(self, duration, dutycycle):
        self.timer.start()
        while self.timer.elapsed_time() < duration:
            if (self.timer.elapsed_time() % (1000/self.frequency))*self.frequency/10 > dutycycle:
                state = False
            else:
                state = True
            self.serial.rts = state
            sleep(0.0001)
