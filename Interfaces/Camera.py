import base64
import io
import json
import logging
import multiprocessing as mp
import os
import shutil
import threading
import time
import warnings
from abc import ABC, abstractmethod
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from multiprocessing import Pool
from pathlib import Path
from queue import Queue
from threading import Condition, Lock, Thread
from typing import Any, List, Optional, Union

import numpy as np

from utils.Timer import Timer

# from libcamera import controls


try:
    from core.Logger import Logger
except ImportError:
    print("Logger not found.")

try:
    import cv2
    from picamera2 import MappedArray, Picamera2
    from picamera2.encoders import H264Encoder, MJPEGEncoder
    from picamera2.outputs import FfmpegOutput, FileOutput

    IMPORT_PICAMERA = True
except ImportError as e:
    IMPORT_PICAMERA = False


class Camera(ABC):
    """
    A class to manage a camera.

    This class provides methods to initialize, start, stop, and record from a camera.
    It also provides methods to manage the recording process, such as setting up a frame
    queue and writing frames to it.

    Attributes:
        filename (str, optional): The name of the file.
        initialized (threading.Event): An event to indicate whether the camera is initialized.
        recording (mp.Event): An event to indicate whether the camera is recording.
        stop (mp.Event): An event to indicate whether the camera should stop recording.
    """

    def __init__(
        self,
        filename: Optional[str] = None,
        logger: Optional["Logger"] = None,
        video_aim: Optional[str] = None,
    ):
        self.recording = mp.Event()
        self.recording.clear()

        with open("local_conf.json", "r", encoding="utf-8") as f:
            conf = json.load(f)

        self.source_path = (
            self._check_json_config("video_source_path", conf)
            + f"/Recordings/{filename}/"
        )
        self.target_path = (
            self._check_json_config("video_target_path", conf)
            + f"/Recordings/{filename}/"
        )

        try:
            self.serve_port = conf["server.port"]
        except KeyError:
            self.serve_port = 0
        if self.serve_port:
            self.server_user = self._check_json_config("server.user", conf)
            self.server_password = self._check_json_config("server.password", conf)
        self.httpthread = None
        self.tmst_type = None
        self.dataset = None

        self.post_process = mp.Event()
        self.post_process.clear()
        self.process_queue = mp.Queue()

        self.stop = mp.Event()
        self.stop.clear()

        self._cam = None
        self.filename = filename
        self.logger = logger

        self.frame_queue = None
        self.capture_runner = None
        self.write_runner = None

        if logger:
            # log video recording
            logger.log_recording(
                dict(
                    rec_aim=video_aim,
                    software="EthoPy",
                    version="0.1",
                    filename=self.filename + ".mp4",
                    source_path=self.source_path,
                    target_path=self.target_path,
                )
            )
            h5s_filename = (
                f"animal_id_{logger.trial_key['animal_id']}"
                f"_session_{logger.trial_key['session']}.h5"
            )
            self.filename_tmst = "video_tmst_" + h5s_filename
            logger.log_recording(
                dict(
                    rec_aim="sync",
                    software="EthoPy",
                    version="0.1",
                    filename=self.filename_tmst,
                    source_path=self.source_path,
                    target_path=self.target_path,
                )
            )

        self.camera_process = mp.Process(target=self.start_rec)
        self.camera_process.start()

    @property
    def filename(self) -> str:
        """
        Get the filename.

        Returns:
            str: The filename.
        """
        return self._filename

    @filename.setter
    def filename(self, filename: Optional[str]):
        """
        Set the filename. If filename is None, set it to the current date and time.

        Args:
            filename (Optional[str]): The filename.
        """
        self._filename = filename or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    @property
    def source_path(self) -> str:
        """
        Get the source path.

        Returns:
            str: The source path.
        """
        return self._source_path

    @source_path.setter
    def source_path(self, source_path: str):
        """
        Set the source path. If the path does not exist, create it.

        Args:
            source_path (str): The source path.
        """
        self._source_path = self._create_and_set_path(source_path)

    @property
    def target_path(self) -> str:
        """
        Get the target path.

        Returns:
            str: The target path.
        """
        return self._target_path

    @target_path.setter
    def target_path(self, target_path: str):
        """
        Set the target path. If the path does not exist, create it.

        Args:
            target_path (str): The target path.
        """
        self._target_path = self._create_and_set_path(target_path)

    def _create_and_set_path(self, path: str) -> str:
        """
        Create the path if it does not exist and return the path.

        Args:
            path (str): The path.

        Returns:
            str: The path.
        """
        if not self.recording.is_set():
            os.makedirs(path, exist_ok=True)

        if not os.path.exists(path):
            raise FileNotFoundError(f"The path '{path}' does not exist.")

        return path

    @staticmethod
    def copy_file(args):
        """
        Copy a file from the source path to the target path.

        Args:
            args (tuple): A tuple containing the source file path and the target directory path.

        Returns:
            None

        Raises:
            FileNotFoundError: If the source file is not found.

        """
        file, target = args
        try:
            shutil.copy(str(file), str(target / file.name))
            print(f"Transferred file: {file.name}")
            # Verify the file exists in the target directory
            if os.path.exists(str(target / file.name)) and \
               os.path.getsize(str(file)) == os.path.getsize(str(target / file.name)):
                os.remove(str(file))
                print(f"Deleted original file: {file.name}")
            else:
                print(f"Failed to transfer file: {file.name}")
        except FileNotFoundError as ex:
            print(f"Failed to transfer file: {file.name}. Reason: {ex}")

    def clear_local_videos(self) -> None:
        """
        Move all files from the source path to the target path.
        """
        source = Path(self.source_path)
        target = Path(self.target_path)

        if not source.is_dir():
            raise ValueError(f"Source path {source} does not exist or is not a directory.")

        if not target.exists():
            raise ValueError(f"Target path {target} does not exist or is not a directory.")

        files = [(entry, target) for entry in source.iterdir() if entry.is_file()]

        with Pool(processes=min(2, os.cpu_count()-1)) as pool:
            pool.map(self.copy_file, files)

        # Clean up if the source directory is empty
        if not any(source.iterdir()):
            source.rmdir()
            print(f"Deleted the empty folder: {source}")

    def setup(self) -> None:
        """
        Set up the frame queue and the capture and write runners.
        """
        self.frame_queue = Queue()
        self.capture_runner = threading.Thread(target=self.rec)
        self.write_runner = threading.Thread(
            target=self.dequeue, args=(self.frame_queue,)
        )

    def start_rec(self) -> None:
        """
        Start the capture and write runners with exception handling.
        """
        try:
            self.setup()
            self.capture_runner.start()
            self.write_runner.start()
            self.capture_runner.join()
            self.write_runner.join()
        except Exception as cam_error:
            raise f"Exception occurred during recording: {cam_error}"

    def dequeue(self, frame_queue: Queue) -> None:
        """
        Dequeue frames from the frame queue and write them until the stop event is set.

        Args:
            frame_queue (Queue): The frame queue to dequeue frames from.
        """
        while not self.stop.is_set() or not frame_queue.empty():
            if not frame_queue.empty():
                self.write_frame(frame_queue.get())
            else:
                time.sleep(0.01)

    def stop_rec(self) -> None:
        """
        Set the stop event and join the write runner.
        """
        self.stop.set()
        time.sleep(1)
        # TODO: use join and close (possible issue due to h5 files)
        self.camera_process.join()

    @staticmethod
    def _check_json_config(key: str, conf) -> str:
        """
        Check if a key exists in the JSON configuration file.

        Args:
            key (str): The key to check.
        """
        if not conf.get(key, False):
            raise ValueError(f"{key} is not provided in the dj_local_conf.json.")
        else:
            return conf[key]

    @abstractmethod
    def rec(self) -> None:
        """
        Record frames. This method should be implemented by subclasses.
        """

    @abstractmethod
    def write_frame(self, item: Any) -> None:
        """
        Write a frame. This method should be implemented by subclasses.

        Args:
            item (Any): The frame to write.
        """


class PiCamera(Camera):
    """A class to manage a rasberry pi camera."""
    def __init__(
        self,
        resolution_x: int = 1280,
        resolution_y: int = 720,
        fps: int = 15,
        sensor_mode: int = 1,
        shutter_speed: int = 10000,
        file_format: str = "rgb",
        logger_timer: "Timer" = None,
        **kwargs,
    ):

        if not globals()["IMPORT_PICAMERA"]:
            raise ImportError(
                "the picamera package could not be imported, install it before use!"
            )
        self.initialized = threading.Event()
        self.initialized.clear()
        self.cam = None
        self.picamera_ouput = None

        self.sensor_mode = sensor_mode
        self.resolution = (resolution_x, resolution_y)
        self.shutter_speed = shutter_speed
        self.file_format = file_format
        self.tmst_output = None

        self.fps = fps
        self.logger_timer = logger_timer

        self._lock_serving = Lock()
        self._counter_serving = 0
        self._encoder_serving = None
        self._output_serving = None

        super().__init__(kwargs["filename"], kwargs["logger"], kwargs["video_aim"])

    @property
    def fps(self) -> int:
        """Get the frames per second of the camera."""
        return self._fps

    @fps.setter
    def fps(self, fps: int):
        """Set the frames per second of the camera."""
        if not isinstance(fps, int):
            raise TypeError("FPS must be an integer.")
        self._fps = fps
        if self.initialized.is_set():
            self.cam.framerate = self._fps

    def setup(self):
        """Setup the camera."""
        if self.logger is not None:
            self.tmst_type = "h5"
            self.dataset = self.logger.createDataset(
                dataset_name="frame_tmst",
                dataset_type=np.dtype([("txt", np.double)]),
                filename=self.filename_tmst,
                log=False,
            )
        else:
            self.tmst_type = "txt"
            self.tmst_output = io.open(
                os.path.join(self.source_path, f"tmst_{self.filename}.txt"),
                "w",
                encoding="utf-8",
            )
        super().setup()

    def rec(self) -> None:
        """Start recording"""
        try:
            if self.recording.is_set():
                warnings.warn("Camera is already recording!")
                return

            self.recording_init()
            self.cam.start()
            while not self.stop.is_set():
                time.sleep(1)
        except Exception as rec_error:
            raise f"Error during camera recording: {rec_error}"
        finally:
            self._stop_recording()

    def recording_init(self) -> None:
        """Initialize the recording."""
        self.stop.clear()
        self.recording.set()
        self.cam = self.init_cam()

    def init_cam(self) -> "PiCamera2":
        """Initialize the camera."""
        picam2 = Picamera2()
        _mode = picam2.sensor_modes[self.sensor_mode]
        config = picam2.create_video_configuration(
            raw={"size": _mode["size"], "format": _mode["format"].format},
            main={
                "format": "RGB888",
                "size": self.resolution,
            },
            lores={
                "format": "YUV420",
                "size": (int(self.resolution[0] / 4), int(self.resolution[1] / 4)),
            },
            controls={
                "FrameDurationLimits": (int(1e6 / self.fps), int(1e6 / self.fps)),
                "ExposureTime": int(self.shutter_speed),
                # "AfMode": controls.AfModeEnum.Manual,
                # "LensPosition": 0.0,
            },
        )
        picam2.configure(config)
        self.picamera_ouput = PicameraOutput(
            self.logger_timer, self.frame_queue, self.process_queue, self.post_process
        )
        picam2.post_callback = lambda request: self.picamera_ouput.annotate_timestamp(
            request
        )
        encoder = H264Encoder(10000000)
        output = FfmpegOutput(str(Path(self.source_path) / f"{self.filename}.mp4"))
        if self.serve_port > 0:
            self.httpthread = HTTPServerThread(
                self, server_user=self.server_user, server_password=self.server_password
            )
            self.httpthread.start()
        picam2.start_encoder(encoder, output)

        return picam2

    def _stop_recording(self) -> None:
        """Stop recording."""
        if self.recording.is_set():
            if self.httpthread:
                self.httpthread.stop_serving()
            self.cam.stop_recording()
            self.cam.close()

        if self.tmst_type == "txt":
            self.tmst_output.close()
        else:
            self.dataset.exit()

        self.recording.clear()
        self._cam = None
        self.clear_local_videos()

    def write_frame(self, item: Union[List, tuple]) -> None:
        """Write a frame to the output."""
        if not self.stop.is_set():
            if self.tmst_type == "txt":
                self.tmst_output.write(f"{item[0]}\n")
            elif self.tmst_type == "h5":
                self.dataset.append("frame_tmst", [item[0]])

    def start_serving(self) -> "StreamingOutput":
        """Start serving frames."""
        with self._lock_serving:
            if self._counter_serving == 0:
                self._encoder_serving = MJPEGEncoder()
                self._encoder_serving.framerate = self._fps
                self._output_serving = StreamingOutput()
                self.cam.start_recording(
                    self._encoder_serving, FileOutput(self._output_serving)
                )
            self._counter_serving += 1
        return self._output_serving

    def stop_serving(self) -> None:
        """Stop serving frames."""
        with self._lock_serving:
            self._counter_serving -= 1
            if self._counter_serving == 0:
                self.cam.stop_encoder(self._encoder_serving)
                self._encoder_serving = None
                self._output_serving = None


class PicameraOutput:
    """Process the output of the PiCamera."""
    def __init__(self, timer: Any, frame_queue: Any, process_queue: Any, post_process):
        self.timer = timer
        self.frame_queue = frame_queue
        self.process_queue = process_queue
        self.post_process = post_process
        self.position = (8, 16)
        self.font = cv2.FONT_HERSHEY_PLAIN
        self.color = (255, 255, 255)

    def annotate_timestamp(self, request: Any) -> None:
        """Annotate the frame with a timestamp."""
        timestamp = f"{self.timer.elapsed_time()}"
        with MappedArray(request, "main") as frame:
            cv2.putText(
                frame.array, timestamp, self.position, self.font, 1.0, self.color
            )
            self.frame_queue.put((timestamp,))
            if self.post_process.is_set():
                self.process_queue.put((timestamp, frame.array))


class StreamingOutput(io.BufferedIOBase):
    """A class that handles the streaming output."""

    def __init__(self):
        super().__init__()
        self.frame = None
        self.tmst_time = None
        self.condition = Condition()

    def write(self, buf: bytes) -> None:
        """Write the buffer to the frame and notify all waiting threads."""
        with self.condition:
            self.frame = buf
            self.tmst_time = time.time()
            self.condition.notify_all()


class HTTPServerThread(Thread):
    """A class that handles the HTTP server thread."""

    def __init__(
        self,
        cam: "Camera",
        serve_port: int = 8000,
        server_user: Optional[str] = None,
        server_password: Optional[str] = None,
    ):
        super().__init__()
        self.python_logger = logging.getLogger(self.__class__.__name__)
        self.server = ThreadingHTTPServer(
            ("", serve_port), self.CameraHTTPRequestHandler
        )
        self.server.cam = cam
        self.server.auth = None
        if server_user and server_password:
            str_auth = f"{server_user}:{server_password}"
            self.server.auth = "Basic " + base64.b64encode(str_auth.encode()).decode()

    def run(self) -> None:
        """Start the server."""
        self.python_logger.info(
            "Starting HTTP server on port %s", self.server.server_port
        )
        self.server.serve_forever()

    def stop_serving(self) -> None:
        """Stop the server."""
        self.python_logger.info("Stopping HTTP server")
        self.server.shutdown()

    class CameraHTTPRequestHandler(BaseHTTPRequestHandler):
        """A class that handles HTTP requests for the camera."""

        def logger(self) -> logging.Logger:
            """Return the logger for this class."""
            return logging.getLogger("HTTPRequestHandler")

        def check_auth(self) -> bool:
            """Check if the request is authorized."""
            if self.server.auth is None or self.server.auth == self.headers.get(
                "authorization"
            ):
                return True
            else:
                self.send_response(401)
                self.send_header("WWW-Authenticate", "Basic")
                self.end_headers()
                return False

        def send_jpeg(self, output: StreamingOutput) -> None:
            """Send a JPEG image."""
            with output.condition:
                output.condition.wait()
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", len(output.frame))
                self.end_headers()
                self.wfile.write(output.frame)

        def do_GET(self) -> None:
            """Handle a GET request."""
            if self.path == "/cam.mjpg":
                if self.check_auth():
                    output = self.server.cam.start_serving()
                    try:
                        self.send_response(200)
                        self.send_header(
                            "Content-Type", "multipart/x-mixed-replace; boundary=FRAME"
                        )
                        self.end_headers()

                        while not self.wfile.closed:
                            self.wfile.write(b"--FRAME\r\n")
                            self.send_jpeg(output)
                            self.wfile.write(b"\r\n")
                            self.wfile.flush()
                    except IOError as err:
                        self.logger().error(
                            "Exception while serving client %s: %s",
                            self.client_address,
                            err,
                        )
                    finally:
                        self.server.cam.stop_serving()
                        output = None
            else:
                self.send_error(404)
