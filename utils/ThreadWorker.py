import sys
import time
import threading


class GetHWPoller(threading.Thread):
    """ thread to repeatedly evaluate a function
    sleeptime: time to sleep between pollfunc calls
    pollfunc: function to repeatedly call to poll hardware"""

    def __init__(self, sleeptime, pollfunc):

        self.sleeptime = sleeptime
        self.pollfunc = pollfunc
        threading.Thread.__init__(self)
        self.runflag = threading.Event()  # clear this to pause thread
        self.runflag.clear()

    def run(self):
        self.runflag.set()
        self.worker()

    def worker(self):
        while (1):
            if self.runflag.is_set():
                self.pollfunc()
                time.sleep(self.sleeptime)
            else:
                time.sleep(0.01)

    def pause(self):
        self.runflag.clear()

    def resume(self):
        self.runflag.set()

    def running(self):
        return (self.runflag.is_set())

    def kill(self):
        print("WORKER END")
        #sys.stdout.flush()
        #  self._Thread__stop()
