from Stimulus import *
import time, os, types,sys
import numpy as np
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
import panda3d.core as core
from panda3d.core import *
from panda3d.core import ClockObject
#from direct.stdpy import threading2 as threading
from scipy import interpolate
from panda3d.core import loadPrcFileData
#loadPrcFileData("", "depth-bits 16\n")
#loadPrcFileData('', 'fullscreen true')
class Panda3D(Stimulus, ShowBase):
    """ This class handles the presentation of Objects with Panda3D"""

    def get_condition_tables(self):
        return []

    def setup(self):
        # setup parameters
        self.path = 'objects/'     # default path to copy local stimuli
        #self.set_intensity(self.params['intensity'])

        # store local copy of files
        if not os.path.isdir(self.path):  # create path if necessary
            os.makedirs(self.path)
        self.object_files = dict()
        for cond in self.conditions:
            for obj_id in cond['object_id']:
                object_info = self.logger.get_object(obj_id)
                filename = self.path + object_info['file_name']
                self.object_files[obj_id] = filename
                if not os.path.isfile(filename):
                    print('Saving %s ...' % filename)
                    object_info['object'].tofile(filename)

        ShowBase.__init__(self,fStartDirect=True, windowType=None)

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
            return

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

        self.objects = dict()
        for idx, obj in enumerate(self.curr_cond['object_id']):
            self.objects[obj] = Object(self, idx)

        #self.windowType = 'onscreen'
        #props = WindowProperties.getDefault()
        #props.setSize(800, 400)
        #props.setFullscreen(True)
        #self.openDefaultWindow(props)

    def init(self):
        self.isrunning = True
        self.timer.start()
        self.logger.log_stim()

    def present(self):
        self.taskMgr.step()
        if self.timer.elapsed_time() > self.curr_cond['stim_duration']*1000:
            self.isrunning = False

    def stop(self):
        for idx in self.curr_cond['object_id']:
            self.taskMgr.remove("Obj%s-Task" % idx)
            self.objects[idx].model.removeNode()
        self.isrunning = False

    def set_intensity(self, intensity=None):
        if intensity is None:
            intensity = self.params['intensity']
        cmd = 'echo %d > /sys/class/backlight/rpi_backlight/brightness' % intensity
        os.system(cmd)

    def close(self):
        """Close stuff"""
        self.destroy()


class Object(Panda3D):
    def __init__(self, env, idx):
        self.env = env
        self.model = self.env.loader.loadModel(self.env.object_files[self.env.curr_cond['object_id'][idx]])
        self.model.reparentTo(self.env.render)

        fov = self.env.camLens.get_fov()
        #fov =  [40]
        # define object time parameters
        self.rot_fun = self._make_lambda(self.env.curr_cond['obj_rot'][idx])
        self.tilt_fun = self._make_lambda(self.env.curr_cond['obj_tilt'][idx])
        self.yaw_fun = self._make_lambda(self.env.curr_cond['obj_yaw'][idx])
        self.z_fun = self._make_lambda(self.env.curr_cond['obj_mag'][idx],
                                       lambda x,t: 20/x)
        self.x_fun = self._make_lambda(self.env.curr_cond['obj_pos_x'][idx],
                                       lambda x,t: np.arctan(x * np.pi * fov[0] / 360) * self.z_fun(t))
        self.y_fun = self._make_lambda(self.env.curr_cond['obj_pos_y'][idx],
                                       lambda x,t: np.arctan(x * np.pi * fov[0] / 360) * self.z_fun(t))

        # set initial params
        self.model.setPos(self.x_fun(0), self.z_fun(0), self.y_fun(0))
        self.model.setHpr(self.rot_fun(0), self.tilt_fun(0), self.yaw_fun(0))

        # add task object
        self.env.taskMgr.add(self.objTask, "Obj%s-Task" % self.env.curr_cond['object_id'][idx])

    def objTask(self, task):
        t = task.time
        self.model.setHpr(self.rot_fun(t), self.tilt_fun(t), self.yaw_fun(t))
        self.model.setPos(self.x_fun(t), self.z_fun(t), self.y_fun(t))
        return Task.cont

    def _make_lambda(self, param, fun=lambda x,t: x):
        param = np.array([param]) if type(param) not in (list,tuple,dict, str, np.ndarray) else param
        idx = np.linspace(0, self.env.curr_cond['stim_duration'], param.size)
        return lambda t: np.interp(t, idx,fun(param, t))
        #return lambda t: interpolate.splev(t, interpolate.splrep(idx, fun(param, t)))
