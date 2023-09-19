from core.Stimulus import *
from time import sleep
import io, os, imageio
from utils.Presenter import *


@stimulus.schema
class Movies(Stimulus, dj.Manual):
    definition = """
    # movie clip conditions
    -> StimCondition
    ---
    movie_name           : char(8)                      # short movie title
    clip_number          : int                          # clip index
    movie_duration       : smallint                     # movie duration
    skip_time            : smallint                     # start time in clip
    static_frame         : smallint                     # static frame presentation
    """

    default_key = dict(movie_duration=10, skip_time=0, static_frame=False)
    required_fields = ['movie_name', 'clip_number', 'movie_duration', 'skip_time', 'static_frame']
    cond_tables = ['Movies']

    def __init__(self):
        super().__init__()
        self.fill_colors.set({'background': (128, 128, 128),
                              'start': (32, 32, 32),
                              'ready': (64, 64, 64),
                              'reward': (128, 128, 128),
                              'punish': (0, 0, 0)})
    def setup(self):
        # setup parameters
        self.path = os.path.dirname(os.path.abspath(__file__)) + '/movies/'
        self.size = (self.monitor['resolution_x'], self.monitor['resolution_y'])     # window size

        # setup screen
        self.Presenter = Presenter(self.monitor, background_color=self.fill_colors.background)
        self.timer = Timer()

    def prepare(self, curr_cond, stim_period=''):
        self.curr_cond = curr_cond
        self.curr_frame = 1
        clip = self.get_clip_info(self.curr_cond, 'Movie.Clip', 'clip')
        frame_height, frame_width = self.get_clip_info(self.curr_cond, 'Movie', 'frame_height', 'frame_width')
        self.vid = imageio.get_reader(io.BytesIO(clip[0].tobytes()), 'mov')
        self.vsize = (frame_width[0], frame_height[0])
        self.vfps = self.vid.get_meta_data()['fps']
        self.isrunning = True
        self.timer.start()

    def present(self):
        if self.timer.elapsed_time() < self.curr_cond['movie_duration']:
            surface = pygame.image.frombuffer(self.vid.get_next_data(), self.vsize, "RGB")
            self.Presenter.render(surface)
            self.Presenter.flip_clock(self.vfps)
            self.curr_frame += 1
        else:
            self.isrunning = False

    def stop(self):
        super().stop()
        self.vid.close()

    def fill(self, color=False):
        if not color:
            color = self.fill_colors.background
        if self.fill_colors.background: self.Presenter.fill(color)

    def exit(self):
        self.Presenter.quit()

    def get_clip_info(self, key, table, *fields):
        return self.exp.logger.get(schema='stimulus', table=table, key=key, fields=fields)



