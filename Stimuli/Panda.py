import os
import time

import datajoint as dj
import numpy as np
import panda3d.core as core
from direct.showbase.Loader import Loader
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import CardMaker, ClockObject, NodePath, TextureStage

from core.Logger import stimulus
from core.Stimulus import StimCondition, Stimulus # import StimCondition need for the Panda class definition
from utils.helper_functions import iterable
from utils.Timer import Timer


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
        obj_occluder          : int
        perspective           : int
        """

    class Environment(dj.Part):
        definition = """
        # object conditions
        -> Panda
        ---
        background_color      : tinyblob
        ambient_color         : tinyblob
        """

    class Movie(dj.Part):
        definition = """
        # object conditions
        -> Panda
        ---
        movie_name            : char(8)                      # short movie title
        clip_number           : int                          # clip index
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

    cond_tables = ['Panda', 'Panda.Object', 'Panda.Environment', 'Panda.Light', 'Panda.Movie']
    required_fields = ['obj_id', 'obj_dur']
    default_key = {'background_color': (0, 0, 0),
                   'ambient_color': (0.1, 0.1, 0.1, 1),
                   'light_idx': (1, 2),
                   'light_color': (np.array([0.7, 0.7, 0.7, 1]), np.array([0.2, 0.2, 0.2, 1])),
                   'light_dir': (np.array([0, -20, 0]), np.array([180, -20, 0])),
                   'obj_pos_x': 0,
                   'obj_pos_y': 0,
                   'obj_mag': .5,
                   'obj_rot': 0,
                   'obj_tilt': 0,
                   'obj_yaw': 0,
                   'obj_delay': 0,
                   'obj_occluder': 0,
                   'perspective': 0}

    object_files, is_recording = dict(), False

    def init(self, exp):
        super().init(exp)
        cls = self.__class__
        if "ShowBase" not in cls.__name__:
            self.__class__ = cls.__class__(cls.__name__ + "ShowBase", (cls, ShowBase), {})
        if self.logger.is_pi:
            self.fStartDirect = True
            self.windowType = None
            self.Fullscreen = True
        else:
            self.fStartDirect = False
            self.windowType = 'onscreen'
            self.Fullscreen = False

        self.path = self.logger.source_path + 'objects/'  # default path to copy local stimuli
        self.movie_path = self.logger.source_path + 'movies/'
        self.record_path = self.logger.source_path + 'recorded/'
        self.globalClock = ClockObject.getGlobalClock()
        self.fps = 30

        if not os.path.isdir(self.path): os.mkdir(self.path)
        if not os.path.isdir(self.movie_path): os.mkdir(self.movie_path)
        if self.is_recording and not os.path.isdir(self.record_path): os.mkdir(self.record_path)

        self.fill_colors.background_color = (0, 0, 0)

    def name(self):
        return 'Panda'

    def setup(self):
        ShowBase.__init__(self, fStartDirect=self.fStartDirect, windowType=self.windowType)
        self.props = core.WindowProperties()
        if self.monitor.fullscreen:
            self.props.setSize(self.pipe.getDisplayWidth(), self.pipe.getDisplayHeight())
            self.props.setFullscreen(self.Fullscreen)
        else:
            self.props.setSize(self.monitor.resolution_x, self.monitor.resolution_y)
        self.props.setCursorHidden(True)
        self.props.setUndecorated(True)
        self.win.requestProperties(self.props)
        self.graphicsEngine.openWindows()
        self.set_background_color(0, 0, 0)

        self.disableMouse()
        self.in_operation = False
        self.present_movie = False

        # Create Ambient Light
        self.ambientLight = core.AmbientLight('ambientLight')
        self.ambientLightNP = self.render.attachNewNode(self.ambientLight)
        self.render.setLight(self.ambientLightNP)
        self.set_taskMgr()

    def prepare(self, curr_cond, stim_period=''):
        self.flag_no_stim = False
        if stim_period == '':
            self.curr_cond = curr_cond
        elif stim_period not in curr_cond:
            self.flag_no_stim = True
            return
        else: 
            self.curr_cond = curr_cond[stim_period]
        
        self.period = stim_period

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

        if 'movie_name' in self.curr_cond:
            self.present_movie = True
            loader = Loader(self)
            file_name = self.get_clip_info(self.curr_cond, 'file_name')
            self.mov_texture = loader.loadTexture(self.movie_path + file_name[0])
            cm = CardMaker("card")
            tx_scale = self.mov_texture.getTexScale()
            cm.setFrame(-1, 1, -tx_scale[1]/tx_scale[0], tx_scale[1]/tx_scale[0])
            self.movie_node = NodePath(cm.generate())
            self.movie_node.setTexture(self.mov_texture, 1)
            self.movie_node.setPos(0, 100, 0)
            self.movie_node.setTexScale(TextureStage.getDefault(), self.mov_texture.getTexScale())
            self.movie_node.setScale(48)
            self.movie_node.reparentTo(self.render)

    def start(self):
        if self.flag_no_stim: return
        self.fill()
        if not self.in_operation:
            self.timer.start()
            self.in_operation = True

        self.log_start()
        if self.present_movie: self.mov_texture.play()
        for idx, obj in enumerate(iterable(self.curr_cond['obj_id'])):
            self.objects[idx].run()
        self.flip(2)
        self.start_recording()

    def present(self):
        self.flip()
        if 'obj_dur' in self.curr_cond and self.curr_cond['obj_dur'] < self.timer.elapsed_time():
            self.in_operation = False

    def flip(self, n=1):
        for i in range(0, n):
            self.taskMgr.step()

    def stop(self):
        if self.flag_no_stim: return
        for idx, obj in self.objects.items():
            obj.remove(obj.task)
        for idx, light in self.lights.items():
            self.render.clearLight(self.lightsNP[idx])
        if self.present_movie:
            self.mov_texture.stop()
            self.movie_node.removeNode()
            self.present_movie = False
        self.render.clearLight

        self.stop_recording()
        self.flip(2) # clear double buffer
        self.log_stop()
        self.in_operation = False

    def fill(self, color=None):
        if not color: color = self.curr_cond['background_color']
        self.set_background_color(*color)
        self.flip(2)

    def close(self):
        pass

    def exit(self):
        self.destroy()
        if self.is_recording: self.create_movies()

    def record(self):
        self.is_recording = True

    def start_recording(self):
        if self.is_recording:
            self.record_task = self.movie(namePrefix=self.record_path + '/trial' + str(self.exp.curr_trial) + '_frame',
                                          duration=self.curr_cond['obj_dur'], fps=self.fps, format='png')
            self.globalClock.setMode(ClockObject.MLimited)
            self.globalClock.setFrameRate(self.fps)

    def stop_recording(self):
        if self.is_recording:
            self.taskMgr.remove(self.record_task)

    def create_movies(self):
        import glob
        import os
        print('creating movies..')
        for itrial in range(1, self.exp.curr_trial + 1):
            name = self.record_path + 'trial' + str(itrial) + '_frame_*.png'
            output_name = self.record_path + str(self.exp.logger.trial_key['animal_id']) + '_' + \
                          str(self.exp.logger.trial_key['session']) + '_trial' + str(itrial) + '.mov'
            print(output_name)
            os.system("ffmpeg -framerate " + str(self.fps) + " -pattern_type glob -i " + f'"{name}"'
                      + " -loglevel quiet -c:v libx264 -pix_fmt gray -crf 5 " + f'"{output_name}"')

        for f in glob.glob(self.record_path + '*.png'):
            os.remove(f)

    def get_cond(self, cond_name, idx=0):
        return {k.split(cond_name, 1)[1]: v if type(v) is int or type(v) is float else v[idx]
                for k, v in self.curr_cond.items() if k.startswith(cond_name)}

    def make_conditions(self, conditions):
        conditions = super().make_conditions(conditions)

        # store local copy of files
        if not os.path.isdir(self.path):  # create path if necessary
            os.makedirs(self.path)
        for cond in conditions:
            if 'movie_name' in cond:
                file = self.exp.logger.get(schema='stimulus', table='Movie.Clip', key=cond, fields=('file_name',))
                filename = self.movie_path + file[0]
                if not os.path.isfile(filename):
                    print('Saving %s' % filename)
                    clip = self.exp.logger.get(schema='stimulus', table='Movie.Clip', key=cond, fields=('clip',))
                    clip[0].tofile(filename)
            if not 'obj_id' in cond: continue
            for obj_id in iterable(cond['obj_id']):
                object_info = self.exp.logger.get(schema='stimulus', table='Objects', key={'obj_id': obj_id})[0]
                filename = self.path + object_info['file_name']
                self.object_files[obj_id] = filename
                if not os.path.isfile(filename): print('Saving %s' % filename); object_info['object'].tofile(filename)
        return conditions

    def get_clip_info(self, key, *fields):
        return self.logger.get(schema='stimulus', table='Movie.Clip', key=key, fields=fields)

    def set_taskMgr(self):
        """
        Use this at the setup of pandas because for some reason the taskMgr the first time it 
        doesn't work properly. It needs time sleep between steps or to run many steps
        """
        self.set_background_color((0, 0, 0))
        for i in range(0, 2):
            time.sleep(0.1)
            self.taskMgr.step()

class Agent(Panda):
    def __init__(self, env, cond):
        self.cond = cond
        self.env = env
        self.timer = Timer()
        self.duration = cond['dur']
        hfov = self.env.camLens.get_fov() * np.pi / 180 # half field of view in radians
        # define object time parameters
        self.rot_fun = self.time_fun(cond['rot'])
        self.tilt_fun = self.time_fun(cond['tilt'])
        self.yaw_fun = self.time_fun(cond['yaw'])
        self.z_loc = 2
        if cond['occluder']: self.z_loc = 1.5
        self.x_fun = self.time_fun(cond['pos_x'], lambda x, t: np.arctan(x * hfov[0]) * self.z_loc)
        self.y_fun = self.time_fun(cond['pos_y'], lambda x, t: np.arctan(x * hfov[0]) * self.z_loc)
        self.scale_fun = self.time_fun(cond['mag'], lambda x, t: .15*x)
        # add task object
        self.name = "Obj%s-Task" % cond['id']

    def run(self):
        self.timer.start()
        self.model = self.env.loader.loadModel(self.env.object_files[self.cond['id']])
        self.model.reparentTo(self.env.render)
        if self.cond['occluder']:
            self.model.setLightOff()
            self.model.setColor(*self.env.curr_cond['background_color'])
        self.task = self.env.taskMgr.doMethodLater(self.cond['delay']/1000, self.objTask, self.name)

    def objTask(self, task):
        t = self.timer.elapsed_time()/1000
        if t > self.duration/1000:
            self.remove(task)
            return
        self.model.setHpr(self.rot_fun(t), self.tilt_fun(t), self.yaw_fun(t))
        self.model.setPos(self.x_fun(t), self.z_loc, self.y_fun(t))
        self.model.setScale(self.scale_fun(t))

        return Task.cont

    def remove(self, task):
        task.remove()
        self.model.removeNode()

    def time_fun(self, param, fun=lambda x, t: x):
        param = (iterable(param))
        idx = np.linspace(0, self.duration/1000, param.size)
        return lambda t: np.interp(t, idx, fun(param, t))

