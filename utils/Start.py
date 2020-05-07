from utils.Interface import *
import time, os

class Welcome:
    def __init__(self, logger):
        self.logger = logger
        self.screen = Interface()
        self.start()

    def start(self):
        animal = self.logger.get_setup_animal()
        task = self.logger.get_setup_task()
        self.screen.clear()
        self.screen.draw('Animal %d \n task %d' % (animal, task), 200, 0, 400, 480)
        self.screen.add_button(name='Set animal ID', action=self.change_animal, x=0, y=0, w=100, h=240, color=(0, 0, 50))
        self.screen.add_button(name='Change Task', action=self.change_task, x=0, y=240, w=100, h=240, color=(0, 0, 50))
        self.screen.add_button(name='Start experiment', action=self.start_experiment, x=0, y=350, w=100, h=100, color=(0, 128, 0))
        self.screen.add_button(name='Restart', action=self.reboot, x=700, y=0, w=100, h=240, color=(50, 0, 0))
        self.screen.add_button(name='Power off', action=self.shutdown, x=700, y=240, w=100, h=240, color=(50, 0, 0))

    def start_experiment(self):
        self.logger.update_state('running')

    def exit(self):
        self.logger.update_state('stopped')

    def change_animal(self):
        self.screen.clear()
        self.screen.draw('Enter animal ID', 0, 0, 400, 280)
        self.screen.add_numpad()
        button = self.screen.add_button(name='OK', x=100, y=300, w=100, h=100, color=(0, 128, 0))
        while not button.is_pressed():
            time.sleep(0.2)
        self.logger.update_animal_id(int(self.screen.numpad))
        self.start()

    def change_task(self):
        self.screen.clear()
        self.screen.draw('Enter task idx', 0, 0, 400, 280)
        self.screen.add_numpad()
        button = self.screen.add_button(name='OK', x=100, y=300, w=100, h=100, color=(0, 128, 0))
        while not button.is_pressed():
            time.sleep(0.2)
        self.logger.update_task_idx(int(self.screen.numpad))
        self.start()

    def reboot(self):
        os.system('systemctl reboot -i')

    def shutdown(self):
        os.system('systemctl poweroff')

