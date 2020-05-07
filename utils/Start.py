from utils.Interface import *


class Welcome:
    def __init__(self):
        self.screen = Interface()
        self.screen.clear()
        self.screen.draw('Place zero-weighted pad under the probe', 0, 0, 800, 280)
        button = self.screen.add_button(name='Set animal ID', action=self.change_animal, x=300, y=300, w=200, h=100)

    def start_experiment(self):
        pass

    def change_animal(self):
        print('Changing animal')

    def reboot(self):
        pass

    def shutdown(self):
        pass

