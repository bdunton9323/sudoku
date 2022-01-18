from __future__ import annotations
from copy import deepcopy
from exceptions import ConstraintViolationError
from typing import List


class SolverState(object):
    """
    This class resembles the scratch pad that a human would use when solving Sudoku. It tracks what is assigned in
    every cell, what is still possible for each cell, and what is still possible in each row and column. Most of the
    methods in here are related to manipulating that information and accessing it in different ways.

    This allows the algorithm to be separate from the data.
    """
    def __init__(self, board):
        self.board = board

        # This gives the remaining choices for cells in a row. When this is empty the row is solved.
        self.row_remaining = [[i for i in range(1, 10)] for _ in range(1, 10)]

        # This gives the remaining choices for cells in a column. When this is empty the column is solved.
        self.col_remaining = [[i for i in range(1, 10)] for _ in range(1, 10)]

        # cell_possibles[row][col] gives the possible values for each cell
        self.cell_possible = [[[i for i in range(1, 10)] for _ in range(1, 10)] for _ in range(1, 10)]

    def copy(self) -> SolverState:
        """ Returns a deep copy of this SolverState. Useful for undoing changes. """
        new_state = SolverState(deepcopy(self.board))
        new_state.cell_possible = deepcopy(self.cell_possible)
        new_state.row_remaining = deepcopy(self.row_remaining)
        new_state.col_remaining = deepcopy(self.col_remaining)
        return new_state

    def get_choices_for_cell(self, row: int, column: int) -> List[int]:
        """ Returns the list of remaining choices possible for the given cell """
        return self.cell_possible[row][column]

    def get_choices_for_cells_in_row(self, row) -> set[int]:
        """
        Returns the union of remaining possible choices for all the cells in the given row. This only includes
        unsolved cells because solved ones are no longer possible to assign.
        """
        choices = set()
        for col in range(9):
            # cells with one possibility are known
            if len(self.cell_possible[row][col]) != 1:
                choices.update(self.cell_possible[row][col])
        return choices

    def get_choices_for_cells_in_col(self, col: int) -> set[int]:
        """
        Returns the union of remaining possible choices for all the cells in the given column. This only includes
        unsolved cells because solved ones are no longer possible to assign.
        """
        # building a set explicitly is much faster than using itertools.chain(filter()))
        choices = set()
        for row in range(9):
            if len(self.cell_possible[row][col]) != 1:
                choices.update(self.cell_possible[row][col])
        return choices

    def get_unique_values_in_section(self, start_cell: (int, int), end_cell: (int, int)) -> list[int]:
        """
        Returns the unique values that are known within a given section, bounded by start_cell and end_cell.
        :param (int, int) start_cell: The upper left corner of the range (inclusive)
        :param (int, int) end_cell: The lower right corner of the range (exclusive)
        """
        # building a set explicitly is much faster than using itertools.chain(filter()))
        values_in_section = []
        for r in range(start_cell[0], end_cell[0]):
            for c in range(start_cell[1], end_cell[1]):
                if self.board[r][c] is not None:
                    values_in_section.append(self.board[r][c])
        return values_in_section

    def get_choices_for_row(self, row: int) -> list[int]:
        """ Returns the remaining possible choices for unsolved cells in the given row """
        return self.row_remaining[row]

    def get_choices_for_col(self, col: int) -> list[int]:
        """ Returns the remaining possible choices for unsolved cells in the given row """
        return self.col_remaining[col]

    def mark_impossible_in_cell(self, row, column, to_remove) -> bool:
        """
        Remove the given value from the list of remaining possibilities for the given cell
        :return bool True if anything was changed, False if the value was already impossible
        """
        if to_remove in self.cell_possible[row][column]:
            self.cell_possible[row][column].remove(to_remove)
            return True
        else:
            return False

    def mark_impossible_in_row(self, row: int, value: int):
        """ Remove the given value from the list of remaining possibilities for a given row """
        if value in self.row_remaining[row]:
            self.row_remaining[row].remove(value)

    def mark_impossible_in_col(self, col: int, value: int):
        """ Remove the given value from the list of remaining possibilities for a given row """
        if value in self.col_remaining[col]:
            self.col_remaining[col].remove(value)

    def set_choices_for_cell(self, row: int, column: int, value: list[int]):
        """ Sets the list of remaining possibilities for a given cell """
        self.cell_possible[row][column] = value

    def set_choices_for_row(self, row, new_choices: List[int]):
        """ Sets the list of remaining possibilities for a given row """
        self.row_remaining[row] = new_choices

    def set_choices_for_col(self, col, new_choices: List[int]):
        """ Sets the list of remaining possibilities for a given column """
        self.col_remaining[col] = new_choices

    def board_at(self, row: int, column: int) -> int:
        """ Returns the value of the given cell. Returns None if it does not have a known value. """
        return self.board[row][column]

    def is_cell_solved(self, row: int, column: int) -> bool:
        """ Returns whether the given cell has a known value """
        return self.board[row][column] is not None

    def get_row(self, row: int):
        """ Returns the given row of the board, including both solved and unsovled cells """
        return self.board[row]

    def get_column(self, col: int):
        """ Returns the given column of the board, including both solved and unsovled cells """
        return [v[col] for v in self.board]

    def update_board(self, row: int, column: int, value: int):
        """ Sets a value for the given cell in the board and updates the other possibility lists to match """
        self.board[row][column] = value

        # update all derived information
        self.set_choices_for_cell(row, column, [value])
        if value in self.row_remaining:
            self.row_remaining[row].remove(value)
        if value in self.col_remaining:
            self.col_remaining[column].remove(value)

    def is_solved(self) -> bool:
        """ Returns True if every cell in the board has a known value """
        for row in self.board:
            for cell in row:
                if not cell:
                    return False
        try:
            self.assert_still_valid()
        except ConstraintViolationError:
            return False

        return True

    def matches_expected(self, expected_solution) -> bool:
        """ Returns true if the current board matches the given expectation """
        matched = True
        for r in range(9):
            for c in range(9):
                if self.board[r][c] != expected_solution[r][c]:
                    return False
        return matched

    def assert_still_valid(self):
        """
        Ensures that all of the possiblity lists are consistent with each other. If they are not, it either
        indicates the solver has guessed an incorrect value (raises ConstraintViolationError) or there is a bug in the
        code (assertion failure)
        """
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

    def _assert_internal_consistency(self):
        # any of these assertions that fail indicate a bug in the code
        for r in range(9):
            for c in range(9):
                assert(self.get_choices_for_cell(r, c) != 0)

                # if there are no more possibiliites, yet this cell has not been solved, there is a bug
                if len(self.get_choices_for_cell(r, c)) == 1:
                    assert(self.board[r][c] is not None)

                if self.board[r][c] is not None:
                    assert(self.board[r][c] not in self.row_remaining)
                    assert(self.board[r][c] not in self.col_remaining)
                    assert(self.board[r][c] == self.get_choices_for_cell(r, c)[0])
                    assert(len(self.get_choices_for_cell(r, c)) == 1)
