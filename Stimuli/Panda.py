from core.Stimulus import *
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

    def store(self, obj_id, file_name, description=''):
        tuple = dict(obj_id=obj_id, description=description,
                     object=np.fromfile(file_name, dtype=np.int8), file_name=file_name)
        self.insert1(tuple, replace=True)


@stimulus.schema
class Panda(Stimulus, dj.Manual):
    definition = """
    # This class handles the presentation of Objects with Panda3D
    -> StimCondition
    """

    class Object(dj.Part):
        definition = """
        # object conditions
        -> Panda
        -> Objects
        ---
        obj_pos_x             : blob
        obj_pos_y             : blob
        obj_mag               : blob
        obj_rot               : blob
        obj_tilt              : blob 
        obj_yaw               : blob
        obj_delay             : int
        obj_dur               : int
        """

    class Environment(dj.Part):
        definition = """
        # object conditions
        -> Panda
        ---
        background_color      : tinyblob
        ambient_color         : tinyblob
        """

    class Light(dj.Part):
        definition = """
        # object conditions
        -> Panda
        light_idx             : tinyint
        ---
        light_color           : tinyblob
        light_dir             : tinyblob
        """

    cond_tables = ['Panda', 'Panda.Object', 'Panda.Environment', 'Panda.Light']
    required_fields = ['obj_id', 'obj_dur']
    default_key = {'background_color': (0, 0, 0),
                   'ambient_color': (0.1, 0.1, 0.1, 1),
                   'light_idx': [[1, 2]],
                   'light_color': (np.array([0.7, 0.7, 0.7, 1]), np.array([0.2, 0.2, 0.2, 1])),
                   'light_dir': (np.array([0, -20, 0]), np.array([180, -20, 0])),
                   'obj_pos_x': 0,
                   'obj_pos_y': 0,
                   'obj_mag': .5,
                   'obj_rot': 0,
                   'obj_tilt': 0,
                   'obj_yaw': 0,
                   'obj_delay': 0}

    object_files = dict()

    def setup(self, exp):
        self.logger = exp.logger
        self.exp = exp

        cls = self.__class__
        self.__class__ = cls.__class__(cls.__name__ + "ShowBase", (cls, ShowBase), {})

        self.isrunning = False
        self.timer = Timer()

        ShowBase.__init__(self, fStartDirect=True, windowType=False)
        self.props = core.WindowProperties()

        self.props.setSize(self.pipe.getDisplayWidth(), self.pipe.getDisplayHeight())
        #self.props.setFullscreen(True)
        self.props.setCursorHidden(True)
        self.win.requestProperties(self.props)

        info = self.pipe.getDisplayInformation()
        #print(info.getTotalDisplayModes())
        #print(info.getDisplayModeWidth(0), info.getDisplayModeHeight(0))
        #print(self.pipe.getDisplayWidth(), self.pipe.getDisplayHeight())

        self.graphicsEngine.openWindows()
        self.set_background_color(0, 0, 0)
        self.disableMouse()

        # Create Ambient Light
        self.ambientLight = core.AmbientLight('ambientLight')
        self.ambientLightNP = self.render.attachNewNode(self.ambientLight)
        self.render.setLight(self.ambientLightNP)

    def prepare(self, curr_cond, period='Trial'):
        self.curr_cond = curr_cond['stimulus'][period]
        if not self.curr_cond:
            self.isrunning = False
        self.background_color = self.curr_cond['background_color']

        # set background color
        self.set_background_color(*self.curr_cond['background_color'])

        # Set Ambient Light
        self.ambientLight.setColor(self.curr_cond['ambient_color'])

        # Set Directional Light
        self.lights = dict();  self.lightsNP = dict()
        for idx, light_idx in enumerate(iterable(self.curr_cond['light_idx'])):
            self.lights[idx] = core.DirectionalLight('directionalLight_%d' % idx)
            self.lightsNP[idx] = self.render.attachNewNode(self.lights[idx])
            self.render.setLight(self.lightsNP[idx])
            self.lights[idx].setColor(tuple(self.curr_cond['light_color'][idx]))
            self.lightsNP[idx].setHpr(*self.curr_cond['light_dir'][idx])

        # Set Object tasks
        self.objects = dict()
        for idx, obj in enumerate(iterable(self.curr_cond['obj_id'])):
            self.objects[idx] = Agent(self, self.get_cond('obj_', idx))

        self.flip(2)
        self.logger.log('StimCondition.Trial', dict(period=period, stim_hash=self.curr_cond['stim_hash']),
                        schema='stimulus')
        if not self.isrunning:
            self.timer.start()
            self.isrunning = True

    def present(self):
        self.flip()
        if 'obj_dur' in self.curr_cond and self.curr_cond['obj_dur'] < self.timer.elapsed_time():
            self.isrunning = False

    def flip(self, n=1):
        for i in range(0, n):
            self.taskMgr.step()

    def stop(self):
        for idx, obj in self.objects.items():
            obj.remove(obj.task)
        for idx, light in self.lights.items():
            self.render.clearLight(self.lightsNP[idx])

        self.flip(2) # clear double buffer
        self.isrunning = False

    def punish_stim(self):
        self.unshow((0, 0, 0))

    def reward_stim(self):
        self.unshow((0.5, 0.5, 0.5))

    def unshow(self, color=None):
        if not color: color = self.background_color
        self.set_background_color(*color)
        self.flip(2)

    def set_intensity(self, intensity=None):
        if not intensity: intensity = self.params['intensity']
        cmd = 'echo %d > /sys/class/backlight/rpi_backlight/brightness' % intensity
        os.system(cmd)

    def exit(self):
        self.destroy()

    def get_cond(self, cond_name, idx=0):
        return {k.split(cond_name, 1)[1]: v if type(v) is int or type(v) is float else v[idx]
                for k, v in self.curr_cond.items() if k.startswith(cond_name)}

    def make_conditions(self, exp, conditions):
        conditions = super().make_conditions(exp, conditions)

        # setup parameters
        self.path = os.path.dirname(os.path.abspath(__file__)) + '/objects/'     # default path to copy local stimuli

        # store local copy of files
        if not os.path.isdir(self.path):  # create path if necessary
            os.makedirs(self.path)
        for cond in conditions:
            if not 'obj_id' in cond: continue
            for obj_id in iterable(cond['obj_id']):
                object_info = (Objects() & ('obj_id=%d' % obj_id)).fetch1()
                filename = self.path + object_info['file_name']
                self.object_files[obj_id] = filename
                if not os.path.isfile(filename):
                    print('Saving %s ...' % filename)
                    object_info['object'].tofile(filename)
        return conditions


class Agent(Panda):
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
        param = (iterable(param))
        idx = np.linspace(0, self.duration/1000, param.size)
        return lambda t: np.interp(t, idx, fun(param, t))

