from core.Stimulus import *
from time import sleep
import io, os, imageio
from utils.PsychoPresenter import *


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

    def init(self, exp):
        super().init(exp)
        self.path = self.logger.source_path + 'movies/'

    def setup(self):
        self.Presenter = Presenter(self.logger, self.monitor, background_color=self.fill_colors.background,
                                   photodiode='parity', rec_fliptimes=self.rec_fliptimes)

    def prepare(self, curr_cond, stim_period=''):
        self.curr_cond = curr_cond
        file_name = self.get_clip_info(self.curr_cond, 'Movie.Clip', 'file_name')
        frame_rate, frame_height, frame_width = \
            self.get_clip_info(self.curr_cond, 'Movie', 'frame_rate', 'frame_height', 'frame_width')
        video_aspect = frame_width[0]/frame_height[0]
        size = [2, video_aspect*2] if self.monitor.aspect > video_aspect else [2*video_aspect, 2]
        print('size: ', size)
        self.vid = psychopy.visual.MovieStim(self.Presenter.win, self.path +file_name[0],
                                             loop=False,  # replay the video when it reaches the end
                                             autoStart=True,
                                             size=[2, 2],  # set as `None` to use the native video size
                                             units='norm')

        self.in_operation = True
        self.timer.start()

    def present(self):
        if self.timer.elapsed_time() < self.curr_cond['movie_duration']:
            self.vid.draw()
            self.Presenter.flip()
        else:
            self.in_operation = False

    def stop(self):
        super().stop()
        self.vid.stop()

    def get_clip_info(self, key, table, *fields):
        return self.exp.logger.get(schema='stimulus', table=table, key=key, fields=fields)

    def make_conditions(self, conditions):
        conditions = super().make_conditions(conditions)

        # store local copy of files
        if not os.path.isdir(self.path):  # create path if necessary
            os.makedirs(self.path)
        for cond in conditions:
            file = self.exp.logger.get(schema='stimulus', table='Movie.Clip', key=cond, fields=('file_name',))
            print(file)
            filename = self.path + file[0]
            if not os.path.isfile(filename):
                print('Saving %s' % filename)
                clip = self.exp.logger.get(schema='stimulus', table='Movie.Clip', key=cond, fields=('clip',))
                clip[0].tofile(filename)
        return conditions


