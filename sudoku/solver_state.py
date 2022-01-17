from copy import deepcopy
from exceptions import ConstraintViolationError
from typing import List


class SolverState(object):
    def __init__(self, board, expected_solution):
        self.board = board
        self.expected_solution = expected_solution

        # This gives the remaining choices for cells in a row. When this is empty the row is solved.
        self.row_remaining = [[i for i in range(1, 10)] for _ in range(1, 10)]

        # This gives the remaining choices for cells in a column. When this is empty the column is solved.
        self.col_remaining = [[i for i in range(1, 10)] for _ in range(1, 10)]

        # cell_possibles[row][col] gives the possible values for each cell
        self.cell_possible = [[[i for i in range(1, 10)] for _ in range(1, 10)] for _ in range(1, 10)]

    def copy(self):
        new_state = SolverState(deepcopy(self.board), self.expected_solution)
        new_state.cell_possible = deepcopy(self.cell_possible)
        new_state.row_remaining = deepcopy(self.row_remaining)
        new_state.col_remaining = deepcopy(self.col_remaining)
        return new_state

    @property
    def cell_possible(self) -> List[List[List[int]]]:
        return self._cell_possible

    @cell_possible.setter
    def cell_possible(self, val):
        self._cell_possible = val

    def get_possible_for_cell(self, row, column) -> List[int]:
        return self.cell_possible[row][column]

    def mark_value_impossible(self, row, column, to_remove) -> bool:
        if to_remove in self.cell_possible[row][column]:
            self.cell_possible[row][column].remove(to_remove)
            return True
        else:
            return False

    def compute_new_cell_possibilities(self, row, column):
        current_possible = set(self.row_remaining[row]).union(self.col_remaining[column])
        old_possible = set(self.cell_possible[row][column])

        # apply the updated information but intersect it with the old info so we don't go backward
        self.cell_possible[row][column] = list(current_possible.intersection(old_possible))

    def set_cell_possibilities(self, row, column, value: list[int]):
        self.cell_possible[row][column] = value

    @property
    def row_remaining(self) -> List[List[int]]:
        return self._row_remaining

    @row_remaining.setter
    def row_remaining(self, val):
        self._row_remaining = val

    @property
    def col_remaining(self) -> List[List[int]]:
        return self._col_remaining

    @col_remaining.setter
    def col_remaining(self, val):
        self._col_remaining = val

    @property
    def board(self):
        return self._board

    @board.setter
    def board(self, val):
        self._board = val

    # TODO: some of these seem like they should be assertions (the code has a bug rather than the solver tried an illegal value)
    def assert_consistency(self):
        for r in range(9):
            for c in range(9):
                if len(self.get_possible_for_cell(r, c)) == 0:
                    raise ConstraintViolationError(f"No possible values for cell {r, c}")

                if len(self.get_possible_for_cell(r, c)) == 1:
                    # if there are no more possibiliites, yet this cell has not been solved, there is a bug
                    if self.board[r][c] is None:
                        raise ConstraintViolationError(
                            f"Cell {r, c} has no more possible values but wasn't marked on the board")

                if self.board[r][c] is not None:
                    if self.board[r][c] in self.row_remaining:
                        raise ConstraintViolationError(f"Solved cell still assignable in row {r}")

                    if self.board[r][c] in self.col_remaining:
                        raise ConstraintViolationError(f"Solved cell still assignable in column {c}")

                    if self.board[r][c] != self.get_possible_for_cell(r, c)[0]:
                        raise ConstraintViolationError(f"Solved cell {r, c} marked impossible")

                    if len(self.get_possible_for_cell(r, c)) != 1:
                        raise ConstraintViolationError(
                            f"Cell {r, c} was solved but still has possibilities: {self.get_possible_for_cell(r, c)}")

                    # I'm not sure this should even be here. I could just check this at the very end
                    if self.expected_solution is not None:
                        expected = self.expected_solution[r][c]
                        actual = self.board[r][c]
                        if actual != expected:
                            raise ConstraintViolationError(
                                f"Cell {r, c} has value of {actual} did not match expected value {expected}")

        # no two values in the same column:
        self.check_rows()

        # no two values in the same row:
        self.check_columns()

        # no two values in the same section
        for start_row in range(0, 7, 3):
            for start_col in range(0, 7, 3):
                self.check_section(start_row, start_row + 3, start_col, start_col + 3)

    def check_rows(self):
        for r in range(9):
            row_values = set()
            for c in range(9):
                value = self.board[r][c]
                if value:
                    if value in row_values:
                        raise ConstraintViolationError(f"Cell {r, c} value {value} is duplicatedd in row")
                    row_values.add(value)

    def check_columns(self):
        for c in range(9):
            col_values = set()
            for r in range(9):
                value = self.board[r][c]
                if value:
                    if self.board[r][c] in col_values:
                        raise ConstraintViolationError(f"Cell {r, c} is duplicated in column")
                    col_values.add(value)

    def check_section(self, start_row, end_row, start_col, end_col):
        nums_in_section = set()
        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                if self.board[r][c] in nums_in_section:
                    raise ConstraintViolationError(
                        f"Duplicate value {self.board[r][c]} in section {(start_row, end_row), (start_col, end_col)}")
                if self.board[r][c] is not None:
                    nums_in_section.add(self.board[r][c])

    def is_solved(self):
        for row in self.board:
            for cell in row:
                if not cell:
                    return False
        try:
            self.assert_consistency()
        except ConstraintViolationError:
            return False

        return True
