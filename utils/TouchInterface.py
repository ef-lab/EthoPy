import pygame, numpy, os
from ft5406 import Touchscreen, TS_PRESS, TS_RELEASE


class Button:
    def __init__(self, **kwargs):
        self.color = kwargs.get('color', (50, 50, 50))
        self.push_color = kwargs.get('push_color', (128, 0, 0))
        self.x = kwargs.get('x', 350)
        self.y = kwargs.get('y', 200)
        self.w = kwargs.get('w', 90)
        self.h = kwargs.get('h', 90)
        self.font_color = kwargs.get('font_color', (255, 255, 255))
        self.font_size = kwargs.get('font_size', 20)
        self.name = kwargs.get('name', '')
        self.action = kwargs.get('action', '')
        self.pressed = False

    def is_pressed(self):
        if self.pressed:
            self.pressed = False
            return True
        return False


class TouchInterface:
    def __init__(self, **kwargs):
        # define interface parameters
        self.screen_size = kwargs.get('screen_size', (800, 480))
        self.fill_color = kwargs.get('fill_color', (0, 0, 0))
        self.font_color = kwargs.get('font_color', (255, 255, 255))
        self.font_size = kwargs.get('font_size', 20)
        self.font = kwargs.get('font', "freesansbold.ttf")
        cmd = 'echo %d > /sys/class/backlight/rpi_backlight/brightness' % 64
        os.system(cmd)

        # define interface variables
        self.screen = None
        self.ts = Touchscreen()
        if not pygame.get_init():
            pygame.init()
        pygame.mouse.set_visible(0)
        self.screen = pygame.display.set_mode(self.screen_size)
        pygame.display.toggle_fullscreen()
        for touch in self.ts.touches:
            touch.on_press = self._touch_handler
            touch.on_release = self._touch_handler

        self.ts.run()
        self.screen.fill(self.fill_color)
        self.buttons = []
        self.texts = []
        self.button = []
        self.numpad = ''

    def _draw_button(self, button, color=None):
        if not color:
            color = button.color
        self.draw(button.name, button.x, button.y, button.w, button.h,
                  button.font_color, button.font_size, color)

    def _numpad_input(self, digit):
        if any(digit):
            self.numpad += digit
        else:
            self.numpad = self.numpad[0:-1]
        self.draw(self.numpad, 500, 0, 300, 100, (255, 255, 255), 40, (0, 0, 0))

    def _touch_handler(self, event, touch):
        if event == TS_PRESS:
            self.button = []
            for button in self.buttons:
                if button.x+button.w > touch.x > button.x and button.y+button.h > touch.y > button.y:
                    self.button = button
                    self._draw_button(button, button.push_color)
                    return
        if event == TS_RELEASE:
            button = self.button
            if button:
                self._draw_button(button)
                button.pressed = True
                if isinstance(button.action, str):
                    exec(button.action)
                else:
                    button.action()

    def add_button(self,  **kwargs):
        button = Button(**kwargs)
        self.buttons.append(button)
        self._draw_button(button)
        return button

    def remove_button(self, button):
        self.buttons.remove(button)

    def add_numpad(self):
        for i in range(1, 10):
            self.add_button(name=str(i), x=numpy.mod(i-1, 3)*100+400, y=numpy.floor((i-1)/3)*100+100,
                            action='self._numpad_input("' + str(i) + '")')
        self.add_button(name='0', x=700, y=200, action='self._numpad_input("0")')
        self.add_button(name='<-', x=700, y=300, action='self._numpad_input("")')
        self.add_button(name='.', x=700, y=100, action='self._numpad_input(".")')

    def add_esc(self):
        self.add_button(name='Esc', x=750, y=0, w=50, h=50, action='self.exit()')

    def draw(self, text, x=0, y=0, w=800, h=480, color=(255, 255, 255), size=40, background=None):
        if background:
            pygame.draw.rect(self.screen,  background, (x, y, w, h))
        font = pygame.font.Font(self.font, size)
        lines = []; txt = ''; line_width = 0; nline = 0
        for word in text.split(' '):
            word_surface = font.render(word, True, color)
            word_width, word_height = word_surface.get_size()
            if line_width + word_width >= w:
                lines.append(txt)
                txt = ''; line_width = 0
            txt += ' ' + word
            line_width += word_width + font.size(' ')[0]
        lines.append(txt)
        offset = (h-word_height*numpy.size(lines))/2
        for line in lines:
            nline += 1  # Start on new row.
            text_surf = font.render(line, True, color)
            text_rect = text_surf.get_rect()
            text_rect.center = ((x + (w / 2)), (y + offset + word_height*(nline-1) + word_height/2))
            self.screen.blit(text_surf, text_rect)
        pygame.display.update()

    def cleanup(self):
        self.screen.fill(self.fill_color)
        self.buttons = []
        self.button = []
        self.numpad = ''

    def exit(self):
        try:
            self.ts.stop()
        finally:
            if pygame.get_init():
                pygame.mouse.set_visible(1)
                pygame.quit()

