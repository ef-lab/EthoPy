import pygame
from pygame.locals import *
from OpenGL.GL import *
import numpy as np


class Presenter():

    def __init__(self, logger, monitor, background_color=(0, 0, 0), photodiode=False, rec_fliptimes=False):
        global pygame
        if not pygame.get_init(): pygame.init()

        self.logger = logger
        if monitor.fullscreen:
            PROPERTIES = pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN | pygame.OPENGL
        else:
            PROPERTIES = pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.OPENGL
        self.screen = pygame.display.set_mode((monitor.resolution_x, monitor.resolution_y),
                                              PROPERTIES, display=monitor.screen_idx-1)
        pygame.display.init()
        pygame.mouse.set_visible(0)
        if photodiode:
            if photodiode == 'parity':
                # Encodes the flip even / dot in the flip amplitude
                self.phd_f = lambda x: float(float(x // 2) == x / 2)
                self.photodiode = True
            elif photodiode == 'flipcount':
                # Encodes the flip count (n) in the flip amplitude.
                # Every 32 sequential flips encode 32 21-bit flip numbers.
                # Thus each n is a 21-bit flip number: FFFFFFFFFFFFFFFFCCCCP
                # C = the position within F
                # F = the current block of 32 flips
                self.phd_f = lambda x: 0.5 * float(((x+1) & 1) * (2 - ((x+1) & (1 << (((np.int64(np.floor((x+1) / 2)) & 15) + 6) - 1)) != 0)))
                self.photodiode = True
            else:
                print(photodiode, ' method not implemented! Available methods: parity, flipcount')
                self.photodiode = False
        else:
            self.photodiode = False

        self.rec_fliptimes = rec_fliptimes
        if self.rec_fliptimes:
            self.fliptimes_dataset = self.logger.createDataset(dataset_name='fliptimes',
                                                               dataset_type=np.dtype([("flip_idx", np.double),
                                                                                      ("tmst", np.double)]))

        self.clock = pygame.time.Clock()
        self.set_background_color(background_color)
        self.flip_count = 0
        self.phd_size = 0.025  # default photodiode signal size in ratio of the X screen size

        self.info = pygame.display.Info()
        self.texID = glGenTextures(1)
        self.offscreen_surface = pygame.Surface((self.info.current_w, self.info.current_h))
        self.offscreen_surface.fill((self.background_color[0]*255,
                                     self.background_color[1]*255,
                                     self.background_color[2]*255))
        self.phd_size = (self.phd_size, self.phd_size * float(self.info.current_w/self.info.current_h))
        glViewport(0, 0, self.info.current_w, self.info.current_h)
        glDepthRange(0, 1)
        glMatrixMode(GL_PROJECTION)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glShadeModel(GL_SMOOTH)
        glClearColor(self.background_color[0], self.background_color[1], self.background_color[2], 0.0)
        glClearDepth(1.0)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glDepthFunc(GL_LEQUAL)
        glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        self.fill()

    def set_background_color(self, color):
        self.background_color = color
        glClearColor(color[0], color[1], color[2], 0.0)

    def render(self, surface):
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()
        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        surf = self._surfaceToTexture(surface)

        surf_ratio = surf.width/surf.height
        window_ratio = self.info.current_w/self.info.current_h

        if window_ratio > surf_ratio:
            x_scale = surf_ratio/window_ratio
            y_scale = 1
        else:
            x_scale = 1
            y_scale = window_ratio/surf_ratio

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex2f(-1*x_scale, 1*y_scale)
        glTexCoord2f(0, 1)
        glVertex2f(-1*x_scale, -1*y_scale)
        glTexCoord2f(1, 1)
        glVertex2f(1*x_scale, -1*y_scale)
        glTexCoord2f(1, 0)
        glVertex2f(1*x_scale, 1*y_scale)
        glEnd()
        self.flip()

    def draw_rect(self, rect, color):
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()
        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(self.background_color[0], self.background_color[1], self.background_color[2], 0.0)
        # draw rectangle
        glDisable(GL_TEXTURE_2D)
        glColor3fv(color)
        glRectf(rect[0], rect[1], rect[2], rect[3])
        self.flip()

    def fill(self, color=False):
        if not color:
            color = self.background_color
        self.offscreen_surface.fill((color[0]*255, color[0]*255, color[0]*255))
        self.render(self.offscreen_surface)

    def flip(self):
        self.flip_count += 1
        self._encode_photodiode()
        pygame.display.flip()
        if self.rec_fliptimes:
            self.fliptimes_dataset.append('fliptimes', [self.flip_count, self.logger.logger_timer.elapsed_time()])
        for event in pygame.event.get():
            if event.type == QUIT: pygame.quit()

    def make_surface(self, array):
        return pygame.surfarray.make_surface(array)

    def tick(self, fps):
        self.clock.tick(fps)

    def _surfaceToTexture(self, pygame_surface):
        rgb_surface = pygame.image.tostring(pygame_surface, 'RGB')
        glBindTexture(GL_TEXTURE_2D, self.texID)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
        surface_rect = pygame_surface.get_rect()
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, surface_rect.width, surface_rect.height, 0, GL_RGB, GL_UNSIGNED_BYTE,
                     rgb_surface)
        glColor3f(1.0, 1.0, 1.0)
        glGenerateMipmap(GL_TEXTURE_2D)
        return surface_rect

    def _encode_photodiode(self):
        """ Encodes the flip parity or flip number in the flip amplitude.
        """
        if self.photodiode:
            amp = self.phd_f(self.flip_count)
            glLoadIdentity()
            glDisable(GL_LIGHTING)
            glEnable(GL_TEXTURE_2D)
            glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
            glDisable(GL_TEXTURE_2D)
            glColor3f(amp, amp, amp)
            glRectf(-1, 1, self.phd_size[0]*2-1, 1-self.phd_size[1]*2)

    def quit(self):
        pygame.mouse.set_visible(1)
        pygame.display.quit()
