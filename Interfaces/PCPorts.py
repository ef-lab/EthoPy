from core.Interface import *

class PCPorts(Interface):

    def __init__(self, **kwargs):
        super(PCPorts, self).__init__(**kwargs)
        import serial
        serial_port = 'COM1'
        self.serial = serial.serial_for_url(serial_port)
        self.serial.dtr = False

    def sync_out(self, state=True):
        self.serial.dtr = state