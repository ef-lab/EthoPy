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

    def setup(self):
        super().setup()
        self.path = os.path.dirname(os.path.abspath(__file__)) + '/movies/'

    def prepare(self, curr_cond, stim_period=''):
        self.curr_cond = curr_cond
        self.curr_frame = 1
        clip = self.get_clip_info(self.curr_cond, 'Movie.Clip', 'clip')
        frame_rate, frame_height, frame_width = \
            self.get_clip_info(self.curr_cond, 'Movie', 'frame_rate', 'frame_height', 'frame_width')
        self.vid = imageio.get_reader(io.BytesIO(clip[0].tobytes()), format='mov')
        self.vsize = (frame_width[0], frame_height[0])
        self.vfps = frame_rate
        self.in_operation = True
        self.timer.start()

    def present(self):
        if self.timer.elapsed_time() < self.curr_cond['movie_duration']:
            surface = pygame.image.frombuffer(self.vid.get_next_data(), self.vsize, "RGB")
            self.Presenter.render(surface)
            self.Presenter.tick(self.vfps)
            self.curr_frame += 1
        else:
            self.in_operation = False

    def stop(self):
        super().stop()
        self.vid.close()

    def get_clip_info(self, key, table, *fields):
        return self.exp.logger.get(schema='stimulus', table=table, key=key, fields=fields)



