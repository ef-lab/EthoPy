import time
from importlib import import_module

import pygame

from core.Experiment import *

try:
    import pygame_menu

    IMPORT_PYGAME_MENU = True
except:
    IMPORT_PYGAME_MENU = False


class Experiment:
    """_summary_
    I created a main menu where every time i want to move to new one a clean it
    and i render the new components

    Menu order:
    1. pressure menu: define the air pressure in PSI
    The next menus run in loop for all the number of pulses
    2. a menu to check that pads has been placed under the ports
    3. run the pulses on every port
    4. port weight menu to define the weight in every port
    """

    def __init__(self):
        # self.interface = None
        self.params = None
        self.logger = None
        self.sync = False
        self.cal_idx = 0
        self.msg = ""
        self.pulse = 0
        self.screen_width = 800
        self.screen_height = 480
        self.ports = None
        self.port = None
        if not globals()["IMPORT_PYGAME_MENU"]:
            raise ImportError(
                "You need to install the pygame-menu: pip install pygame-menu"
            )

    def setup(self, logger, params):
        """setup _summary_

        _extended_summary_
        """
        self.params = params
        self.logger = logger
        interface_module = self.logger.get(
            schema="experiment",
            table="SetupConfiguration",
            fields=["interface"],
            key={"setup_conf_idx": self.params["setup_conf_idx"]},
        )[0]
        interface = getattr(
            import_module(f"Interfaces.{interface_module}"), interface_module
        )

        self.interface = interface(exp=self, callbacks=False)

        pygame.init()
        self.surface = pygame.display.set_mode((800, 480))
        if self.logger.is_pi:
            self.screen = pygame.display.set_mode(
                (self.screen_width, self.screen_height), pygame.FULLSCREEN
            )

        # Configure self.theme
        self.theme = pygame_menu.themes.THEME_DARK.copy()
        self.theme.background_color = (0, 0, 0)
        self.theme.title_background_color = (43, 43, 43)
        self.theme.title_font_size = 35
        self.theme.widget_alignment = pygame_menu.locals.ALIGN_CENTER
        self.theme.widget_font_color = (255, 255, 255)
        self.theme.widget_font_size = 30
        self.theme.widget_padding = 0

        self.menu = pygame_menu.Menu(
            "",
            self.screen_width,
            self.screen_height,
            center_content=False,
            mouse_motion_selection=True,
            onclose=None,
            overflow=False,
            theme=self.theme,
        )

        self.pressure = None
        self.curr = ""
        self.stop = False
        # Start with the pressure menu

        self.create_pressure_menu()
        self.run()

    def run(self) -> None:
        """
        Calibration mainloop.
        """

        # self.menu.mainloop(self.surface, disable_loop=test)
        while self.stop == False:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    exit()

            if self.menu.is_enabled():
                self.menu.update(events)
                self.menu.draw(self.surface)

            pygame.display.flip()

        pygame_menu.events.CLOSE

        if pygame.get_init():
            pygame.display.quit()

    def create_pressure_menu(self):
        """The First menu in Calibration where is definde the air pressure in PSI"""
        self.menu.clear()
        self.button_input("Enter air pressure (PSI)", self.create_pulsenum_menu)

    def create_pulsenum_menu(self):
        """Before start pulses show a label in screen to place a pad under the ports"""
        self.pressure = self.curr
        self.curr = ""
        if self.cal_idx < len(self.params["pulsenum"]):
            self.menu.clear()
            self.menu.add.label(
                "Place zero-weighted pad under the port", float=True, font_size=30
            ).translate(20, 80)
            self.menu.add.button(
                "OK",
                self.create_pulse_num,
                align=pygame_menu.locals.ALIGN_LEFT,
                float=True,
                padding=(10, 10, 10, 10),
                background_color=(0, 128, 0),
                font_size=30,
            ).translate(400, 140)
        else:
            self.exit()

    def create_pulse_num(self):
        """
        Display the pulses
        """
        self.pulse = 0
        msg = f"Pulse {self.pulse + 1}/{self.params['pulsenum'][self.cal_idx]}"
        self.menu.clear()
        pulses_label = self.menu.add.label(
            msg,
            float=True,
            label_id="pulses_label",
            font_size=40,
            background_color=(0, 15, 15),
        ).translate(0, 50)
        # Adds a function to the Widget to be executed each time the label is drawn.
        pulses_label.add_draw_callback(self.run_pulses)

    def run_pulses(self, widget, menu):
        """This function is executed each time the label is drawm

        Args:
            widget (_type_): The widget that uses the function
            menu (_type_): The current menu
        """
        if self.pulse < self.params["pulsenum"][self.cal_idx]:
            self.msg = f"Pulse {self.pulse + 1}/{self.params['pulsenum'][self.cal_idx]}"
            print("\r" + self.msg, end="")
            widget.set_title(self.msg)
            for port in self.params["ports"]:
                try:
                    self.interface.give_liquid(
                        port, self.params["duration"][self.cal_idx]
                    )
                    pass
                except Exception as error:
                    # ToDo update notes in control table
                    print(f"Error {error}")
                    self.exit()

                time.sleep(
                    self.params["duration"][self.cal_idx] / 1000
                    + self.params["pulse_interval"][self.cal_idx] / 1000
                )
            self.pulse += 1  # update trial
        else:
            print("\r" + self.msg, end="")
            self.cal_idx += 1
            self.ports = self.params["ports"].copy()
            self.create_port_weight()

    def create_port_weight(self):
        """A menu with numpad for defining the water in every port"""
        self.menu.clear()
        cal_idx = self.cal_idx - 1
        if self.params["save"]:
            self.menu.clear()
            if len(self.ports) != 0:
                if len(self.ports) != len(self.params["ports"]):
                    self.log_pulse_weight(
                        self.params["duration"][cal_idx],
                        self.port,
                        self.params["pulsenum"][cal_idx],
                        self.curr,
                        self.pressure,
                    )

                self.port = self.ports.pop(0)
                self.button_input(
                    f"Enter weight for port {self.port }", self.create_port_weight
                )
            else:
                self.log_pulse_weight(
                    self.params["duration"][cal_idx],
                    self.port,
                    self.params["pulsenum"][cal_idx],
                    self.curr,
                    self.pressure,
                )

                self.create_pulsenum_menu()
        else:
            self.create_pulsenum_menu()

    def exit(self):
        """exit _summary_

        exit function after the Experiment has finished
        """
        self.menu.clear()
        self.menu.add.label("Done calibrating!!", float=True, font_size=30).translate(
            20, 80
        )
        self.menu.draw(self.screen)
        pygame.display.flip()
        time.sleep(2)
        self.stop = True
        self.interface.cleanup()
        self.logger.update_setup_info({"status": "ready"})
        time.sleep(1)

    def button_input(self, message: str, _func):
        """button_input _summary_

        Create a label with a numpad

        Args:
            message (str): a string to display in as label
            _func (method): a method to run after the OK is pressed in the numpad
        """
        self.menu.add.label(
            message,
            font_size=25,
        )
        self.num_pad(_func)

    def num_pad(self, _func):
        """num_pad _summary_

        _extended_summary_

        Args:
            log_function (_type_): _description_
        """
        self.num_pad_disp = self.menu.add.label(
            "",
            background_color=None,
            margin=(10, 0),
            selectable=True,
            selection_effect=None,
        )
        self.menu.add.vertical_margin(10)
        cursor = pygame_menu.locals.CURSOR_HAND

        self.curr = ""

        # Add horizontal frames
        f1 = self.menu.add.frame_h(299, 54, margin=(0, 0))
        b1 = f1.pack(self.menu.add.button("1", lambda: self._press(1), cursor=cursor))
        b2 = f1.pack(
            self.menu.add.button("2", lambda: self._press(2), cursor=cursor),
            align=pygame_menu.locals.ALIGN_CENTER,
        )
        b3 = f1.pack(
            self.menu.add.button("3", lambda: self._press(3), cursor=cursor),
            align=pygame_menu.locals.ALIGN_RIGHT,
        )
        self.menu.add.vertical_margin(5)

        f2 = self.menu.add.frame_h(299, 54, margin=(0, 0))
        b4 = f2.pack(self.menu.add.button("4", lambda: self._press(4), cursor=cursor))
        b5 = f2.pack(
            self.menu.add.button("5", lambda: self._press(5), cursor=cursor),
            align=pygame_menu.locals.ALIGN_CENTER,
        )
        b6 = f2.pack(
            self.menu.add.button("6", lambda: self._press(6), cursor=cursor),
            align=pygame_menu.locals.ALIGN_RIGHT,
        )
        self.menu.add.vertical_margin(5)

        f3 = self.menu.add.frame_h(299, 54, margin=(0, 0))
        b7 = f3.pack(self.menu.add.button("7", lambda: self._press(7), cursor=cursor))
        b8 = f3.pack(
            self.menu.add.button("8", lambda: self._press(8), cursor=cursor),
            align=pygame_menu.locals.ALIGN_CENTER,
        )
        b9 = f3.pack(
            self.menu.add.button("9", lambda: self._press(9), cursor=cursor),
            align=pygame_menu.locals.ALIGN_RIGHT,
        )
        self.menu.add.vertical_margin(5)

        f4 = self.menu.add.frame_h(299, 54, margin=(0, 0))
        delete = f4.pack(
            self.menu.add.button("<", lambda: self._press("<"), cursor=cursor),
            align=pygame_menu.locals.ALIGN_RIGHT,
        )
        b0 = f4.pack(
            self.menu.add.button("0", lambda: self._press(0), cursor=cursor),
            align=pygame_menu.locals.ALIGN_CENTER,
        )
        dot = f4.pack(
            self.menu.add.button(" .", lambda: self._press("."), cursor=cursor),
            align=pygame_menu.locals.ALIGN_LEFT,
        )
        self.menu.add.vertical_margin(5)

        f5 = self.menu.add.frame_h(299, 54, margin=(0, 0))
        ok = f5.pack(
            self.menu.add.button("OK", lambda: self._press("ok", _func), cursor=cursor),
            align=pygame_menu.locals.ALIGN_CENTER,
        )

        # Add decorator for each object
        for widget in (b1, b2, b3, b4, b5, b6, b7, b8, b9, b0, ok, delete, dot):
            w_deco = widget.get_decorator()
            if widget != ok:
                w_deco.add_rectangle(-37, -27, 74, 54, (15, 15, 15))
                on_layer = w_deco.add_rectangle(-37, -27, 74, 54, (84, 84, 84))
            else:
                w_deco.add_rectangle(-37, -27, 74, 54, (0, 128, 0))
                on_layer = w_deco.add_rectangle(-37, -27, 74, 54, (40, 171, 187))
            w_deco.disable(on_layer)
            widget.set_attribute("on_layer", on_layer)

            def widget_select(sel: bool, wid: "pygame_menu.widgets.Widget", _):
                """
                Function triggered if widget is selected
                """
                lay = wid.get_attribute("on_layer")
                if sel:
                    wid.get_decorator().enable(lay)
                else:
                    wid.get_decorator().disable(lay)

            widget.set_onselect(widget_select)
            widget.set_padding((2, 19, 0, 23))

    def _press(self, digit, _func=None) -> None:
        """
        Press numpad digit.

        :param digit: Number or symbol
        """
        if digit == "ok":
            if not self.curr == "":
                _func()
        elif digit == "<":
            self.curr = ""
            self.num_pad_disp.set_title(str(""))
        else:
            if len(self.curr) <= 9:
                self.curr += str(digit)
            self.num_pad_disp.set_title(self.curr)

    def log_pulse_weight(self, pulse_dur, port, pulse_num, weight=0, pressure=0):
        key = dict(setup=self.logger.setup, port=port, date=time.strftime("%Y-%m-%d"))
        self.logger.put(
            table="PortCalibration",
            tuple=key,
            schema="behavior",
            priority=5,
            ignore_extra_fields=True,
            validate=True,
            block=True,
            replace=False,
        )
        self.logger.put(
            table="PortCalibration.Liquid",
            schema="behavior",
            replace=True,
            ignore_extra_fields=True,
            tuple=dict(
                key,
                pulse_dur=pulse_dur,
                pulse_num=pulse_num,
                weight=weight,
                pressure=pressure,
            ),
        )
