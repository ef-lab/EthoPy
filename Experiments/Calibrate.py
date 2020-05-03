import pygame
from Probe import *


class Calibrate:
    def __init__(self, logger, params):
        self.params = params
        self.logger = logger
        self.size = (800, 480)     # window size

        # setup pygame
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        pygame.mouse.set_visible(0)
        pygame.display.toggle_fullscreen()

    def run(self):
        """ Lickspout liquid delivery calibration """
        valve = RPProbe(self.logger)
        print('Running calibration')
        pulse = 0
        font = pygame.font.SysFont("comicsansms", 100)
        while pulse < self.params.pulsenum:
            text = font.render('Pulse %d/%d' % (pulse + 1, self.params.pulsenum), True, (0, 128, 0))
            self.screen.fill((255, 255, 255))
            self.screen.blit(text, (self.size[1] / 4, self.size[1] / 2))
            self.flip()
            for probe in self.params.probes:
                valve.give_liquid(probe, self.params.duration, False)  # release liquid
            time.sleep(self.params.duration / 1000 + self.params.pulse_interval / 1000)  # wait for next pulse
            pulse += 1  # update trial
        if self.params.save:
            for probe in self.params.probes:
                self.logger.log_pulse_weight(self.params.duration, probe, self.params.pulsenum)  # insert
        self.screen.fill((255, 255, 255))
        self.screen.blit(font.render('Done calibrating', True, (0, 128, 0)), (self.size[1] / 4, self.size[1] / 2))
        self.flip()
        valve.cleanup()

    def flip(self):
        """ Main flip method"""
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()

