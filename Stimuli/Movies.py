from Stimulus import *


class Movies(Stimulus):
    """ This class handles the presentation of Movies"""

    def setup(self):
        # setup parameters
        self.path = 'stimuli/'     # default path to copy local stimuli
        self.size = (400, 240)     # window size
        self.color = [127, 127, 127]  # default background color
        self.loc = (0, 0)          # default starting location of stimulus surface
        self.fps = 30              # default presentation framerate
        self.phd_size = (50, 50)    # default photodiode signal size in pixels

        # setup pygame
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.unshow()
        pygame.mouse.set_visible(0)

    def prepare(self):
        self.probes = np.array([d['probe'] for d in self.conditions])
        self.logger.log_conditions('MovieCond', self.conditions)

    def init(self):
        self.curr_frame = 1
        self.clock = pygame.time.Clock()
        clip_info = self.logger.get_clip_info(self.curr_cond)
        self.vid = imageio.get_reader(io.BytesIO(clip_info['clip'].tobytes()), 'ffmpeg')
        self.vsize = (clip_info['frame_width'], clip_info['frame_height'])
        self.pos = np.divide(self.size, 2) - np.divide(self.vsize, 2)
        self.isrunning = True

        self.logger.start_trial(self.curr_cond['cond_idx'])  # log start trial
        return self.curr_cond

    def present(self):
        if self.curr_frame < self.vid.count_frames():
            py_image = pygame.image.frombuffer(self.vid.get_next_data(), self.vsize, "RGB")
            self.screen.blit(py_image, self.pos)
            self.flip()
            self.curr_frame += 1
            self.clock.tick_busy_loop(self.fps)
        else:
            self.isrunning = False

    def stop(self):
        self.vid.close()
        self.unshow()
        self.isrunning = False
        self.logger.log_trial()  # log trial
