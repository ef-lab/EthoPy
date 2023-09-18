import pygame
from pygame.locals import *
from OpenGL.GL import *

texID = glGenTextures(1)


class Presenter():

    def __init__(self, size, display=0):
        if not pygame.get_init():
            pygame.init()
        PROPERTIES = pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN | pygame.OPENGL
        self.screen = pygame.display.set_mode(size, PROPERTIES, display=display)
        pygame.display.init()
        pygame.mouse.set_visible(0)
        self.clock = pygame.time.Clock()
        self.color = (0, 0, 0)
        self.flip_count = 0
        #self.phd_size = (50, 50)  # default photodiode signal size in pixels

        self.info = pygame.display.Info()

        self.offscreen_surface = pygame.Surface((self.info.current_w, self.info.current_h))
        self.offscreen_surface.fill(self.color)

        glViewport(0, 0, self.info.current_w, self.info.current_h)
        glDepthRange(0, 1)
        glMatrixMode(GL_PROJECTION)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glShadeModel(GL_SMOOTH)
        glClearColor(self.color[0], self.color[1], self.color[2], 0.0)
        glClearDepth(1.0)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glDepthFunc(GL_LEQUAL)
        glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        self.fill()

    def set_background_color(self, color):
        self.color = color
        glClearColor(self.color[0]/255, self.color[1]/255, self.color[2]/255, 0.0)

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

        glBindTexture(GL_TEXTURE_2D, texID)
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

    def fill(self, color=False):
        if not color:
            color = self.color
        self.offscreen_surface.fill(color)
        self.render(self.offscreen_surface)

    def flip(self):
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == QUIT: pygame.quit()
        self.flip_count += 1

    def make_surface(self, array):
        return pygame.surfarray.make_surface(array)

    def flip_clock(self, fps):
        self.clock.tick_busy_loop(fps)

    def _surfaceToTexture(self, pygame_surface):
        global texID
        rgb_surface = pygame.image.tostring(pygame_surface, 'RGB')
        glBindTexture(GL_TEXTURE_2D, texID)
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
