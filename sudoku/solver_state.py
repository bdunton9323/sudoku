from copy import deepcopy
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

    def mark_value_impossible(self, row, column, to_remove):
        if to_remove in self.cell_possible[row][column]:
            self.cell_possible[row][column].remove(to_remove)

    def compute_new_cell_possibilities(self, row, column):
        self.cell_possible[row][column] = list(
            set(self.row_remaining[row])
                .union(self.col_remaining[column])
                .intersection(set(self.cell_possible[row][column])))

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
