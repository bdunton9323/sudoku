from exceptions import ConstraintViolationError


def assert_constraint(condition, message="Game constraint violated"):
    if not condition:
        raise ConstraintViolationError(message)


class StatsTracker(object):
    def __init__(self):
        self.num_iterations = None
        self.num_guesses = 0
        self.max_recursion_depth = 0
        self.start_time = 0
        self.end_time = 0

    @property
    def num_iterations(self):
        return self._num_iterations

    @num_iterations.setter
    def num_iterations(self, val):
        self._num_iterations = val

    @property
    def num_guesses(self):
        return self._num_iterations

    @num_guesses.setter
    def num_guesses(self, val):
        self._num_iterations = val

    def on_recursion(self, depth):
        if depth > self.max_recursion_depth:
            self.max_recursion_depth = depth

    def get_max_recursion_depth(self):
        return self.max_recursion_depth

    def start_timer(self):
        self.start_time = time.time()

    def stop_timer(self):
        self.end_time = time.time()

    def get_elapsed_time(self):
        return self.end_time - self.start_time
