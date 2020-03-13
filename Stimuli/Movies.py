from Stimulus import *
import imageio, pygame, io


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
        self.timer.start()

    def present(self):
        if self.timer.elapsed_time() < self.params['stim_duration']:
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

    def unshow(self, color=False):
        """update background color"""
        if not color:
            color = self.color
        self.screen.fill(color)
        self.flip()

    def encode_photodiode(self):
        """Encodes the flip number n in the flip amplitude.
        Every 32 sequential flips encode 32 21-bit flip numbers.
        Thus each n is a 21-bit flip number:
        FFFFFFFFFFFFFFFFCCCCP
        P = parity, only P=1 encode bits
        C = the position within F
        F = the current block of 32 flips
        """
        n = self.flip_count + 1
        amp = 127 * (n & 1) * (2 - (n & (1 << (((np.int64(np.floor(n / 2)) & 15) + 6) - 1)) != 0))
        surf = pygame.Surface(self.phd_size)
        surf.fill((amp, amp, amp))
        self.screen.blit(surf, (0, 0))

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


    def get_new_cond(self):
        """Get curr condition & create random block of all conditions
        Should be called within init_trial
        """
        if self.params['randomization'] == 'block':
            if np.size(self.indexes) == 0:
                self.indexes = np.random.permutation(np.size(self.conditions))
            cond = self.conditions[self.indexes[0]]
            self.indexes = self.indexes[1:]
            self.curr_cond = cond
        elif self.params['randomization'] == 'random':
            self.curr_cond = np.random.choice(self.conditions)
        elif self.params['randomization'] == 'bias':
            if len(self.beh.probe_bias) == 0 or np.all(np.isnan(self.beh.probe_bias)):
                self.beh.probe_bias = np.random.choice(self.probes, 5)
                self.curr_cond = np.random.choice(self.conditions)
            else:
                mn = np.min(self.probes)
                mx = np.max(self.probes)
                bias_probe = np.random.binomial(1, 1 - np.nanmean((self.beh.probe_bias - mn)/(mx-mn)))*(mx-mn) + mn
                biased_conditions = [i for (i, v) in zip(self.conditions, self.probes == bias_probe) if v]
                self.curr_cond = np.random.choice(biased_conditions)
