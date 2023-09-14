import pygame
from pygame.locals import *
from OpenGL.GL import *

texID = glGenTextures(1)


class Presenter():

    def __init__(self):
        pygame.init()
        PROPERTIES = pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN | pygame.OPENGL
        self.screen = pygame.display.set_mode((self.monitor['resolution_x'], self.monitor['resolution_y']), PROPERTIES)
        pygame.display.init()
        pygame.mouse.set_visible(0)
        self.clock = pygame.time.Clock()
        self.color = (0, 0, 0)
        info = pygame.display.Info()

        self.offscreen_surface = pygame.Surface((info.current_w, info.current_h))
        self.offscreen_surface.fill(self.color)

        glViewport(0, 0, info.current_w, info.current_h)
        glDepthRange(0, 1)
        glMatrixMode(GL_PROJECTION)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glShadeModel(GL_SMOOTH)
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClearDepth(1.0)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glDepthFunc(GL_LEQUAL)
        glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        self.unshow()

    def render(self, surface):
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()
        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        self._surfaceToTexture(surface)
        glBindTexture(GL_TEXTURE_2D, texID)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0);
        glVertex2f(-1, 1)
        glTexCoord2f(0, 1);
        glVertex2f(-1, -1)
        glTexCoord2f(1, 1);
        glVertex2f(1, -1)
        glTexCoord2f(1, 0);
        glVertex2f(1, 1)
        glEnd()
        self.flip()

    def unshow(self, color=False):
        if not color:
            color = self.color
        self.offscreen_surface.fill(self.color)
        self.render(self.offscreen_surface)

    def flip(self):
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == QUIT: pygame.quit()
        self.flip_count += 1

    def make_surface(self, array):
        return pygame.surfarray.make_surface(array)

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

    def quit(self):
        pygame.mouse.set_visible(1)
        pygame.display.quit()
        pygame.quit()
