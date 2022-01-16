from exceptions import ConstraintViolationError


def assert_constraint(condition, message="Game constraint violated"):
    if not condition:
        raise ConstraintViolationError(message)
