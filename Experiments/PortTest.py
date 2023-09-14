import numpy
from Interfaces.RPPorts import RPPorts
import time
import pygame
import pygame_menu

class PortTest:
    def __init__(self, logger, params):
        self.params = params
        self.logger = logger
        self.sync = False
        self.interface = RPPorts(exp=self, callbacks=True)
        self.size = (800, 480)     # window size
        self.result = dict()
        self.total_pulses=0
        self.screen_width = 800
        self.screen_height = 480
        pygame.init()
        if self.logger.is_pi:
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height),
                                                pygame.FULLSCREEN)
        else:
            self.surface = pygame.display.set_mode((self.screen_width, self.screen_height))

        # Configure self.theme
        self.theme = pygame_menu.themes.THEME_DARK.copy()
        self.theme.background_color = (0, 0, 0)
        self.theme.title_background_color = (43, 43, 43)
        self.theme.title_font_size = 35
        self.theme.widget_alignment = pygame_menu.locals.ALIGN_CENTER
        self.theme.widget_font_color = (255, 255, 255)
        self.theme.widget_font_size = 30
        self.theme.widget_padding = 0

        self.menu = pygame_menu.Menu('',
                        self.screen_width,
                        self.screen_height,
                        center_content=False,
                        mouse_motion_selection=True,
                        onclose=None,
                        overflow=False,
                        theme=self.theme,
                        )

    def run(self):
        """ Lickspout liquid delivery test """
        print('Running port test')
        for port in self.params['ports']:
            self.total_pulses = 0
            self.result[port] = False
            tmst = self.logger.logger_timer.elapsed_time()
            for cal_idx in range(0, numpy.size(self.params['pulsenum'])):
                self.menu.clear()
                self.flip_frame()
                pulse = 0
                while pulse < self.params['pulsenum'][cal_idx] and not self.result[port]:
                    self.menu.clear(); self.flip_frame() 
                    msg = f"Pulse {pulse + 1}/{self.params['pulsenum'][cal_idx]}"
                    self.menu.add.label(
                        msg,
                        float=True,
                        label_id="pulses_label",
                        font_size=40,
                        background_color = (0, 15, 15)).translate(0, 50)
                    self.flip_frame()
                    print(msg)
                    self.interface.give_liquid(port, self.params['duration'][cal_idx])
                    time.sleep(self.params['duration'][cal_idx] / 1000 +\
                               self.params['pulse_interval'][cal_idx] / 1000)
                    pulse += 1  # update trial
                    self.total_pulses += 1
                    self.result[port] = self.get_response(tmst, port)
                if self.result[port]:
                    self.log_test(port, self.total_pulses, 'Passed')
                    break
            if not self.result[port]:
                self.log_test(port, self.total_pulses, 'Failed')
        self.menu.clear()
        self.menu.add.label(
                            msg,
                            float=True,
                            label_id="Done testing!",
                            font_size=40,
                            background_color = (0, 15, 15)).translate(0, 50)
        self.flip_frame()
        self.close()

    def close(self):
        self.interface.cleanup()
        self.logger.update_setup_info({'status': 'ready'})
        time.sleep(1)
        if pygame.get_init():
            pygame.display.quit()


    def flip_frame(self):
        """update the menu Gui"""
        self.menu.draw(self.screen)
        pygame.display.flip()

    def get_response(self, since=0, port=0):
        return self.interface.resp_tmst >= since and self.interface.response.port == port

    def log_test(self, port=0, pulses=0, result='Passed'):
        self.menu.clear()
        self.menu.add.label(
            f'Probe {port} {result}!',
            float=True,
            label_id="pulses_label",
            font_size=40,
            background_color = (0, 15, 15)).translate(0, 50)
        self.flip_frame()
        key = dict(setup=self.logger.setup, port=port, result=result, pulses=pulses, 
                   date=time.strftime("%Y-%m-%d"),timestamp=time.strftime("%Y-%m-%d %H:%M:%S"))
        self.logger.put(table='PortCalibration', tuple=key, schema='behavior', priority=5)
        self.logger.put(table='PortCalibration.Test',  schema='behavior', replace=True, tuple=key)
        time.sleep(1)
