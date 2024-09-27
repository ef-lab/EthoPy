from Stimuli.Panda import *


@stimulus.schema
class Opto(Panda, dj.Manual):
    definition = """
    # This class handles the presentation of Opto pulses for optogenetic activity control
    -> StimCondition
    ---
    opt_duration             : int                     # duration (ms)
    opt_dutycycle            : int                     #  dutycycle
    """

    cond_tables = ['Opto', 'Panda', 'Panda.Object', 'Panda.Environment', 'Panda.Light', 'Panda.Movie']
    required_fields = ['obj_id', 'obj_dur', 'opt_duration']
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
                   'opt_dutycycle': 50,
                   'perspective': 0}

    def start(self):
        if not self.flag_no_stim:
            self.exp.interface.opto_stim(self.curr_cond['opt_duration'], self.curr_cond['opt_dutycycle'])
        super().start()
