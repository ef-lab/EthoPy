from core.Stimulus import *
import os
import numpy as np
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
import panda3d.core as core
from utils.Timer import *
#from pandac.PandaModules import *
#ConfigVariableBool('fullscreen').setValue(1)
from panda3d.core import ConfigVariableManager


from pandac.PandaModules import loadPrcFileData
loadPrcFileData('', 'fullscreen 0')
loadPrcFileData('', 'undecorated 1')
loadPrcFileData('', 'win-origin 1860 -1')
loadPrcFileData('', 'win-size 1000 1000')
loadPrcFileData('', 'win-unexposed-draw 1')

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
        obj_period=Trial      : varchar(16)
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
        direct1_color         : tinyblob
        direct1_dir           : tinyblob
        direct2_color         : tinyblob
        direct2_dir           : tinyblob
        """

    cond_tables = ['Panda', 'Panda.Object', 'Panda.Environment']
    required_fields = ['obj_id', 'obj_dur']
    default_key = {'background_color': (0.1, 0.1, 0.1),
                   'ambient_color': (0.1, 0.1, 0.1, 1),
                   'direct1_color': (0.7, 0.7, 0.7, 1),
                   'direct1_dir': (0, -20, 0),
                   'direct2_color': (0.2, 0.2, 0.2, 1),
                   'direct2_dir': (180, -20, 0),
                   'obj_pos_x': 0,
                   'obj_pos_y': 0,
                   'obj_mag': .5,
                   'obj_rot': 0,
                   'obj_tilt': 0,
                   'obj_yaw': 0,
                   'obj_delay': 0,
                   'obj_period': 'Trial'}

    def setup(self, logger, conditions):
        cls = self.__class__
        self.__class__ = cls.__class__(cls.__name__ + "ShowBase", (cls, ShowBase), {})

        self.logger = logger
        self.isrunning = False
        self.timer = Timer()

        # setup parameters
        self.path = os.path.dirname(os.path.abspath(__file__)) + '/objects/'     # default path to copy local stimuli

        # store local copy of files
        if not os.path.isdir(self.path):  # create path if necessary
            os.makedirs(self.path)
        self.object_files = dict()
        for cond in conditions:
            if not 'obj_id' in cond: continue
            for obj_id in cond['obj_id']:
                object_info = (Objects() & ('obj_id=%d' % obj_id)).fetch1()
                filename = self.path + object_info['file_name']
                self.object_files[obj_id] = filename
                if not os.path.isfile(filename):
                    print('Saving %s ...' % filename)
                    object_info['object'].tofile(filename)

        print('Starting Showbase')
        time.sleep(2)
        ShowBase.__init__(self, fStartDirect=True, windowType=False)
        print('Done!')
        time.sleep(2)
        #props = core.WindowProperties()
        #props.setFullscreen(True)
        #props.setSize(2560, 1840)
        #props.setUndecorated(True)
        #props.setCursorHidden(True)
        #props.set_origin(1680,0)
        #self.win.requestProperties(props)

        self.openMainWindow()
        wp = core.WindowProperties()
        wp.setFullscreen(1)
        self.win.requestProperties(wp)
        self.graphicsEngine.openWindows()

        #self.graphicsEngine.openWindows()
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

    def prepare(self, curr_cond):
        self.curr_cond = curr_cond
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
            self.objects[idx] = Agent(self, self.get_cond('obj_', idx))
        self.logger.log('StimCondition.Trial', dict(period=period,stim_hash=self.curr_cond['stim_hash']), schema='stimulus')
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

    def exit(self):
        self.shutdown()
        self.graphicsEngine.removeAllWindows()
        self.destroy()

    def get_cond(self, cond_name, idx=0):
        return {k.split(cond_name, 1)[1]: v if type(v) is int or type(v) is float else v[idx]
                for k, v in self.curr_cond.items() if k.startswith(cond_name)}


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
        param = np.array([param]) if type(param) != np.ndarray else param
        idx = np.linspace(0, self.duration/1000, param.size)
        return lambda t: np.interp(t, idx, fun(param, t))
