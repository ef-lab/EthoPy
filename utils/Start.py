"""
Graphical user interface when an experiment starts
"""

import pygame
import pygame_menu

from typing import Union, List

import os

class PyWelcome():
    def __init__(self, logger)->None:
        
        self.logger = logger

        self.SCREEN_WIDTH = 800
        self.SCREEN_HEIGHT = 480
        pygame.init()
        if self.logger.is_pi:
            self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        
        # Configure self.theme
        self.theme = pygame_menu.themes.THEME_DARK.copy()
        self.theme.background_color = (0, 0, 0)
        self.theme.title_background_color = (43, 43, 43)
        self.theme.title_font_size = 35
        self.theme.widget_alignment = pygame_menu.locals.ALIGN_CENTER
        self.theme.widget_font_color = (255, 255, 255)
        self.theme.widget_font_size = 30
        self.theme.widget_padding = 0

        # variables
        self.task_id = self.logger.get_setup_info('task_idx')
        self.animal_id = self.logger.get_setup_info('animal_id')
        self.weight = ''
        self.change_var = ''
        

        self.setup_menus()
        self.mainloop()

    def setup_menus(self) -> None:
        self.animal_menu = self.create_animal()
        self.task_menu = self.create_task()
        self.weight_menu = self.create_weight()
        self.main_menu = self.create_main()

    def mainloop(self) -> None:
        """
        App mainloop.

        :param test: Test status
        """
        while self.logger.setup_status != 'running' and self.logger.setup_status != 'exit':
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    exit()

            if self.main_menu.is_enabled():
                self.main_menu.update(events)
                self.main_menu.draw(self.screen)

            pygame.display.update()
            pygame.time.wait(10)
            self.logger.ping()

        pygame_menu.events.CLOSE
        if pygame.get_init():
            pygame.mouse.set_visible(1)
            pygame.display.quit()
            
    def create_main(self) -> 'pygame_menu.Menu':
        menu = pygame_menu.Menu('EthoPy',
                                self.SCREEN_WIDTH,
                                self.SCREEN_HEIGHT,
                                center_content=False,
                                mouse_motion_selection=True,
                                onclose=pygame_menu.events.EXIT,
                                overflow=False,
                                theme=self.theme,
                                )
        
        menu.add.label(
            f'ip: {self.logger.get_ip()}, setup: {self.logger.setup}',
            font_size=15,
            align=pygame_menu.locals.ALIGN_LEFT,
        ).translate(5, 10)

        menu.add.button(
            f'Animal id: {self.animal_id}',
            self.animal_menu,
            align=pygame_menu.locals.ALIGN_LEFT,
            float=True,
            padding = (5,10,5,10),
            background_color = (0, 15, 15)
        ).translate(300, 40)

        menu.add.button(
            f'Task id: {self.task_id}',
            self.task_menu,
            align=pygame_menu.locals.ALIGN_LEFT,
            float=True,
            padding = (5,10,5,10),
            background_color = (0, 15, 15)
        ).translate(300, 130)

        menu.add.button(
            'Start experiment',
            lambda: self.start_experiment(),
            align=pygame_menu.locals.ALIGN_LEFT,
            float=True,
            padding = (10,15,10,15),
            background_color = (0, 153, 0),
            font_size=35,
        ).translate(250, 260)

        menu.add.button(
            'Restart',
            self.reboot,
            align=pygame_menu.locals.ALIGN_LEFT,
            float=True,
            padding = (5,23,5,30),
            background_color = (128, 128, 128)
        ).translate(630, 290)

        menu.add.button(
            'Weight',
            self.weight_menu,
            align=pygame_menu.locals.ALIGN_LEFT,
            float=True,
            padding = (10,20,10,20),
            background_color = (128, 128, 128)
        ).translate(10, 310)

        menu.add.button(
            'Power off',
            self.shutdown,
            align=pygame_menu.locals.ALIGN_LEFT,
            float=True,
            background_color = (255, 0, 0),
            padding = (5,10,5,10),
        ).translate(630, 350)

        return menu

    def create_animal(self):
        menu_animal = pygame_menu.Menu('',
                                self.SCREEN_WIDTH,
                                self.SCREEN_HEIGHT,
                                center_content=False,
                                onclose=pygame_menu.events.EXIT,
                                theme=self.theme,
                                )
        menu_animal.add.label(
            'Select Animal id: ',
            font_size=20,
        )
        self.curr_animal=''
        menu_animal.add.vertical_margin(5)
        # Add the layout
        self.animal_screen = menu_animal.add.label('', background_color=None, margin=(10, 0),
                                        selectable=True, selection_effect=None)
        menu_animal = self.add_num_pad(menu_animal, self.log_animal_id, self.animal_screen)

        return menu_animal

    def create_weight(self):
        menu_weight = pygame_menu.Menu('',
                                self.SCREEN_WIDTH,
                                self.SCREEN_HEIGHT,
                                center_content=False,
                                onclose=pygame_menu.events.EXIT,
                                theme=self.theme,
                                )
        menu_weight.add.label(
            'Enter animal weight: ',
            font_size=20,
        )
        self.curr_weight=''
        menu_weight.add.vertical_margin(5)
        self.weight_screen = menu_weight.add.label('', background_color=None, margin=(10, 0),
                                        selectable=True, selection_effect=None)
        menu_weight = self.add_num_pad(menu_weight, self.log_animal_weight, self.weight_screen)


        return menu_weight

    def create_task(self):
        menu_task = pygame_menu.Menu('', 
                                self.SCREEN_WIDTH, 
                                self.SCREEN_HEIGHT,
                                center_content=False,
                                onclose=pygame_menu.events.EXIT,
                                theme=self.theme,
                                )
        menu_task.add.label(
            'Select Task id: ',
            font_size=20,
        )
        self.curr_task=''
        menu_task.add.vertical_margin(5)
        # Add the layout
        self.task_screen = menu_task.add.label('', background_color=None, margin=(10, 0),
                                        selectable=True, selection_effect=None)
        menu_task = self.add_num_pad(menu_task, self.log_task_id, self.task_screen)

        return menu_task

    def reboot(self):
        os.system('systemctl reboot -i')

    def shutdown(self):
        os.system('systemctl poweroff')
        
    def start_experiment(self):
        self.logger.update_setup_info({'status': 'running'})

    def close(self):
        pygame.mouse.set_visible(1)
        pygame.quit()

    def add_num_pad(self, menu, log_function, screen) -> 'pygame_menu.Menu':
        self.curr = ''
        self.menu = menu
        menu.add.vertical_margin(20)

        cursor = pygame_menu.locals.CURSOR_HAND

        # Add horizontal frames
        f1 = menu.add.frame_h(299, 54, margin=(5, 0))
        b1 = f1.pack(menu.add.button('1', lambda: self._press(1, screen), cursor=cursor))
        b2 = f1.pack(menu.add.button('2', lambda: self._press(2, screen), cursor=cursor), align=pygame_menu.locals.ALIGN_CENTER)
        b3 = f1.pack(menu.add.button('3', lambda: self._press(3, screen), cursor=cursor), align=pygame_menu.locals.ALIGN_RIGHT)
        menu.add.vertical_margin(5)

        f2 = menu.add.frame_h(299, 54, margin=(5, 0))
        b4 = f2.pack(menu.add.button('4', lambda: self._press(4, screen), cursor=cursor))
        b5 = f2.pack(menu.add.button('5', lambda: self._press(5, screen), cursor=cursor), align=pygame_menu.locals.ALIGN_CENTER)
        b6 = f2.pack(menu.add.button('6', lambda: self._press(6, screen), cursor=cursor), align=pygame_menu.locals.ALIGN_RIGHT)
        menu.add.vertical_margin(5)

        f3 = menu.add.frame_h(299, 54, margin=(5, 0))
        b7 = f3.pack(menu.add.button('7', lambda: self._press(7, screen), cursor=cursor))
        b8 = f3.pack(menu.add.button('8', lambda: self._press(8, screen), cursor=cursor), align=pygame_menu.locals.ALIGN_CENTER)
        b9 = f3.pack(menu.add.button('9', lambda: self._press(9, screen), cursor=cursor), align=pygame_menu.locals.ALIGN_RIGHT)
        menu.add.vertical_margin(5)

        f4 = menu.add.frame_h(299, 54, margin=(5, 0))
        delete = f4.pack(menu.add.button('<', lambda: self._press('<', screen), cursor=cursor), align=pygame_menu.locals.ALIGN_RIGHT)
        b0 = f4.pack(menu.add.button('0', lambda: self._press(0, screen), cursor=cursor), align=pygame_menu.locals.ALIGN_CENTER)
        dot = f4.pack(menu.add.button(' .', lambda: self._press('.', screen), cursor=cursor), align=pygame_menu.locals.ALIGN_LEFT)
        menu.add.vertical_margin(5)

        f5 = menu.add.frame_h(299, 54, margin=(5, 0))
        ok = f5.pack(menu.add.button('Ok', lambda: self._press('ok', screen, log_function), cursor=cursor), align=pygame_menu.locals.ALIGN_CENTER)

        
        # Add decorator for each object
        for widget in (b1, b2, b3, b4, b5, b6, b7, b8, b9, b0, ok, delete, dot):
            w_deco = widget.get_decorator()
            if widget != ok:
                w_deco.add_rectangle(-37, -27, 74, 54, (15, 15, 15))
                on_layer = w_deco.add_rectangle(-37, -27, 74, 54, (84, 84, 84))
            else:
                w_deco.add_rectangle(-37, -27, 74, 54, (38, 96, 103))
                on_layer = w_deco.add_rectangle(-37, -27, 74, 54, (40, 171, 187))
            w_deco.disable(on_layer)
            widget.set_attribute('on_layer', on_layer)

            def widget_select(sel: bool, wid: 'pygame_menu.widgets.Widget', _):
                """
                Function triggered if widget is selected
                """
                lay = wid.get_attribute('on_layer')
                if sel:
                    wid.get_decorator().enable(lay)
                else:
                    wid.get_decorator().disable(lay)

            widget.set_onselect(widget_select)
            widget.set_padding((2, 19, 0, 23))
            widget._keyboard_enabled = False

        return menu

    def log_animal_id(self, curr):
        try:
            self.animal_id = int(curr)
            self.logger.update_setup_info({'animal_id': self.animal_id})
            return True
        except ValueError:
            return (f"'{curr}' cannot convert int")

    def log_animal_weight(self, curr):
        try:
            self.weight = float(curr)
            self.logger.put(table='MouseWeight', tuple=dict(animal_id=self.logger.get_setup_info('animal_id'),
                                                        weight= self.weight), schema='mice')            
            return True
        except ValueError:
            return (f"'{curr}' cannot convert float")

    def log_task_id(self, curr):
        try:
            self.task_id = int(curr)
            self.logger.update_setup_info({'task_idx': self.task_id})
            return True
        except ValueError:
            return (f"'{curr}' cannot convert int")

    def _press(self, digit: Union[int, str], screen, log_function=None) -> None:
        """
        Press numpad digit.

        :param digit: Number or symbol
        """
        if digit == 'ok':
            if not self.curr=='':
                logged = log_function(self.curr)
                if logged==True:
                    self.curr=''
                    self.main_menu = self.create_main()
                    screen.set_title(self.curr)
                else:
                    screen.set_title(logged)
        elif digit=='<':
            self.curr = ''
            screen.set_title(str(''))
        else:
            if len(self.curr) <= 9:
                self.curr += str(digit)
            screen.set_title(self.curr)