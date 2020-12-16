from Stimulus import *


class VROdors(Stimulus):
    def get_cond_tables(self):
        return ['VRCond']

    def prepare(self):
        self._get_new_cond()

    def init(self):
        delivery_port = self.params['delivery_port']
        odor_id = self.params['odor_id']
        odor_dutycycle = self.curr_cond['duty_cycles']
        self.beh.present_odor(delivery_port, odor_id, odor_dutycycle)
        self.isrunning = True
        self.timer.start()

    def loc2odor(self, x, y):
        xmx = self.curr_cond['x_max']
        ymx = self.curr_cond['y_max']
        fun = self.curr_cond['fun']
        a = (np.abs(np.array([0, 0, xmx, xmx]) - x) / xmx) ** 2
        b = (np.abs(np.array([0, ymx, ymx, 0]) - y) / ymx) ** 2
        return (1 - ((a + b) / 2) ** .5) ** fun * 100

    def present(self):
        x, y = self.beh.get_location()
        odor_dutycycle = self.loc2odor(x, y)
        delivery_port = self.params['delivery_port']
        odor_id = self.params['odor_id']
        self.beh.update_odor(delivery_port, odor_id, odor_dutycycle)

    def stop(self):
        self.isrunning = False
