from core.Stimulus import *
from utils.Timer import *


@stimulus.schema
class VROdors(Stimulus, dj.Manual):
    definition = """
    # vr conditions
    -> StimCondition
    """

    class Source(dj.Part):
        definition = """
        # odor conditions
        -> VROdors
        -> stimulus.Odorants
        ---
        extiction_factor     : float    
        delivery_port        : int                      # delivery idx for channel mapping
        odor_x               : tinyint
        odor_y               : tinyint
        """

    cond_tables = ['VROdors', 'VROdors.Source']
    required_fields = ['odorant_id', 'delivery_port', 'odor_x', 'odor_y']
    default_key = {'extiction_factor': 1}

    def start(self):
        self.exp.interface.start_odor(0)
        self.logger.log('StimCondition.Trial', dict(period=self.period, stim_hash=self.curr_cond['stim_hash']),
                        schema='stimulus')
        self.isrunning = True
        self.time.start()

    def loc2odor(self, x, y):
        odors_x = np.array(self.curr_cond['odor_x'])
        odors_y = np.array(self.curr_cond['odor_y'])
        mx = max(self.curr_cond['x_max'], self.curr_cond['y_max'])
        extiction_factors = np.array(self.curr_cond['extiction_factor'])
        x_dist = (np.abs(odors_x - x) / mx)
        y_dist = (np.abs(odors_y - y) / mx)
        return (1 - ((x_dist ** 2 + y_dist ** 2) / 2) ** .5) ** extiction_factors * 100

    def present(self):
        x, y, theta, tmst = self.beh.get_position()
        odor_dutycycles = self.loc2odor(x, y)
        self.exp.interface.update_odor(odor_dutycycles[np.array(self.curr_cond['delivery_port']) - 1])

    def stop(self):
        self.exp.interface.stop_odor()
        self.isrunning = False
