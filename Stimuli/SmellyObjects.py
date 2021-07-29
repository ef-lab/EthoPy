from Stimuli.Panda import *


class SmellyObjects(Panda):
    """ This class handles the presentation of Objects (Panda) and Olfactory stimuli"""

    cond_tables = ['Olfactory', 'Olfactory.Channel', 'Panda', 'Panda.Object', 'Panda.Environment']
    required_fields = []
    default_key = {'dutycycle': 0,
                   'odor_duration': 0,
                   'obj_dur': 0,
                   'background_color': (0, 0, 0),
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
                   'obj_delay': 0}

    def start(self):
        delivery_port = self.curr_cond['delivery_port']
        odor_id = self.curr_cond['odorant_id']
        odor_dur = self.curr_cond['odor_duration']
        odor_dutycycle = self.curr_cond['dutycycle']
        super().start()
        self.exp.interface.give_odor(delivery_port, odor_id, odor_dur, odor_dutycycle)
        self.timer.start()
