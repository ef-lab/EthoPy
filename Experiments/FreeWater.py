from utils.Timer import *
from StateMachine import *
from datetime import datetime, timedelta
from Stimulus import *
import os


class State(StateClass):
    def __init__(self, parent=None):
        self.timer = Timer()
        if parent:
            self.__dict__.update(parent.__dict__)

    def setup(self, logger, BehaviorClass, StimulusClass, session_params, conditions):

        logger.log_session(session_params, 'Free')

        # Initialize params & Behavior/Stimulus objects
        self.logger = logger
        self.beh = BehaviorClass(logger, session_params)
        self.stim = StimulusClass(logger, session_params, conditions, self.beh)
        self.params = session_params
        exitState = Exit(self)
        self.StateMachine = StateMachine(Prepare(self), exitState)

        print(conditions)
        self.logger.log_conditions(conditions, [])

        # Initialize states
        global states
        states = {
            'PreTrial'     : PreTrial(self),
            'Trial'        : Trial(self),
            'InterTrial'   : InterTrial(self),
            'Reward'       : Reward(self),
            'Sleep'        : Sleep(self),
            'OffTime'      : OffTime(self),
            'Exit'         : exitState}

    def entry(self):  # updates stateMachine from Database entry - override for timing critical transitions
        self.StateMachine.status = self.logger.get_setup_info('status')
        self.logger.update_state(self.__class__.__name__)

    def run(self):
        self.StateMachine.run()

    def is_sleep_time(self):
        now = datetime.now()
        t = datetime.strptime(self.params['start_time'], "%H:%M:%S")
        start = now.replace(hour=0, minute=0, second=0) + timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        t = datetime.strptime(self.params['stop_time'], "%H:%M:%S")
        stop = now.replace(hour=0, minute=0, second=0) + timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        if stop < start:
            stop = stop + timedelta(days=1)
        time_restriction = now < start or now > stop
        return time_restriction


class Prepare(State):
    def run(self):
        self.stim.setup()

    def next(self):
        if self.is_sleep_time():
            return states['Sleep']
        else:
            return states['PreTrial']


class PreTrial(State):
    def entry(self):
        self.stim.prepare()
        self.beh.prepare(self.stim.curr_cond)
        self.timer.start()
        self.logger.update_state(self.__class__.__name__)

    def run(self): pass

    def next(self):
        if self.beh.is_ready(self.stim.curr_cond['init_duration']):
            return states['Trial']
        else:
            self.StateMachine.status = self.logger.get_setup_info('status')
            return states['PreTrial']


class Trial(State):
    def __init__(self, parent):
        self.__dict__.update(parent.__dict__)
        self.is_ready = 0
        self.probe = 0
        self.resp_ready = False
        super().__init__()

    def entry(self):
        self.stim.unshow()
        self.logger.update_state(self.__class__.__name__)
        self.beh.is_licking()
        self.timer.start()  # trial start counter
        self.logger.init_trial(self.stim.curr_cond['cond_hash'])

    def run(self):
        self.stim.present()  # Start Stimulus
        self.is_ready = self.beh.is_ready(self.timer.elapsed_time())  # update times
        self.probe = self.beh.is_licking()
        if self.timer.elapsed_time() > self.stim.curr_cond['delay_duration'] and not self.resp_ready:
            self.resp_ready = True
            if self.probe > 0: self.beh.update_bias(self.probe)

    def next(self):
        if self.probe > 0 and self.resp_ready: # response to correct probe
            return states['Reward']
        elif self.timer.elapsed_time() > self.stim.curr_cond['trial_duration']:      # timed out
            return states['InterTrial']
        else:
            return states['Trial']

    def exit(self):
        self.logger.log_trial()
        self.stim.unshow((0, 0, 0))
        self.logger.ping()


class InterTrial(State):
    def run(self):
        if self.beh.is_licking():
            self.timer.start()

    def next(self):
        if self.is_sleep_time():
            return states['Sleep']
        elif self.beh.is_hydrated():
            return states['OffTime']
        elif self.timer.elapsed_time() > self.stim.curr_cond['intertrial_duration']:
            return states['PreTrial']
        else:
            return states['InterTrial']


class Reward(State):
    def run(self):
        self.beh.reward(self.stim.curr_cond['reward_amount'])
        self.stim.unshow([0, 0, 0])

    def next(self):
        return states['InterTrial']


class Sleep(State):
    def entry(self):
        self.logger.update_state(self.__class__.__name__)
        self.logger.update_setup_status('sleeping')
        self.stim.unshow([0, 0, 0])

    def run(self):
        self.logger.ping()
        time.sleep(5)

    def next(self):
        if self.is_sleep_time() and self.logger.get_setup_info('status') == 'sleeping':
            return states['Sleep']
        elif self.logger.get_setup_info('status') == 'sleeping':  # if wake up then update session
            self.logger.update_setup_status('running')
            return states['Exit']
        else:
            return states['PreTrial']


class OffTime(State):
    def entry(self):
        self.logger.update_state(self.__class__.__name__)
        self.logger.update_setup_status('offtime')
        self.stim.unshow([0, 0, 0])

    def run(self):
        self.logger.ping()
        time.sleep(5)

    def next(self):
        if self.is_sleep_time():
            return states['Sleep']
        elif self.logger.get_setup_info('status') == 'stop':  # if wake up then update session
            return states['Exit']
        else:
            return states['OffTime']


class Exit(State):
    def run(self):
        self.beh.cleanup()
        self.stim.close()


class Uniform(Stimulus):
    """ This class handles the presentation of Movies with an optimized library for Raspberry pi"""

    def setup(self):
        # setup parameters
        self.path = 'stimuli/'     # default path to copy local stimuli
        self.size = (800, 480)     # window size
        self.color = [127, 127, 127]  # default background color
        self.loc = (0, 0)          # default starting location of stimulus surface
        self.fps = 30              # default presentation framerate
        self.phd_size = (50, 50)    # default photodiode signal size in pixels
        self.set_intensity(self.params['intensity'])

        # setup pygame
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.unshow()
        pygame.mouse.set_visible(0)
        pygame.display.toggle_fullscreen()

    def prepare(self):
        self._get_new_cond()

    def unshow(self, color=False):
        """update background color"""
        if not color:
            color = self.color
        self.screen.fill(color)
        self.flip()

    def flip(self):
        """ Main flip method"""
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()

        self.flip_count += 1

    def close(self):
        """Close stuff"""
        pygame.mouse.set_visible(1)
        pygame.display.quit()
        pygame.quit()

    def set_intensity(self, intensity=None):
        if intensity is None:
            intensity = self.params['intensity']
        cmd = 'echo %d > /sys/class/backlight/rpi_backlight/brightness' % intensity
        os.system(cmd)
