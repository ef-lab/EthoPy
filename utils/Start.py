from utils.Interface import *
import time, os, socket

class Welcome:
    def __init__(self, logger):
        self.logger = logger
        self.screen = Interface()
        self.start()
        self.state = ''

    def setup(self):
        animal = self.logger.get_setup_animal()
        task = self.logger.get_setup_task()
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        self.clear()
        self.screen.draw('IP %s name %s' % (ip, hostname), 0, 0, 100, 100, (128, 128, 128), size=10)
        self.screen.add_button(name='Animal %d' % animal, action=self.change_animal, x=200, y=80, w=200, h=100,
                               color=(0, 0, 0))
        self.screen.add_button(name='Task %d' % task, action=self.change_task, x=200, y=160, w=200, h=100,
                               color=(0, 0, 0))
        self.screen.add_button(name='Start experiment', action=self.start_experiment, x=200, y=330, w=200, h=100,
                               color=(0, 128, 0))
        self.screen.add_button(name='Restart', action=self.reboot, x=700, y=340, w=100, h=70, color=(50, 25, 25),
                               font_size=10)
        self.screen.add_button(name='Power off', action=self.shutdown, x=700, y=410, w=100, h=70, color=(50, 50, 25),
                               font_size=10)

    def clear(self):
        self.screen.clear()
        self.exit = self.screen.add_button(name='X', action=self.exit, x=750, y=0, w=50, h=50,
                                           color=(25, 25, 25))

    def start(self):
        self.setup()
        while True:
            if self.state == 'change_animal':
                self.clear()
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
                self.clear()
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
                self.screen.exit()
            elif self.state == 'exit':
                self.logger.update_state('stopped')
                self.screen.exit()
            else:
                time.sleep(0.2)

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

