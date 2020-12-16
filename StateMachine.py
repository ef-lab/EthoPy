

# A State has an operation, and can be moved
# into the next State given an Input
class StateClass:
    def entry(self):
        """Entry transition method"""
        pass

    def run(self):
        """Main run command"""
        assert 0, "run not implemented"

    def next(self):
        """Exit transition method"""
        assert 0, "next not implemented"

    def exit(self):
        """Exit transition method"""
        pass


# move from State to State using a template method.
class StateMachine:
    def __init__(self, initialState, exitState):
        self.futureState = initialState
        self.currentState = initialState
        self.exitState = exitState

    # # # # Main state loop # # # # #
    def run(self):
        while self.futureState != self.exitState:
            if self.currentState != self.futureState:
                self.currentState.exit()
                self.currentState = self.futureState
                self.currentState.entry()
            self.currentState.run()
            self.futureState = self.currentState.next()
        self.currentState.exit()
        self.exitState.run()
