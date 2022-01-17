import time
from exceptions import ConstraintViolationError
from solver_state import SolverState
from utils import assert_constraint


class Solver(object):
    def __init__(self, board, expected_solution=None):
        self.state = SolverState(board, expected_solution)

    def solve(self):
        stats = StatsTracker()

        stats.start_timer()
        self.solve_recursively(stats, 0)
        stats.stop_timer()

        BoardPrinter(self.state.board).pretty_print()

        if self.state.is_solved():
            self.print_success_stats(stats)
        else:
            self.print_failure_stats(stats)

    def solve_recursively(self, stats_tracker, recursion_depth) -> bool:
        stats_tracker.on_recursion(recursion_depth)

        # Using what is known, get as many cells as possible using the game constraints.
        try:
            self.update_possibilities()
            stats_tracker.num_iterations += self.iteratively_solve()
            if self.state.is_solved():
                return True
        except ConstraintViolationError:
            return False

        for row in range(8):
            for col in range(8):
                # scan to the first unsolved space
                if self.state.board[row][col] is not None:
                    continue

                state_before_all_guesses = self.state.copy()

                for guess in self.state.get_possible_for_cell(row, col):
                    state_before_this_guess = self.state.copy()

                    # if this guess was invalid from the start, then move on
                    try:
                        self.update_board(row, col, guess)
                    except ConstraintViolationError:
                        self.state = state_before_this_guess

                    # if this guess did not eventually lead to a correct solution
                    if not self.solve_recursively(stats_tracker, recursion_depth + 1):
                        self.state = state_before_this_guess

                # if none of the guesses worked
                if not self.state.is_solved():
                    self.state = state_before_all_guesses
                    return False

        return True

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

    def update_possibilities(self):
        # the board itself is the primary source of truth. Everything else is just for convenience
        self.update_rows_and_columns_from_solved_cells()
        self.update_cell_possibilities()
        self.update_row_column_possibilities()

        self.state.assert_consistency()

    def update_rows_and_columns_from_solved_cells(self):
        for r in range(9):
            for c in range(9):
                cell_value = self.state.board[r][c]

                if cell_value in self.state.row_remaining[r]:
                    self.remove_row_possibility(r, cell_value)

                if cell_value in self.state.col_remaining[c]:
                    self.remove_col_possibility(c, cell_value)

    def update_row_column_possibilities(self):
        for r in range(9):
            possible_from_cells = set()
            # what is possible for the row is the union of what is avaible in every cell
            for c in range(9):
                # If a cell has been solved, skip it. Only interetsted in what is *left* for a row.
                if len(self.state.get_possible_for_cell(r, c)) != 1:
                    possible_from_cells.update(self.state.get_possible_for_cell(r, c))
            self.state.row_remaining[r] = list(possible_from_cells.intersection(self.state.row_remaining[r]))

        for c in range(9):
            possible_from_cells = set()
            for r in range(9):
                # If a cell has been solved, skip it. Only interetsted in what is *left* for a row.
                if len(self.state.get_possible_for_cell(r, c)) != 1:
                    possible_from_cells.update(self.state.get_possible_for_cell(r, c))
            self.state.col_remaining[c] = list(possible_from_cells.intersection(self.state.col_remaining[c]))

    def update_cell_possibilities(self):
        for r in range(9):
            for c in range(9):
                if self.state.board[r][c] is None:
                    self.compute_new_cell_possibilities(r, c)

                    if len(self.state.get_possible_for_cell(r, c)) == 1:
                        self.update_board(r, c, self.state.get_possible_for_cell(r, c)[0])
                else:
                    self.state.set_cell_possibilities(r, c, [self.state.board[r][c]])

    def compute_new_cell_possibilities(self, row, column):
        current_possible = set(self.state.row_remaining[row]).union(self.state.col_remaining[column])
        old_possible = set(self.state.get_possible_for_cell(row, column))

        # apply the updated information but intersect it with the old info so we don't go backward
        self.state.cell_possible[row][column] = list(current_possible.intersection(old_possible))

    def update_board(self, row, column, value):
        if self.state.expected_solution is not None:
            expected = self.state.expected_solution[row][column]
            assert_constraint(value == expected, f"Cell {row, column} was {value}, but expected {expected}")

        self.state.board[row][column] = value
        if value in self.state.row_remaining:
            self.state.row_remaining.remove(value)
        if value in self.state.col_remaining:
            self.state.col_remaining.remove(value)
        self.state.set_cell_possibilities(row, column, [value])

    def remove_row_possibility(self, row, value):
        if value in self.state.row_remaining[row]:
            self.state.row_remaining[row].remove(value)

            if len(self.state.row_remaining[row]) == 1:
                # We can solve a cell. Find which column it is.
                for col in range(9):
                    if self.state.board[row][col] is None:
                        self.update_board(row, col, self.state.row_remaining[row][0])

    def remove_col_possibility(self, col, value):
        if value in self.state.col_remaining[col]:
            self.state.col_remaining[col].remove(value)

            if len(self.state.col_remaining[col]) == 1:
                # We can solve a cell. Find which row it is.
                for row in range(9):
                    if self.state.board[row][col] is None:
                        self.update_board(row, col, self.state.col_remaining[col][0])

    def attempt_section(self):
        changed = False

        # look at each of the 3x3 sections
        for start_row in range(0, 7, 3):
            for start_col in range(0, 7, 3):
                changed = self.attempt_range(start_row, start_row + 3, start_col, start_col + 3) or changed

        return changed

    # start values are inclusive
    # end values are exclusive
    def attempt_range(self, start_row, end_row, start_col, end_col):
        values_in_section = []

        changed = False
        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                if self.state.board[r][c] is not None:
                    values_in_section.append(self.state.board[r][c])

        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                # anything in the same section is not possible for this cell
                for val in values_in_section:
                    # don't remove the answer if this cell is solved
                    if len(self.state.get_possible_for_cell(r, c)) != 1:
                        changed = self.state.mark_value_impossible(r, c, val)
                        # TODO: Why does it break when I uncomment this? Updating the board here seems to make sense
                        # if len(self.state.cell_possible[r][c]) == 1:
                        #     self.update_board(r, c, val)
                        #     changed = True

        return changed

    def check_intersections(self) -> bool:
        """
        This uses the possible values for each row and column to find whether any cell has only one possible choice.

        If A is the set of possible values for row i, and B is the set of possible values in column j, then
        intersect(Ai, Bj) are the possible values for cell i,j.
        """
        changed = False
        for r in range(9):
            for c in range(9):
                # if it's known already, skip it
                if self.state.board[r][c] is not None:
                    continue

                intersection = [v for v in self.state.row_remaining[r] if v in self.state.col_remaining[c]]
                if len(intersection) == 1:
                    self.update_board(r, c, intersection[0])
                    changed = True
        return changed

    def check_known(self):
        changed = False
        for r_num, row_vals in enumerate(self.state.row_remaining):
            # if there is only one possibility for the row, we can fill it in
            if len(row_vals) == 1:
                new_val = row_vals[0]
                unknown_cols = [i for i, v in enumerate(self.state.board[r_num]) if v is None]
                assert_constraint(
                    len(unknown_cols) == 1,
                    f"The only possibility for the row was {new_val} but there were {len(unknown_cols)} spaces left")
                self.update_board(r_num, unknown_cols[0], new_val)
                changed = True

        for c_num, col_vals in enumerate(self.state.col_remaining):
            # if there is only one possibility for the column, we can fill it in
            if len(col_vals) == 1:
                new_val = col_vals[0]
                unknown_rows = [i for i, row in enumerate(self.state.board) if row[c_num] is None]
                assert_constraint(
                    len(unknown_rows) == 1,
                    f"The only possibility for the colum was {new_val} but there were {len(unknown_rows)}  spaces left")
                self.update_board(unknown_rows[0], c_num, new_val)
                changed = True

        return changed

    @staticmethod
    def print_success_stats(stats):
        print(f"Took {round(stats.get_elapsed_time(), 4)} milliseconds")
        print(f"Solved in {stats.num_iterations} passes, with max recursion depth {stats.get_max_recursion_depth()}")

    @staticmethod
    def print_failure_stats(stats):
        print("Could not solve puzzle")
        print(f"Took {round(stats.get_elapsed_time(), 4)} milliseconds")
        print(f"Attempted {stats.num_iterations} passes and max recursion depth {stats.get_max_recursion_depth()}")


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
