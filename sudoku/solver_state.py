from copy import deepcopy
from exceptions import ConstraintViolationError
from itertools import chain
from typing import List


class SolverState(object):
    """
    This class resembles the scratch pad that a human would use when solving Sudoku. It tracks what is assigned in
    every cell, what is still possible for each cell, and what is still possible in each row and column. Most of the
    methods in here are related to manipulating that information and accessing it in different ways.
    """
    def __init__(self, board):
        self.board = board

        # This gives the remaining choices for cells in a row. When this is empty the row is solved.
        self.row_remaining = [[i for i in range(1, 10)] for _ in range(1, 10)]

        # This gives the remaining choices for cells in a column. When this is empty the column is solved.
        self.col_remaining = [[i for i in range(1, 10)] for _ in range(1, 10)]

        # cell_possibles[row][col] gives the possible values for each cell
        self.cell_possible = [[[i for i in range(1, 10)] for _ in range(1, 10)] for _ in range(1, 10)]

    def copy(self):
        new_state = SolverState(deepcopy(self.board))
        new_state.cell_possible = deepcopy(self.cell_possible)
        new_state.row_remaining = deepcopy(self.row_remaining)
        new_state.col_remaining = deepcopy(self.col_remaining)
        return new_state

    def get_possible_for_cell(self, row, column) -> List[int]:
        return self.cell_possible[row][column]

    def mark_value_impossible(self, row, column, to_remove) -> bool:
        if to_remove in self.cell_possible[row][column]:
            self.cell_possible[row][column].remove(to_remove)
            return True
        else:
            return False

    def set_cell_possibilities(self, row, column, value: list[int]):
        self.cell_possible[row][column] = value

    def get_remaining_cell_choices_in_row(self, row) -> set[int]:
        # only include unsolved cells because solved ones are no longer available to assign
        # cells with one possibility are known
        # unknowns = filter(lambda c:  len(c) != 1, self.cell_possible[row])
        # return list(chain.from_iterable(unknowns))
        choices = set()
        for col in range(9):
            if len(self.cell_possible[row][col]) != 1:
                choices.update(self.cell_possible[row][col])
        return choices

    def get_remaining_cell_choices_in_col(self, col: int) -> set[int]:
        # building a set explicitly is much faster than using itertools.chain(filter()))
        choices = set()
        for row in range(9):
            if len(self.cell_possible[row][col]) != 1:
                choices.update(self.cell_possible[row][col])
        return choices

    def get_values_in_range(self, start_cell, end_cell):
        # building a set explicitly is much faster than using itertools.chain(filter()))
        values_in_section = []
        for r in range(start_cell[0], end_cell[0]):
            for c in range(start_cell[1], end_cell[1]):
                if self.board[r][c] is not None:
                    values_in_section.append(self.board[r][c])
        return values_in_section

    def get_choices_for_row(self, row):
        return self.row_remaining[row]

    def set_choices_for_row(self, row, new_choices: List[int]):
        self.row_remaining[row] = new_choices

    def get_choices_for_col(self, col):
        return self.col_remaining[col]

    def set_choices_for_col(self, col, new_choices: List[int]):
        self.col_remaining[col] = new_choices

    def remove_row_choice(self, row, value):
        if value in self.row_remaining[row]:
            self.row_remaining[row].remove(value)

    def remove_col_choice(self, col, value):
        if value in self.col_remaining[col]:
            self.col_remaining[col].remove(value)

    def board_at(self, row, column):
        return self.board[row][column]

    def set_cell(self, row, column, value):
        self.board[row][column] = value

    def cell_solved(self, row: int, column: int) -> bool:
        return self.board[row][column] is not None

    def get_row(self, row):
        return self.board[row]

    def get_column(self, col):
        return [v[col] for v in self.board]

    def update_board(self, row, column, value):
        self.set_cell(row, column, value)
        if value in self.row_remaining:
            self.row_remaining.remove(value)
        if value in self.col_remaining:
            self.col_remaining.remove(value)
        self.set_cell_possibilities(row, column, [value])

    def assert_still_valid(self):
        # no two values in the same column:
        self._check_rows()

        # no two values in the same row:
        self._check_columns()

        # no two values in the same section
        for start_row in range(0, 7, 3):
            for start_col in range(0, 7, 3):
                self._check_section(start_row, start_row + 3, start_col, start_col + 3)

        self._assert_internal_consistency()

    def _check_rows(self):
        for r in range(9):
            row_values = set()
            for c in range(9):
                value = self.board[r][c]
                if value:
                    if value in row_values:
                        raise ConstraintViolationError(f"Cell {r, c} value {value} is duplicatedd in row")
                    row_values.add(value)

    def _check_columns(self):
        for c in range(9):
            col_values = set()
            for r in range(9):
                value = self.board[r][c]
                if value:
                    if self.board[r][c] in col_values:
                        raise ConstraintViolationError(f"Cell {r, c} is duplicated in column")
                    col_values.add(value)

    def _check_section(self, start_row, end_row, start_col, end_col):
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
            self.assert_still_valid()
        except ConstraintViolationError:
            return False

        return True

    def compare_to_expected(self, expected_solution):
        for r in range(9):
            for c in range(9):
                if self.board[r][c] != expected_solution[r][c]:
                    print(f"{r, c} was {self.board[r][c]} but expected {expected_solution[r][c]}")

    def _assert_internal_consistency(self):
        for r in range(9):
            for c in range(9):
                assert(self.get_possible_for_cell(r, c) != 0)

                # if there are no more possibiliites, yet this cell has not been solved, there is a bug
                if len(self.get_possible_for_cell(r, c)) == 1:
                    assert(self.board[r][c] is not None)

                if self.board[r][c] is not None:
                    assert(self.board[r][c] not in self.row_remaining)
                    assert(self.board[r][c] not in self.col_remaining)
                    assert(self.board[r][c] == self.get_possible_for_cell(r, c)[0])
                    assert(len(self.get_possible_for_cell(r, c)) == 1)
