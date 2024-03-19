import numpy as np
import threading, multiprocessing, struct, time
from core.Interface import *


class Ball(Interface):
    speed, timestamp, update_location, prev_loc_x, prev_loc_y, loc_x, loc_y, theta, xmx, ymx = 0, 0, True, 0, 0, 0, 0, 0, 1, 1

    def __init__(self, exp, ball_radius=0.125):
        self.cleanup()
        self.logger = exp.logger
        self.exp = exp
        self.mouse1 = MouseReader("/dev/input/by-path/platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.1:1.0-mouse", exp.logger)
        self.mouse2 = MouseReader("/dev/input/by-path/platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.2:1.0-mouse", exp.logger)
        self.setPosition()
        self.phi_z1 = 1  # angle of z axis (rotation)
        self.phi_z2 = self.phi_z1
        self.phi_y1 = np.pi - 0.13  # angle of y1 axis (mouse1) .6
        self.phi_y2 = self.phi_y1 + np.pi/2  # angle of y2 axis (mouse2)
        self.ball_radius = ball_radius
        self.dataset = self.logger.createDataset(dataset_name='ball',
                                                 dataset_type=np.dtype([("loc_x", np.double),
                                                                        ("loc_y", np.double),
                                                                        ("theta", np.double),
                                                                        ("tmst", np.double)]))

        self.thread_end = threading.Event()
        self.thread_runner = threading.Thread(target=self.readMouse)
        self.thread_runner.start()

    def readMouse(self):
        while not self.thread_end.is_set():
            t = self.logger.logger_timer.elapsed_time()
            x1, y1, x2, y2, tmst1, tmst2 = 0, 0, 0, 0, t, t
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
            theta = self.theta + (theta_step2 + theta_step1)/2
            theta = np.mod(theta, 2*np.pi)

            x = -xm*np.sin(self.theta) - ym*np.cos(self.theta)
            y = -xm*np.cos(self.theta) + ym*np.sin(self.theta)

            loc_x = self.prev_loc_x + np.double(x)
            loc_y = self.prev_loc_y + np.double(y)
            timestamp = max(tmst1, tmst2)
            self.speed = np.sqrt((loc_x - self.prev_loc_x)**2 + (loc_y - self.prev_loc_y)**2)/(timestamp - self.timestamp)
            self.prev_loc_x = max(min(loc_x, self.xmx), 0)
            self.prev_loc_y = max(min(loc_y, self.ymx), 0)
            self.timestamp = timestamp

            if self.update_location:
                self.theta = theta
                self.loc_x = max(min(self.loc_x + np.double(x), self.xmx), 0)
                self.loc_y = max(min(self.loc_y + np.double(y), self.ymx), 0)
                print(self.loc_x, self.loc_y, self.theta/np.pi*180)
                self.dataset.append('tracking_data', [self.loc_x, self.loc_y, self.theta, self.timestamp])
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

    def cleanup(self):
        try:
            self.thread_end.set()
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
            queue.put({'x': x/dpm, 'y': y/dpm, 'timestamp': self.logger.logger_timer.elapsed_time()})

    def close(self):
        self.thread_end.set()
        self.thread_runner.join()