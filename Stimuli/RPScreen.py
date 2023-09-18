from core.Stimulus import *
from utils.Presenter import *

class RPScreen(Stimulus):

    def setup(self):
        self.fill_colors.set({'background': (0, 0, 0),
                              'start': (32, 32, 32),
                              'ready': (64, 64, 64),
                              'reward': (128, 128, 128),
                              'punish': (0, 0, 0)})

        self.Presenter = Presenter((self.monitor['resolution_x'], self.monitor['resolution_y']))
        self.Presenter.set_background_color(self.fill_colors.background)

    def fill(self, color=False):
        if not color:
            color = self.fill_colors.background
        if self.fill_colors.background: self.Presenter.fill(color)

    def exit(self):
        self.Presenter.quit()

