import io
import multiprocessing as mp
import os
import shutil
import threading
import time
import warnings
from datetime import datetime
from queue import Queue
from typing import Optional, Tuple

import numpy as np

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
                source_path: Optional[str] = None,
                target_path: Optional[str] = None,
                filename: Optional[str] = None,  
                fps: int = 15, 
                logger_timer: 'Timer' = None, 
                **kwargs):
        
        self.initialized = threading.Event()
        self.initialized.clear()

        self.recording = mp.Event()
        self.recording.clear() 

        self.stop = mp.Event()
        self.stop.clear()

        self.fps = fps
        self._cam = None 
        self.filename = filename
        self.source_path = source_path
        self.target_path = target_path 
        self.logger_timer = logger_timer
        if not globals()['import_skvideo']:
            raise ImportError('you need to install the skvideo: sudo pip3 install sk-video')
        
        self.setup()

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, filename):
        if filename is None:
            filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        self._filename = filename

    @property
    def source_path(self) -> str:
        return self._source_path

    @source_path.setter
    def source_path(self, source_path):
        # make folder if doesn't exist
        if not os.path.exists(source_path) and not self.recording.is_set():
            os.makedirs(source_path)

        # check that folder has been made correctly
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"The path '{source_path}' does not exist.")

        self._source_path = source_path

    @property
    def target_path(self) -> str:
        return self._target_path

    @target_path.setter
    def target_path(self, target_path):
        # make folder if doesn't exist
        if not os.path.exists(target_path) and not self.recording.is_set():
            os.makedirs(target_path)

        # check that folder has been made correctly
        if not os.path.exists(target_path):
            raise FileNotFoundError(f"The path '{target_path}' does not exist.")

        self._target_path = target_path

    def clear_local_videos(self):
        if os.path.exists(self.source_path):
            files = [file for _, _, files in os.walk(self.source_path) for file in files]
            for file in files:
                shutil.move(os.path.join(self.source_path, file), os.path.join(self.target_path, file))
                print(f"transfered file : {file}")

    def setup(self):
        self.frame_queue = Queue()
        self.capture_runner = threading.Thread(target=self.rec)
        self.write_runner = threading.Thread(target=self.dequeue, args=(self.frame_queue,))  # max insertion rate of 10 events/sec
            
    def start_rec(self):
        self.capture_runner.start()
        self.write_runner.start()

    def dequeue(self, frame_queue:"Queue"):
        while not self.stop.is_set() or not frame_queue.empty():
            if not frame_queue.empty():
                self.write_frame(frame_queue.get())
            else:
                time.sleep(.01)

    def stop_rec(self):
        self.stop.set()
        self.capture_runner.join()
        self.write_runner.join()

    def rec(self):
        raise NotImplementedError

    def write_frame(self, item):
        raise NotImplementedError

class PiCamera(Camera):
    def __init__(self,  
                sensor_mode:int=0,
                resolution:tuple=(1280,720), 
                shutter_speed:int=0,
                video_format:str='rgb',
                logger_timer:'Timer'=None,
                *args, **kwargs):

        if not globals()['import_PiCamera']:
            raise ImportError('the picamera package could not be imported, install it before use!')
        
        self.video_format = video_format
        
        super(PiCamera, self).__init__(*args, **kwargs)
        self.resolution    = resolution
        self.logger_timer  = logger_timer
        self.video_type    = self.check_video_format(video_format)
        self.shutter_speed = shutter_speed
        self.sensor_mode   = sensor_mode

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

    def setup(self):
        if 'compress'==self.check_video_format(self.video_format):
            self.stream='compress'
            self.video_output = io.open(self.source_path+self.filename+'.'+self.video_format, 'wb')
        else:
            self.stream='raw'
            self.tmst_output   = io.open(f"{self.source_path}tmst_{self.filename}.txt", 'w', 1) # buffering = 1 means that every line is buffered
            out_vid_fn = self.source_path+self.filename+'.mp4'
            self.video_output = FFmpegWriter(out_vid_fn, inputdict={'-r': str(self.fps),},
                                            outputdict={
                                                '-vcodec': 'libx264',
                                                '-pix_fmt': 'yuv420p',
                                                '-r': str(self.fps),
                                                '-preset': 'ultrafast',
                                            },)
        super().setup()

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

        self.video_output.close()
        if self.stream=='raw': self.tmst_output.close()

        self.recording.clear()
        self._cam=None
        self.clear_local_videos()

    def write_frame(self, item):
        if not self.stop.is_set():
            if self.stream=='compress':
                self.video_output.write(item[1])
            elif self.stream=='raw':
                img=item[1].copy()
                self.video_output.writeFrame(img)
                self.tmst_output.write(f"{item[0]}\n")
            else:
                warnings.warn("Recording is neither raw or stream so the results aren't saved")
                return
            
        
    def check_video_format(self, video_format:str):
        if video_format in ['h264', 'mjpeg']:
            return 'compress'
        elif video_format in ['yuv', 'rgb', 'rgba','bgr','bgra']:
            return 'raw'
        else:
            raise Exception(f"the video format: {video_format} is not supported by picamera!!") 

    class PiCam_Output:
            def __init__(self, camera, resolution:Tuple[int, int], frame_queue, video_type, logger_timer):
                
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
