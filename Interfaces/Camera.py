import threading
import os
import time
import typing
import logging
import io
import warnings

from datetime import datetime
from queue import Queue
import numpy as np
import multiprocessing as mp

try:
    from skvideo.io import FFmpegWriter
    import_skvideo = True
except:
    import_skvideo = False

try:
    import picamera
    import_PiCamera = True
except:
    import_PiCamera = False

class Camera:
    def __init__(self,
                path:str=None,
                filename:str=None,  
                fps:int=15, 
                duration:int=None, 
                logger_timer:'Timer'=None, 
                **kwargs):

        self._cam = None 
        self._fps = None

        self._path = path
        self._filename = filename
        
        # self.duration = duration # TODO: use it to record for specific duration only
        self.logger_timer = logger_timer
        
        # self.camera_logger=logging # TODO: add logger in Camera
        
        # event for initialization
        self.initialized = threading.Event()
        self.initialized.clear()

        # event for recording
        self.recording = mp.Event()
        self.recording.clear() 

        # event for stop recording
        self.stop = mp.Event()
        self.stop.clear()

        if not globals()['import_skvideo']:
            raise ImportError('you need to install the skvideo: sudo pip3 install sk-video')

    def setup(self):
        self.frame_queue = Queue()
        self.capture_runner = threading.Thread(target=self.rec)
        self.thread_runner = threading.Thread(target=self.dequeue, args=(self.frame_queue,))  # max insertion rate of 10 events/sec

    def start_rec(self):
        self.capture_runner.start()
        self.thread_runner.start()

    def dequeue(self, frame_queue:"Queue"):
        while not self.stop.is_set() or not frame_queue.empty():
            if not frame_queue.empty():
                item = frame_queue.get() # tuple with buffer and timestamp
                if self.stream=='compress':
                    self.video_output.write(item[1])
                elif self.stream=='raw':
                    img = item[1].copy()
                    self.video_output.writeFrame(img)
                else:
                    warnings.warn("Recording is neither raw or stream so the results aren't saved")
                    return
                self.tmst_output.write(f"{item[0]}\n")
            else:
                time.sleep(.01)

    def stop_rec(self):
        self.stop.set()

    def _init_camera(self):
        pass

    def _process(self):
        "process frame before save it"
        pass
    
    @property
    def path(self):
        if self._path is None:
            self._path='/mnt/lab/data/behavior_video_rp/'
            self._path=self._path + f"video_rec {datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}/"

        if not os.path.exists(self._path) and not self.recording.is_set():
            os.makedirs(self._path)

        return self._path

    @path.setter
    def path(self, path):
        self._path = path

    @property
    def filename(self):
        if self._filename is None:
            self._filename = 'video_rec_%s' % (datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        elif os.path.exists(self.path+self._filename) and not self.recording.is_set():
            warnings.warn(f'{self.path+self._filename} is already exists!')
            self._filename = 'video_rec_%s' % (datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))

        return self._filename

    @filename.setter
    def filename(self, filename):
        self._filename = filename

class PiCamera(Camera):
    def __init__(self,  
                sensor_mode:int=0,
                resolution:tuple=(1280,720), 
                fps:int=15,
                shutter_speed:int=0,
                video_format:str='rgb',
                logger_timer:'Timer'=None,
                *args, **kwargs):

        if not globals()['import_PiCamera']:
            raise ImportError('the picamera package could not be imported, install it before use!')

        
        super(PiCamera, self).__init__(*args, **kwargs)

        self.video_format = video_format
        self.sensor_mode = sensor_mode
        self.resolution = resolution
        self.fps = fps
        self.logger_timer=logger_timer
        self.video_type = self.check_video_format(video_format)
        self.shutter_speed=shutter_speed

        self.setup()

    def setup(self):
        self.tmst_output   = io.open(f"{self.path}tmst_{self.filename}.txt", 'w', 1) # buffering = 1 means that every line is buffered
        
        if 'compress'==self.check_video_format(self.video_format):
            self.video_output = io.open(self.path+self.filename+'.h264', 'wb')
            self.stream='compress'
        else:
            self.stream='raw'
            out_vid_fn = self.path+self.filename+'.mp4'
            self.video_output = FFmpegWriter(out_vid_fn, inputdict={'-r': str(self.fps),},
                                            outputdict={
                                                '-vcodec': 'libx264',
                                                '-pix_fmt': 'yuv420p',
                                                '-r': str(self.fps),
                                                '-preset': 'ultrafast',
                                            },)

        super(PiCamera, self).setup()

    def rec(self):
        
        if self.recording.is_set():
            warnings.warn('Camera is already recording!')
            return

        self.recording_init()
        self.cam.start_recording(self._picam_writer, self.video_format)
        
    def recording_init(self):
        
        self.stop.clear()
        self.recording.set()

        self.cam = self.init_cam()
        self._picam_writer = self.PiCam_Output(self.cam, resolution=self.resolution, 
                                                frame_queue=self.frame_queue, 
                                                video_type = self.video_type,
                                                logger_timer=self.logger_timer)        

    def init_cam(self) -> 'picamera.PiCamera':

        cam = picamera.PiCamera(
            resolution=self.resolution,
            framerate=self.fps,
            sensor_mode=self.sensor_mode)
        if self.shutter_speed!=0: cam.shutter_speed = self.shutter_speed
        self.initialized.set()

        return cam

    def stop_rec(self):
        if self.recording.is_set():
            self.cam.stop_recording()
            self.cam.close()

        super().stop_rec()
        self.capture_runner.join()
        self.thread_runner.join()
        self.video_output.close()

        self.recording.clear()
        self._cam=None

    @property
    def sensor_mode(self) -> int:
        return self._sensor_mode

    @sensor_mode.setter
    def sensor_mode(self, sensor_mode: int):
        self._sensor_mode = sensor_mode
        if self.initialized.is_set():
            self.cam.sensor_mode = self._sensor_mode

    @property
    def fps(self) -> int:
        return self._fps

    @fps.setter
    def fps(self, fps:int):
        self._fps = fps
        if self.initialized.is_set():
            self.cam.framerate = self._fps
        
    def check_video_format(self, video_format:str):
        if video_format in ['h264', 'mjpeg']:
            return 'compress'
        elif video_format in ['yuv', 'rgb', 'rgba','bgr','bgra']:
            return 'raw'
        else:
            raise Exception(f"the video format: {video_format} is not supported by picamera!!") 

    class PiCam_Output:
            def __init__(self, camera, resolution:typing.Tuple[int, int], frame_queue, video_type, logger_timer):
                
                self.camera = camera
                self.resolution = resolution
                self.frame_queue = frame_queue
                self.logger_timer=logger_timer

                self.first_tmst = None
                self.tmst=0
                self.i_frames = 0
                self.video_type = video_type

            def write(self, buf):
                '''
                Write timestamps of each frame: https://forums.raspberrypi.com/viewtopic.php?f=43&t=106930&p=736694#p741128
                '''
                if self.video_type=='raw':
                    if self.camera.frame.complete and self.camera.frame.timestamp:
                        # TODO:Use camera timestamps
                        # the first time consider the first timestamp as zero
                        # if self.first_tmst is None:
                        #     self.first_tmst = self.camera.frame.timestamp # first timestamp of camera
                        # self.tmst = (self.camera.frame.timestamp-self.first_tmst)+self.logger_timer.elapsed_time()
                        # print("self.logger_timer.elapsed_time() :", self.logger_timer.elapsed_time())
                        
                        self.tmst = self.logger_timer.elapsed_time()
                        self.frame = np.frombuffer(
                                buf, dtype=np.uint8,
                                count=self.camera.resolution[0]*self.camera.resolution[1]*3
                            ).reshape((self.camera.resolution[1], self.camera.resolution[0], 3))
                        self.frame_queue.put(( self.tmst,self.frame))
                else:
                    tmst_t = self.camera.frame.timestamp
                    if  tmst_t != None:
                        # TODO:Fix timestamps in camera is in μs but in timer in ms
                        if self.first_tmst is None:
                            self.first_tmst = tmst_t # first timestamp of camera
                        else:
                            self.tmst = (tmst_t-self.first_tmst)+self.logger_timer.elapsed_time()
                    self.frame_queue.put((self.tmst,buf))
