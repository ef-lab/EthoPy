from Stimuli.Olfactory import *


@stimulus.schema
class VROdors(Stimulus, dj.Manual):
    definition = """
    # vr conditions
    -> StimCondition
    ---
    frequency           : int   # pulse frequency
    """

    class Source(dj.Part):
        definition = """
        # odor conditions
        -> VROdors
        -> Odorants
        ---
        extiction_factor     : float    
        delivery_port        : int                      # delivery idx for channel mapping
        odor_x               : tinyint
        odor_y               : tinyint
        """

    cond_tables = ['VROdors', 'VROdors.Source']
    required_fields = ['odorant_id', 'delivery_port', 'odor_x', 'odor_y']
    default_key = {'extiction_factor': 1, 'frequency': 10}

    def setup(self):
        super().setup()
        self.speaker_properties = self.logger.get(table='SetupConfiguration.Speaker', key=self.exp.params, as_dict=True)[0]

    def start(self):
        self.exp.interface.start_odor(self.curr_cond['delivery_port'],
                                      dutycycle=0, frequency=self.curr_cond['frequency'])
        self.log_start()
        self.in_operation = True
        self.timer.start()

    def loc2odor(self, x, y):
        odors_x = np.array(self.curr_cond['odor_x'])
        odors_y = np.array(self.curr_cond['odor_y'])
        mx = max(self.curr_cond['x_sz'], self.curr_cond['x_sz'])
        extiction_factors = np.array(self.curr_cond['extiction_factor'])
        x_dist = (np.abs(odors_x - x) / mx)
        y_dist = (np.abs(odors_y - y) / mx)
        return (1 - ((x_dist ** 2 + y_dist ** 2) / 2) ** .5) ** extiction_factors * 100

    def present(self):
        x, y, theta, tmst = self.exp.beh.get_position()
        odor_dutycycles = self.loc2odor(x, y)
        self.exp.interface.update_odor(odor_dutycycles)

    def ready_stim(self):
        self.exp.interface.give_sound(sound_freq=self.speaker_properties['sound_freq'],
                                      duration=self.speaker_properties['duration'],
                                      volume=self.speaker_properties['volume'])

    def stop(self):
        self.exp.interface.stop_odor()
        self.log_stop()
        self.in_operation = False
