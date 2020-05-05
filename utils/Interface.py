import pygame, numpy
from ft5406 import Touchscreen, TS_PRESS, TS_RELEASE


class Interface:

    def __init__(self):
        self.screen = []
        self.screen_sz = (800, 480)
        self.background = (0, 0, 0)
        self.buttons = []
        self.button_color = (50, 50, 50)
        self.push_color=(128, 0, 0)
        self.font_color = (255, 255, 255)
        self.texts = []
        self.w = 90
        self.h = 90
        self.font_size = 20
        self.font = "freesansbold.ttf"
        self.numpad = ''
        self.ts = Touchscreen()
        self.button = []

    def _draw_button(self, button, color=None):
        if not color:
            color = button['color']
        self.draw(button['name'], button['x'], button['y'], button['w'], button['h'],
                  self.font_color, self.font_size, color)

    def _draw_text(self, text):
        self.draw(text['text'], text['x'], text['y'], text['w'], text['h'],
                  text['font_color'], text['font_size'], text['color'])

    def _numpad_input(self, digit):
        if any(digit):
            self.numpad += digit
        else:
            self.numpad = self.numpad[0:-1]
        self.draw(self.numpad, 0, 0, 200, 100)

    def _touch_handler(self, event, touch):
        if event == TS_PRESS:
            for button in self.buttons:
                if button['x']+button['w'] > touch.x > button['x'] and button['y']+button['h'] > touch.y > button['y']:
                    self.button = button
                    self._draw_button(button, self.push_color)
                    return
        if event == TS_RELEASE:
            self._draw_button(self.button)
            eval(self.button['action'])

    def add_button(self, name, x, y, x_size, y_size, action, color=None):
        if not color:
            color = self.button_color
        self.buttons.append({'name': name, 'x': x, 'y': y, 'w': x_size, 'h': y_size, 'action': action, 'color': color})

    def add_text(self, text, x, y, x_size, y_size, font_color=None, font_size=None, color=None):
        if not color:
            color = self.button_color
        if not font_color:
            font_color = self.font_color
        if not font_size:
            font_size = self.font_size
        self.texts.append({'text': text, 'x': x, 'y': y, 'w': x_size, 'h': y_size,
                           'font_size': font_size, 'font_color': font_color, 'color': color})

    def add_numpad(self):
        for i in range(1, 10):
            self.add_button(str(i), numpy.mod(i-1, 3)*100, numpy.floor((i-1)/3)*100+100,
                            self.w, self.h, 'self._numpad_input("' + str(i) + '")')
        self.add_button('0', 300, 200, self.w, self.h, 'self._numpad_input("0")')
        self.add_button('<-', 300, 300, self.w, self.h, 'self._numpad_input("")')
        self.add_button('.', 300, 100, self.w, self.h, 'self._numpad_input(".")')

    def add_esc(self):
        self.add_button('Esc', 750, 0, 50, 50, 'self.exit()')

    def draw(self, text, x, y, w, h, color=(255, 255, 255), size=40, background=None):
        if not background:
            background = self.background
        pygame.draw.rect(self.screen,  background, (x, y, w, h))
        text_h = pygame.font.Font(self.font, size)
        text_surf = text_h.render(text, True, color)
        text_rect = text_surf.get_rect()
        text_rect.center = ((x + (w / 2)), (y + (h / 2)))
        self.screen.blit(text_surf, text_rect)
        pygame.display.update()

    def run(self):
        pygame.init()
        self.screen = pygame.display.set_mode(self.screen_sz)
        self.screen.fill(self.background)
        for button in self.buttons:
            self._draw_button(button)

        for text in self.texts:
            self._draw_text(text)

        for touch in self.ts.touches:
            touch.on_press = self._touch_handler
            touch.on_release = self._touch_handler

        self.ts.run()

    def exit(self):
        try:
            self.ts.stop()
        finally:
            pygame.quit()

