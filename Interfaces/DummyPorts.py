import pygame

from core.Interface import Interface, Port


class DummyPorts(Interface):
    def __init__(self, **kwargs):
        super(DummyPorts, self).__init__(**kwargs)
        global pygame
        if not pygame.get_init():
            pygame.init()
        pygame.display.init()
        self.dummy_ports = {
            "left_port": [pygame.KEYDOWN, "left"],
            "right_port": [pygame.KEYDOWN, "right"],
            "proximity_true": [pygame.KEYDOWN, "space"],
            "proximity_false": [pygame.KEYUP, "space"],
        }
        self.beh.is_licking = self.call_getevents(self.beh.is_licking)
        self.beh.get_response = self.call_getevents(self.beh.get_response)

    def call_getevents(self, original_method):
        def wrapper(*args, **kwargs):
            self._get_events()
            return original_method(*args, **kwargs)

        return wrapper

    def in_position(self):
        self._get_events()
        position_dur = (
            self.timer_ready.elapsed_time() if self.ready else self.position_dur
        )
        return self.position, position_dur, self.position_tmst

    def off_proximity(self):
        self._get_events()
        return self.position.type != "Proximity"

    def stop_sound(self):
        print("Stopping sound")

    def _get_events(self):
        port = 0
        events = pygame.event.get() if pygame.get_init() else []

        for event in events:
            # Check if any port is licked
            port = self._port_activated(event, port)
            # Check position
            port = self._proximity_change(event, port)

            if event.type == pygame.MOUSEBUTTONDOWN:
                print(pygame.mouse.get_pos())
            elif event.type == pygame.QUIT:
                self.logger.update_setup_info({"status": "stop"})

    def _port_activated(self, event, port):
        if self.dummy_ports_true(event, "left_port"):
            print("Probe 1 activated!")
            port = 1
        if self.dummy_ports_true(event, "right_port"):
            print("Probe 2 activated!")
            port = 2
        if port:
            self.position = self.ports[Port(type="Lick", port=port) == self.ports][0]
            self.resp_tmst = self.logger.logger_timer.elapsed_time()
            self.beh.log_activity(self.position.__dict__)
        return port

    def _proximity_change(self, event, port):
        if self.dummy_ports_true(event, "proximity_true") and not self.ready:
            self.timer_ready.start()
            self.ready = True
            port = 3
            self.position = self.ports[Port(type="Proximity", port=port) == self.ports][
                0
            ]
            self.position_tmst = self.beh.log_activity(
                {**self.position.__dict__, "in_position": self.ready}
            )
            print("in position")
        elif self.dummy_ports_true(event, "proximity_false") and self.ready:
            self.ready = False
            port = 0
            tmst = self.beh.log_activity(
                {**self.position.__dict__, "in_position": self.ready}
            )
            self.position_dur = tmst - self.position_tmst
            self.position = Port()
            print("off position")
            # print(pygame.mouse.get_pos())

    def dummy_ports_true(self, event, name):
        if event.type == self.dummy_ports[name][0]:
            if pygame.key.name(event.key) == self.dummy_ports[name][1]:
                return True
        return False

    def load_calibration(self):
        pass

    def setup_touch_exit(self):
        pass

    def calc_pulse_dur(self, reward_amount):
        actual_rew = dict()
        for port in self.rew_ports:
            actual_rew[port] = reward_amount
        return actual_rew

    def cleanup(self):
        pygame.display.quit()
        self.set_operation_status(False)
