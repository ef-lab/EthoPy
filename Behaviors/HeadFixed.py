from core.Behavior import *


@behavior.schema
class HeadFixed(Behavior, dj.Manual):
    definition = """
    # This class handles the behavior variables for RP
    ->BehCondition
    """

    def setup(self, exp):
        self.logging = True
        super(HeadFixed, self).setup(exp)

    def exit(self):
        super().exit()
        self.interface.cleanup()

