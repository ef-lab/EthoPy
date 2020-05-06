import pygame, numpy
from ft5406 import Touchscreen, TS_PRESS, TS_RELEASE


class Button:
    def __init__(self, **kwargs):
        self.color = kwargs.get('color', (50, 50, 50))
        self.push_color = kwargs.get('push_color', (128, 0, 0))
        self.x = kwargs.get('x', 350)
        self.y = kwargs.get('y', 200)
        self.w = kwargs.get('w', 90)
        self.h = kwargs.get('h', 90)
        self.name = kwargs.get('name', '')
        self.action = kwargs.get('action', '')
        self.pressed = False

    def is_pressed(self):
        if self.pressed:
            self.pressed = False
            return True
        return False


class Interface:
    def __init__(self, **kwargs):

        # define interface parameters
        self.screen_size = kwargs.get('screen_size', (800, 480))
        self.fill_color = kwargs.get('fill_color', (0, 0, 0))
        self.font_color = kwargs.get('font_color', (255, 255, 255))
        self.font_size = kwargs.get('font_size', 20)
        self.font = kwargs.get('font', "freesansbold.ttf")

        # define interface variables
        self.screen = None
        self.buttons = []
        self.texts = []
        self.numpad = ''
        self.ts = Touchscreen()
        self.button = []

    def _draw_button(self, button, color=None):
        if not color:
            color = button.color
        self.draw(button.name, button.x, button.y, button.w, button.h,
                  self.font_color, self.font_size, color)

    def _draw_text(self, text):
        self.draw(text['text'], text['x'], text['y'], text['w'], text['h'],
                  text['font_color'], text['font_size'], text['color'])

    def _numpad_input(self, digit):
        if any(digit):
            self.numpad += digit
        else:
            self.numpad = self.numpad[0:-1]
        self.draw(self.numpad, 500, 0, 300, 100)

    def _touch_handler(self, event, touch):
        if event == TS_PRESS:
            for button in self.buttons:
                if button.x+button.w > touch.x > button.x and button.y+button.h > touch.y > button.y:
                    button.pressed = True
                    self.button = button
                    self._draw_button(button, button.push_color)
                    return
        if event == TS_RELEASE:
            self._draw_button(self.button)
            exec(self.button.action)

    def add_button(self,  **kwargs):
        button = Button(**kwargs)
        self.buttons.append(button)
        return button

    def add_text(self, text, x, y, x_size, y_size, font_color=None, font_size=None, color=None):
        if not color:
            color = self.fill_color
        if not font_color:
            font_color = self.font_color
        if not font_size:
            font_size = self.font_size
        self.texts.append({'text': text, 'x': x, 'y': y, 'w': x_size, 'h': y_size,
                           'font_size': font_size, 'font_color': font_color, 'color': color})

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
        for line in lines:
            nline += 1  # Start on new row.
            text_surf = font.render(line, True, color)
            text_rect = text_surf.get_rect()
            text_rect.center = ((x + (w / 2)), (y + (h / (numpy.size(lines) + 1)) * nline))
            self.screen.blit(text_surf, text_rect)
        pygame.display.update()

    def run(self):
        pygame.init()
        pygame.mouse.set_visible(0)
        self.screen = pygame.display.set_mode(self.screen_size)
        self.screen.fill(self.fill_color)
        for button in self.buttons:
            self._draw_button(button)

        for text in self.texts:
            self._draw_text(text)

        for touch in self.ts.touches:
            touch.on_press = self._touch_handler
            touch.on_release = self._touch_handler

        self.ts.run()

    def clear(self):
        pass

    def exit(self):
        try:
            self.ts.stop()
        finally:
            pygame.mouse.set_visible(1)
            pygame.quit()

