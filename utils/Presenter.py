import pygame
from pygame.locals import *
from OpenGL.GL import *


class Presenter():

    def __init__(self, monitor, background_color=(0, 0, 0)):
        global pygame
        if not pygame.get_init():
            pygame.init()
        else:
            print('pygame already initiated! (Presenter)')
        if monitor.fullscreen:
            PROPERTIES = pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN | pygame.OPENGL
        else:
            PROPERTIES = pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.OPENGL
        self.screen = pygame.display.set_mode((monitor.resolution_x, monitor.resolution_y),
                                              PROPERTIES, display=monitor.screen_idx-1)
        pygame.display.init()
        pygame.mouse.set_visible(0)
        self.clock = pygame.time.Clock()
        self.set_background_color(background_color)
        self.flip_count = 0
        #self.phd_size = (50, 50)  # default photodiode signal size in pixels

        self.info = pygame.display.Info()
        self.texID = glGenTextures(1)
        self.offscreen_surface = pygame.Surface((self.info.current_w, self.info.current_h))
        self.offscreen_surface.fill((self.background_color[0]*255,
                                     self.background_color[1]*255,
                                     self.background_color[2]*255))

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

        glBindTexture(GL_TEXTURE_2D, self.texID)
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
        glColor3fv(self.background_color)

    def fill(self, color=False):
        if not color:
            color = self.background_color
        self.offscreen_surface.fill((color[0]*255, color[0]*255, color[0]*255))
        self.render(self.offscreen_surface)

    def flip(self):
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == QUIT: pygame.quit()
        self.flip_count += 1

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
        glGenerateMipmap(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)
        return surface_rect

    #def _encode_photodiode(self):
    #    """Encodes the flip number n in the flip amplitude.
    #    Every 32 sequential flips encode 32 21-bit flip numbers.
    #    Thus each n is a 21-bit flip number:
    #    FFFFFFFFFFFFFFFFCCCCP
    #    P = parity, only P=1 encode bits
    #    C = the position within F
    #    F = the current block of 32 flips
    #    """
    #    n = self.flip_count + 1
    #    amp = 127 * (n & 1) * (2 - (n & (1 << (((np.int64(np.floor(n / 2)) & 15) + 6) - 1)) != 0))
    #    surf = pygame.Surface(self.phd_size)
    #    surf.fill((amp, amp, amp))
    #    self.screen.blit(surf, (0, 0))

    def quit(self):
        pygame.mouse.set_visible(1)
        pygame.display.quit()
