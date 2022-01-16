import time
from copy import deepcopy
from exceptions import ConstraintViolationError
from utils import assert_constraint


# class SolverState(object):
#     def __init__(self, board, cell_possible, row_remaining, col_remaining):
#         self.board = board
#         self.cell_possible = cell_possible
#         self.row_remaining = row_remaining
#         self.col_remaining = col_remaining
#
#     def copy(self):
#         return SolverState(
#             self.board.copy(), self.cell_possible.copy(), self.row_remaining.copy(), self.col_remaining.copy())
#

class Solver(object):
    def __init__(self, board, expected_solution=None):
        self.board = board
        self.expected_solution = expected_solution

        # This gives the remaining choices for cells in a row. When this is empty the row is solved.
        self.row_remaining = [[i for i in range(1, 10)] for _ in range(1, 10)]

        # This gives the remaining choices for cells in a column. When this is empty the column is solved.
        self.col_remaining = [[i for i in range(1, 10)] for _ in range(1, 10)]

        # cell_possibles[row][col] gives the possible values for each cell
        self.cell_possible = [[[i for i in range(1, 10)] for _ in range(1, 10)] for _ in range(1, 10)]

    def solve(self):
        stats = StatsTracker()

        start_time = time.time()
        self.solve_internal(stats)
        end_time = time.time()

        BoardPrinter(self.board).pretty_print()

        if self.is_solved():
            self.print_success_stats(stats.num_iterations, end_time - start_time)
        else:
            self.print_failure_stats(stats.num_iterations, end_time - start_time)
            print(stats.get_guesses())

    def solve_internal(self, stats_tracker) -> bool:
        # Using what is known, get as many cells as possible using the game constraints.
        try:
            self.update_possibilities()
            stats_tracker.num_iterations += self.iteratively_solve()
            if self.is_solved():
                return True
        except ConstraintViolationError as e:
            #print(e.message)
            return False

        for row in range(8):
            for col in range(8):
                # scan to the first unsolved space
                if self.board[row][col] is not None:
                    continue

                before_guess_board = deepcopy(self.board)
                before_guess_row = deepcopy(self.row_remaining)
                before_guess_col = deepcopy(self.col_remaining)
                before_guess_cell = deepcopy(self.cell_possible)

                for guess in self.cell_possible[row][col]:
                    this_guess_board = deepcopy(self.board)
                    this_guess_row = deepcopy(self.row_remaining)
                    this_guess_col = deepcopy(self.col_remaining)
                    this_guess_cell = deepcopy(self.cell_possible)

                    stats_tracker.add_guess(row, col, guess)

                    # if this guess was invalid from the start, then move on
                    try:
                        self.update_board(row, col, guess)
                    except ConstraintViolationError as e:
                        print(f"Tried setting {row, col} to {guess} but it led to a violation: {e.message}")
                        self.rewind(this_guess_board, this_guess_row, this_guess_col, this_guess_cell)

                    # if this guess did not eventually lead to a correct solution
                    if not self.solve_internal(stats_tracker):
                        self.rewind(this_guess_board, this_guess_row, this_guess_col, this_guess_cell)

                # if none of the guesses worked
                if not self.is_solved():
                    self.rewind(before_guess_board, before_guess_row, before_guess_col, before_guess_cell)
                    return False

        return True

    def rewind(self, board, row_remaining, col_remaining, cell_possible):
        self.board = board
        self.row_remaining = row_remaining
        self.col_remaining = col_remaining
        self.cell_possible = cell_possible

    def iteratively_solve(self):
        changed = True
        num_iterations = 0
        while changed:
            num_iterations += 1
            changed = False

            if self.check_intersections():
                self.update_possibilities()
                changed = True

            if self.check_known():
                self.update_possibilities()
                changed = True

            # Can't repeat a number within a 3x3 section, so filter the possibilities
            if self.attempt_section():
                self.update_possibilities()
                changed = True

        return num_iterations

    def rank_cells_by_easiness(self) -> list[(int, int)]:
        # num_guesses -> (row, col)
        ranked_cells = {}

        for r in range(9):
            for c in range(9):
                num_possible = len(self.cell_possible[r][c])
                # Don't take solved cells into account
                if num_possible != 1:
                    if num_possible not in ranked_cells:
                        ranked_cells[num_possible] = []
                    ranked_cells[num_possible].append((r, c))

        # flatten to list
        cells = []
        for easiness_factor in sorted(ranked_cells.keys()):
            for cell in ranked_cells[easiness_factor]:
                cells.append(cell)
        return cells

    def update_possibilities(self):
        # the board itself is the primary source of truth. Everything else is just for convenience
        self.update_rows_and_columns_from_solved_cells()
        self.update_cell_possibilities()
        self.update_row_column_possibilities()

        self.assert_consistency()

    def assert_consistency(self):
        for r in range(9):
            for c in range(9):
                assert_constraint(len(self.cell_possible[r][c]) != 0, f"No possible values for cell {r, c}")
                if self.board[r][c] is not None:
                    assert_constraint(self.board[r][c] not in self.row_remaining, f"Solved cell still assignable in row {r}")
                    assert_constraint(self.board[r][c] not in self.col_remaining, f"Solved cell still assignable in column {c}")
                    assert_constraint(self.board[r][c] == self.cell_possible[r][c][0], f"Solved cell {r, c} marked impossible")
                    assert_constraint(len(self.cell_possible[r][c]) == 1, f"Cell {r, c} was solved but still has possibilities: {self.cell_possible[r][c]}")

                    if self.expected_solution is not None:
                        expected = self.expected_solution[r][c]
                        actual = self.board[r][c]
                        assert_constraint(actual == expected, f"Cell {r, c} has value of {actual} did not match expected value {expected}")

                if len(self.cell_possible[r][c]) == 1:
                    # if there are no more possibiliites, yet this cell has not been solved, there is a bug
                    assert_constraint(
                        self.board[r][c] is not None,
                        f"Cell {r, c} has no more possible values but wasn't marked on the board")

        # no two values in the same column:
        self.check_rows()

        # no two values in the same row:
        self.check_columns()

        # no two values in the same section
        # TODO: this can be a loop
        self.check_section(0, 3, 0, 3)
        self.check_section(0, 3, 3, 6)
        self.check_section(0, 3, 6, 9)

        self.check_section(3, 6, 0, 3)
        self.check_section(3, 6, 3, 6)
        self.check_section(3, 6, 6, 9)

        self.check_section(6, 9, 0, 3)
        self.check_section(6, 9, 3, 6)
        self.check_section(6, 9, 6, 9)

    def check_rows(self):
        for r in range(9):
            row_values = set()
            for c in range(9):
                value = self.board[r][c]
                if value:
                    assert_constraint(value not in row_values, f"Cell {r, c} value {value} is duplicatedd in row")
                    row_values.add(value)

    def check_columns(self):
        for c in range(9):
            col_values = set()
            for r in range(9):
                value = self.board[r][c]
                if value:
                    assert_constraint(self.board[r][c] not in col_values, f"Cell {r, c} is duplicated in column")
                    col_values.add(value)

    def check_section(self, start_row, end_row, start_col, end_col):
        nums_in_section = set()
        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                assert_constraint(
                    self.board[r][c] not in nums_in_section,
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

    def update_rows_and_columns_from_solved_cells(self):
        for r in range(9):
            for c in range(9):
                cell_value = self.board[r][c]

                if cell_value in self.row_remaining[r]:
                    self.remove_row_possibility(r, cell_value)

                if cell_value in self.col_remaining[c]:
                    self.remove_col_possibility(c, cell_value)

    def update_row_column_possibilities(self):
        for r in range(9):
            possible_from_cells = set()
            # what is possible for the row is the union of what is avaible in every cell
            for c in range(9):
                # If a cell has been solved, skip it. Only interetsted in what is *left* for a row.
                if len(self.cell_possible[r][c]) != 1:
                    possible_from_cells.update(self.cell_possible[r][c])
            self.row_remaining[r] = list(possible_from_cells.intersection(self.row_remaining[r]))

        for c in range(9):
            possible_from_cells = set()
            for r in range(9):
                # If a cell has been solved, skip it. Only interetsted in what is *left* for a row.
                if len(self.cell_possible[r][c]) != 1:
                    possible_from_cells.update(self.cell_possible[r][c])
            self.col_remaining[c] = list(possible_from_cells.intersection(self.col_remaining[c]))

    def update_cell_possibilities(self):
        for r in range(9):
            for c in range(9):
                if self.board[r][c] is None:
                    self.cell_possible[r][c] = list(
                        set(self.row_remaining[r])
                        .union(self.col_remaining[c])
                        .intersection(set(self.cell_possible[r][c])))

                    if len(self.cell_possible[r][c]) == 1:
                        self.update_board(r, c, self.cell_possible[r][c][0])
                else:
                    self.cell_possible[r][c] = [self.board[r][c]]

    def update_board(self, row, column, value):
        if self.expected_solution is not None:
            expected = self.expected_solution[row][column]
            assert_constraint(value == expected, f"Cell {row, column} was {value}, but expected {expected}")

        self.board[row][column] = value
        if value in self.row_remaining:
            self.row_remaining.remove(value)
        if value in self.col_remaining:
            self.col_remaining.remove(value)
        self.cell_possible[row][column] = [value]

    def remove_row_possibility(self, row, value):
        if value in self.row_remaining[row]:
            self.row_remaining[row].remove(value)

            if len(self.row_remaining[row]) == 1:
                # We can solve a cell. Find which column it is.
                for col in range(9):
                    if self.board[row][col] is None:
                        self.update_board(row, col, self.row_remaining[row][0])

    def remove_col_possibility(self, col, value):
        if value in self.col_remaining[col]:
            self.col_remaining[col].remove(value)

            if len(self.col_remaining[col]) == 1:
                # We can solve a cell. Find which row it is.
                for row in range(9):
                    if self.board[row][col] is None:
                        self.update_board(row, col, self.col_remaining[col][0])

    def attempt_section(self):
        changed = False

        # look at each of the 3x3 sections
        changed = self.attempt_range(0, 3, 0, 3) or changed
        changed = self.attempt_range(0, 3, 3, 6) or changed
        changed = self.attempt_range(0, 3, 6, 9) or changed

        changed = self.attempt_range(3, 6, 0, 3) or changed
        changed = self.attempt_range(3, 6, 3, 6) or changed
        changed = self.attempt_range(3, 6, 6, 9) or changed

        changed = self.attempt_range(6, 9, 0, 3) or changed
        changed = self.attempt_range(6, 9, 3, 6) or changed
        changed = self.attempt_range(6, 9, 6, 9) or changed

        return changed

    # start values are inclusive
    # end values are exclusive
    def attempt_range(self, start_row, end_row, start_col, end_col):
        values_in_section = []

        changed = False
        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                if self.board[r][c] is not None:
                    values_in_section.append(self.board[r][c])

        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                for val in values_in_section:
                    # anything in the same section is not possible for this cell
                    if val in self.cell_possible[r][c] and len(self.cell_possible[r][c]) != 1:
                        self.cell_possible[r][c].remove(val)
                        if len(self.cell_possible) == 1:
                            self.update_board(r, c, val)
                            changed = True

        return changed

    def check_intersections(self) -> bool:
        """
        If A is the set of possible values for row i, and B is the set of possible values in column j, then
        intersect(Ai, Bj) are the possible values for cell i,j.
        """
        changed = False
        for r in range(9):
            for c in range(9):
                # if it's known already, skip it
                if self.board[r][c] is not None:
                    continue

                intersection = [v for v in self.row_remaining[r] if v in self.col_remaining[c]]
                if len(intersection) == 1:
                    self.update_board(r, c, intersection[0])
                    changed = True
        return changed

    def check_known(self):
        changed = False
        for r_num, row_vals in enumerate(self.row_remaining):
            # if there is only one possibility for the row, we can fill it in
            if len(row_vals) == 1:
                new_val = row_vals[0]
                unknown_cols = [i for i, v in enumerate(self.board[r_num]) if v is None]
                assert_constraint(
                    len(unknown_cols) == 1,
                    f"The only possibility for the row was {new_val} but there were {len(unknown_cols)} left on the board")
                self.update_board(r_num, unknown_cols[0], new_val)
                changed = True

        for c_num, col_vals in enumerate(self.col_remaining):
            # if there is only one possibility for the column, we can fill it in
            if len(col_vals) == 1:
                new_val = col_vals[0]
                unknown_rows = [i for i, row in enumerate(self.board) if row[c_num] is None]
                assert_constraint(
                    len(unknown_rows) == 1,
                    f"The only possibility for the colum was {new_val} but there were {len(unknown_rows)} left on the board")
                self.update_board(unknown_rows[0], c_num, new_val)
                changed = True

        return changed

    @staticmethod
    def print_success_stats(num_iterations, millis):
        print("Solved in", num_iterations, "iterations")
        print("Took", round(millis, 4), "milliseconds")

    @staticmethod
    def print_failure_stats(num_iterations, millis):
        print("Could not solve puzzle")
        print("Took", round(millis, 4), "milliseconds")


class BoardPrinter(object):
    def __init__(self, board: list[list[int]]):
        self.board = board

    def pretty_print(self):
        for i, row in enumerate(self.board):
            print(self.format_row(row))
            if (i + 1) % 3 == 0:
                print(''.join([' ' for _ in range(26)]))

    @staticmethod
    def format_row(row: list[int]) -> str:
        characters = []
        for i, v in enumerate(row):
            if v:
                characters.append(str(v))
            else:
                characters.append('.')
            if (i + 1) % 3 == 0 and i < len(row) - 1:
                characters.append(' ')
        return ' '.join(characters)


class StatsTracker(object):
    def __init__(self):
        self.num_iterations = None
        self.num_guesses = 0
        self.guesses = [[[] for _ in range(1, 10)] for _ in range(1, 10)]

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

    def add_guess(self, row, col, guess):
        self.guesses[row][col].append(guess)

    def get_guesses(self):
        return self.guesses


def main():
    x = None
    # solver = Solver(
    #     [[x, x, x, 8, x, 5, x, 1, 3],
    #      [x, x, x, 2, x, 3, 6, x, x],
    #      [6, x, x, x, 9, x, 2, x, 4],
    #      [x, x, x, x, x, x, x, x, 5],
    #      [x, 4, x, 1, x, x, 7, x, 6],
    #      [2, 5, 6, 3, x, 4, 8, 9, x],
    #      [5, 9, x, x, x, 7, 1, x, 2],
    #      [1, x, 2, x, 8, x, 4, 7, x],
    #      [x, x, 4, 9, 1, x, x, 3, 8]],
    #
    #     [[4, 2, 7, 8, 6, 5, 9, 1, 3],
    #      [9, 1, 5, 2, 4, 3, 6, 8, 7],
    #      [6, 8, 3, 7, 9, 1, 2, 5, 4],
    #      [8, 7, 1, 6, 2, 9, 3, 4, 5],
    #      [3, 4, 9, 1, 5, 8, 7, 2, 6],
    #      [2, 5, 6, 3, 7, 4, 8, 9, 1],
    #      [5, 9, 8, 4, 3, 7, 1, 6, 2],
    #      [1, 3, 2, 5, 8, 6, 4, 7, 9],
    #      [7, 6, 4, 9, 1, 2, 5, 3, 8]]
    # )
    # solver.solve()

    solver = Solver(
        [[9, x, 5, 4, x, x, 6, x, 7],
         [x, x, x, 9, x, 7, x, x, x],
         [4, 2, x, x, x, x, 9, 1, x],
         [5, x, 8, x, x, x, x, x, x],
         [x, x, x, x, 6, 5, x, x, x],
         [x, x, x, 1, x, 9, x, x, x],
         [x, x, 6, x, x, 3, 8, x, x],
         [x, x, x, x, 8, x, x, 2, 6],
         [8, x, x, 2, x, 6, 3, 4, x]],

        None
        # [[9, 1, 5, 4, 3, 2, 6, 8, 7],
        #  [6, 8, 3, 9, 1, 7, 2, 5, 4],
        #  [4, 2, 7, 6, 5, 8, 9, 1, 3],
        #  [5, 9, 8, 3, 7, 4, 1, 6, 2],
        #  [1, 3, 2, 8, 6, 5, 4, 7, 9],
        #  [7, 6, 4, 1, 2, 9, 5, 3, 8],
        #  [2, 5, 6, 7, 4, 3, 8, 9, 1],
        #  [3, 4, 9, 5, 8, 1, 7, 2, 6],
        #  [8, 7, 1, 2, 9, 6, 3, 4, 5]]
    )
    solver.solve()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
