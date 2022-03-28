from core.Behavior import *


@behavior.schema
class HeadFixed(Behavior, dj.Manual):
    definition = """
    # This class handles the behavior variables for RP
    ->BehCondition
    """

    def exit(self):
        self.interface.cleanup()

