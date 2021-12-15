from core.Behavior import *
from core.Interface import *


@behavior.schema
class HeadFixed(Behavior, dj.Manual):
    definition = """
    # This class handles the behavior variables for RP
    ->BehCondition
    """

    def setup(self, exp):
        self.interface = PCProbe(exp=exp)
        super(HeadFixed, self).setup(exp)

    def exit(self):
        self.interface.cleanup()

