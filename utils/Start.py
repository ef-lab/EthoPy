from utils.Interface import *
import time, os


class Welcome:
    def __init__(self, logger):
        self.logger = logger
        self.screen = Interface()
        self.state = ''
        self.animal = 0
        self.task = 0

    def setup(self):
        self.cleanup()
        self.screen.add_button(name='Animal %d' % self.animal, action=self.change_animal,
                                   x=250, y=80, w=200, h=100, color=(0, 0, 0), font_size=30)
        self.screen.add_button(name='Task %d' % self.task, action=self.change_task,
                               x=250, y=160, w=200, h=100, color=(0, 0, 0), font_size=30)
        self.screen.draw('%s %s' % (self.logger.ip, self.logger.setup), 0, 0, 150, 100, (128, 128, 128), size=15)
        self.screen.add_button(name='Start experiment', action=self.start_experiment,
                               x=250, y=330, w=200, h=100, color=(0, 128, 0))
        self.screen.add_button(name='Restart', action=self.reboot, x=700, y=340, w=100, h=70,
                               color=(50, 25, 25), font_size=15)
        self.screen.add_button(name='Power off', action=self.shutdown, x=700, y=410, w=100, h=70,
                               color=(50, 50, 25), font_size=15)

    def cleanup(self):
        self.screen.cleanup()
        self.state = ''
        self.exit = self.screen.add_button(name='X', action=self.exit, x=750, y=0, w=50, h=50,
                                           color=(25, 25, 25))

    def eval_input(self):
        if self.state == 'change_animal':
            self.cleanup()
            self.screen.draw('Enter animal ID', 0, 0, 400, 280)
            self.screen.add_numpad()
            button = self.screen.add_button(name='OK', x=150, y=250, w=100, h=100, color=(0, 128, 0))
            while not button.is_pressed() and not self.exit.is_pressed():
                time.sleep(0.2)
            if self.exit.is_pressed():
                return
            self.logger.update_animal_id(int(self.screen.numpad))
            self.setup()
        elif self.state == 'change_task':
            self.cleanup()
            self.screen.draw('Enter task idx', 0, 0, 400, 280)
            self.screen.add_numpad()
            button = self.screen.add_button(name='OK', x=150, y=250, w=100, h=100, color=(0, 128, 0))
            while not button.is_pressed() and not self.exit.is_pressed():
                time.sleep(0.2)
            if self.exit.is_pressed():
                return
            self.logger.update_task_idx(int(self.screen.numpad))
            self.setup()
        elif self.state == 'start_experiment':
            self.logger.update_state('running')
            self.screen.ts.stop()
        elif self.state == 'exit':
            self.logger.update_state('stopped')
            self.screen.exit()
        else:
            self.update_setup_info()
            time.sleep(0.2)

    def update_setup_info(self):
        animal = self.logger.get_setup_animal()
        task = self.logger.get_setup_task()
        if self.animal != animal or self.task != task:
            self.animal = animal
            self.task = task
            self.setup()

    def start_experiment(self):
        self.state = 'start_experiment'

    def exit(self):
        self.state = 'exit'

    def change_animal(self):
        self.state = 'change_animal'

    def change_task(self):
        self.state = 'change_task'

    def reboot(self):
        os.system('systemctl reboot -i')

    def shutdown(self):
        os.system('systemctl poweroff')

