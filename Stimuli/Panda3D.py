from Stimulus import *
import os
import numpy as np
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
import panda3d.core as core
from utils.Timer import *


@stimulus.schema
class Objects(dj.Lookup):
    definition = """
    # object information
    obj_id               : int                          # object ID
    ---
    description          : varchar(256)                 # description
    object=null          : longblob                     # 3d file
    file_name=null       : varchar(255)   
    """

    
@stimulus.schema
class Panda3D(Stimulus, ShowBase, dj.Manual):
    definition = """
    # This class handles the presentation of Objects with Panda3D
    cond_hash            : char(24)                     # unique condition hash
    """

    class Object(dj.Part):
        definition = """
        # object conditions
        -> Panda3D
        -> stimuli.Objects
        ---
        obj_pos_x             : blob
        obj_pos_y             : blob
        obj_mag               : blob
        obj_rot               : blob
        obj_tilt              : blob
        obj_yaw               : blob
        obj_delay             : blob
        obj_dur               : blob
        """

    class Lights(dj.Part):
        definition = """
        # object conditions
        -> Panda3D
        ---
        background_color      : tinyblob
        ambient_color         : tinyblob
        direct1_color         : tinyblob
        direct1_dir           : tinyblob
        direct2_color         : tinyblob
        direct2_dir           : tinyblob
        """

    class Trial(dj.Part):
        definition = """
        # Stimulus onset timestamps
        -> exp.Trial
        -> Panda3D
        ---
        start_time           : int                          # start time from session start (ms)
        end_time             : int                          # end time from session start (ms)
        """

    def get_cond_tables(self):
        return ['ObjectCond']

    def setup(self):
        # setup parameters
        self.path = os.path.dirname(os.path.abspath(__file__)) + '/objects/'     # default path to copy local stimuli
        self.set_intensity(self.params['intensity'])

        # store local copy of files
        if not os.path.isdir(self.path):  # create path if necessary
            os.makedirs(self.path)
        self.object_files = dict()
        for cond in self.conditions:
            for obj_id in cond['obj_id']:
                object_info = (Objects() & ('obj_id=%d' % obj_id)).fetch1()
                filename = self.path + object_info['file_name']
                self.object_files[obj_id] = filename
                if not os.path.isfile(filename):
                    print('Saving %s ...' % filename)
                    object_info['object'].tofile(filename)

        ShowBase.__init__(self, fStartDirect=True, windowType=None)
        props = core.WindowProperties()
        props.setCursorHidden(True)
        self.win.requestProperties(props)
        self.set_background_color(0, 0, 0)
        self.disableMouse()

        # Create Ambient Light
        self.ambientLight = core.AmbientLight('ambientLight')
        self.ambientLightNP = self.render.attachNewNode(self.ambientLight)
        self.render.setLight(self.ambientLightNP)

        # Directional light 01
        self.directionalLight1 = core.DirectionalLight('directionalLight1')
        self.directionalLight1NP = self.render.attachNewNode(self.directionalLight1)
        self.render.setLight(self.directionalLight1NP)

        # Directional light 02
        self.directionalLight2 = core.DirectionalLight('directionalLight2')
        self.directionalLight2NP = self.render.attachNewNode(self.directionalLight2)
        self.render.setLight(self.directionalLight2NP)

    def prepare(self):
        self._get_new_cond()
        if not self.curr_cond:
            self.isrunning = False
        self.background_color = self.curr_cond['background_color']

        # set background color
        self.set_background_color(self.curr_cond['background_color'][0],
                                  self.curr_cond['background_color'][1],
                                  self.curr_cond['background_color'][2])

        # Set Ambient Light
        self.ambientLight.setColor(self.curr_cond['ambient_color'])

        # Directional light 01
        self.directionalLight1.setColor(self.curr_cond['direct1_color'])
        self.directionalLight1NP.setHpr(self.curr_cond['direct1_dir'][0],
                                        self.curr_cond['direct1_dir'][1],
                                        self.curr_cond['direct1_dir'][2])
        # Directional light 02
        self.directionalLight2.setColor(self.curr_cond['direct2_color'])
        self.directionalLight2NP.setHpr(self.curr_cond['direct2_dir'][0],
                                        self.curr_cond['direct2_dir'][1],
                                        self.curr_cond['direct2_dir'][2])
        self.flip(2)

    def start(self, period=None):
        self.objects = dict()
        if period:
            selected_obj = [p == period for p in self.curr_cond['obj_period']]
        else:
            period = 'Trial'
            selected_obj = [True for p in self.curr_cond['obj_id']]
        for idx, obj in enumerate(self.curr_cond['obj_id']):
            if not selected_obj[idx]:
                continue
            self.objects[idx] = Object(self, self.get_cond('obj_', idx))
        self.logger.log('StimOnset', dict(period=period))
        if not self.isrunning:
            self.timer.start()
            self.isrunning = True

    def present(self):
        self.flip()
        if 'stim_duration' in self.curr_cond and self.curr_cond['stim_duration'] < self.timer.elapsed_time():
            self.isrunning = False

    def flip(self, n=1):
        for i in range(0, n):
            self.taskMgr.step()

    def stop(self):
        for idx, obj in self.objects.items():
            obj.remove(obj.task)
            self.flip(2) # clear double buffer
        self.isrunning = False

    def punish_stim(self):
        self.unshow((0, 0, 0))

    def reward_stim(self):
        self.unshow((0.5, 0.5, 0.5))

    def unshow(self, color=None):
        if not color: color = self.background_color
        self.set_background_color(color[0], color[1], color[2])
        self.flip(2)

    def set_intensity(self, intensity=None):
        if not intensity: intensity = self.params['intensity']
        cmd = 'echo %d > /sys/class/backlight/rpi_backlight/brightness' % intensity
        os.system(cmd)

    def close(self):
        self.destroy()

    def get_cond(self, cond_name, idx=0):
        return {k.split(cond_name, 1)[1]: v if type(v) is int or type(v) is float else v[idx]
                for k, v in self.curr_cond.items() if k.startswith(cond_name)}


class Object(Panda3D):
    def __init__(self, env, cond):
        self.env = env
        self.timer = Timer()
        self.duration = cond['dur']
        self.model = env.loader.loadModel(env.object_files[cond['id']])
        self.model.reparentTo(env.render)
        hfov = self.env.camLens.get_fov() * np.pi / 180 # half field of view in radians

        # define object time parameters
        self.rot_fun = self.time_fun(cond['rot'])
        self.tilt_fun = self.time_fun(cond['tilt'])
        self.yaw_fun = self.time_fun(cond['yaw'])
        self.z_fun = self.time_fun(cond['mag'], lambda x, t: 20/x)
        self.x_fun = self.time_fun(cond['pos_x'], lambda x, t: np.arctan(x * hfov[0]) * self.z_fun(t))
        self.y_fun = self.time_fun(cond['pos_y'], lambda x, t: np.arctan(x * hfov[0]) * self.z_fun(t))

        # add task object
        self.name = "Obj%s-Task" % cond['id']
        self.task = self.env.taskMgr.doMethodLater(cond['delay']/1000, self.objTask, self.name)

    def objTask(self, task):
        t = self.timer.elapsed_time()/1000
        if t > self.duration/1000:
            self.remove(task)
            return
        self.model.setHpr(self.rot_fun(t), self.tilt_fun(t), self.yaw_fun(t))
        self.model.setPos(self.x_fun(t), self.z_fun(t), self.y_fun(t))
        return Task.cont

    def remove(self, task):
        task.remove()
        self.model.removeNode()

    def time_fun(self, param, fun=lambda x, t: x):
        param = np.array([param]) if type(param) != np.ndarray else param
        idx = np.linspace(0, self.duration/1000, param.size)
        return lambda t: np.interp(t, idx, fun(param, t))
