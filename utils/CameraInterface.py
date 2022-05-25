import subprocess
import multiprocessing
import io
import picamera
import os

class CamOutput(object):
    def __init__(self, camera, video_filename, tms_filename, logger):
        self.camera       = camera
        self.video_output = io.open(video_filename, 'wb')
        self.pts_output   = io.open(tms_filename, 'w', 1) # buffering = 1 means that every line is buffered
        self.start_time   = None
        self.logger       = logger

    def write(self, buf):
        self.video_output.write(buf)
        if self.camera.frame.complete and self.camera.frame.timestamp:
            if self.start_time is None:
                self.start_time = self.camera.frame.timestamp
                self.start_time_logger = self.logger.logger_timer.elapsed_time()
            self.pts_output.write(f"\n{self.start_time_logger+(self.camera.frame.timestamp - self.start_time)}")
        
    def flush(self):
        # run when camera.stop_recording() executes
        self.video_output.flush()
        self.pts_output.flush()
        os.fsync(self.video_output)
        os.fsync(self.pts_output) 
        self.close()
        
    def close(self):
        self.video_output.close()
        self.pts_output.close()	

class Runner():
    def __init__(self, source_path=None, target_path=None, filename=None):
        print("Init")
        self.source_path = source_path
        self.target_path = target_path
        self.filename = filename
        self.filetype = 'h264'

    def start(self, logger=None, resolution = (640, 480), framerate = 15):
        self.framerate = framerate
        print("Start Video Recording")
        self.event = multiprocessing.Event()
        self.p = multiprocessing.Process(target=self.start_recording, args=(
                                         logger, resolution, framerate,
                                         self.source_path, self.filename+'.'+self.filetype,
                                         self.filename+'.txt',self.event, self.filetype))
        self.p.start()

    def stop(self):
        self.event.set() # Flag for stop Recording
        self.p.join() # Wait for Proccess to finish
        # convert h264 to mp4 at target path
        subprocess.run(["ffmpeg", "-framerate", str(self.framerate), "-i", 
                        self.source_path+self.filename+'.'+self.filetype,
                        "-c","copy", self.target_path+self.filename+'.mp4'])
                        
    @staticmethod
    def start_recording(logger=None, resolution = (640, 480), framerate = 15,
                    path = '/', filename = 'video.h264',
                    tmst_filename = 'tmst.txt', event=None, filetype='h264'):     
        with picamera.PiCamera() as camera:
            camera.resolution = resolution
            camera.framerate = framerate
            # If output(first argument) is not a string, but is an object with a write method, 
            # it is assumed to be a file-like object and the video data is appended to it 
            # (the implementation only assumes the object has a write() method - 
            # no other methods are required but flush will be called at the end of recording if it is present).
            camera.start_recording(CamOutput(camera, path+filename, path+tmst_filename, logger), format=filetype )
            while not event.is_set():
                camera.wait_recording(1) # check for exceptions
            print('Stop Video Recording')
            camera.stop_recording()
