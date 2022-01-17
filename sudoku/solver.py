from exceptions import ConstraintViolationError
from solver_state import SolverState
from stats import StatsTracker


class Solver(object):
    def __init__(self, board, expected_solution=None):
        self.state = SolverState(board)
        self.expected_solution = expected_solution

    def solve(self):
        stats = StatsTracker()

        stats.start_timer()
        self.solve_recursively(stats, 0)
        stats.stop_timer()

        BoardPrinter(self.state.board).pretty_print()

        if self.state.is_solved():
            if self.expected_solution:
                self.state.compare_to_expected(self.expected_solution)
            self.print_success_stats(stats)
        else:
            self.print_failure_stats(stats)

    def solve_recursively(self, stats_tracker, recursion_depth) -> bool:
        stats_tracker.on_recursion(recursion_depth)

        # Using what is known, get as many cells as possible using the game constraints.
        try:
            self.make_consistent()
            stats_tracker.num_iterations += self.iteratively_solve()
            if self.state.is_solved():
                return True
        except ConstraintViolationError:
            return False

        for row in range(8):
            for col in range(8):
                # scan to the first unsolved space
                if self.state.cell_solved(row, col):
                    continue

                state_before_all_guesses = self.state.copy()

                for guess in self.state.get_possible_for_cell(row, col):
                    state_before_this_guess = self.state.copy()

                    # if this guess was invalid from the start, then move on
                    try:
                        self.state.update_board(row, col, guess)
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

    def iteratively_solve(self) -> int:
        changed = True
        num_iterations = 0
        while changed:
            num_iterations += 1
            changed = False

            if self.check_intersections():
                self.make_consistent()
                changed = True

            if self.check_for_single_possibilities():
                self.make_consistent()
                changed = True

            # Can't repeat a number within a 3x3 section, so filter the possibilities
            if self.attempt_section():
                self.make_consistent()
                changed = True

        return num_iterations

    def make_consistent(self):
        """
        If any cells have been solved or narrowed down, update all the possibility lists so they are consistent
        """
        self.update_rows_and_columns_from_solved_cells()
        self.update_cell_possibilities()
        self.update_row_column_possibilities()

        self.state.assert_still_valid()

    def update_rows_and_columns_from_solved_cells(self):
        for r in range(9):
            for c in range(9):
                cell_value = self.state.board_at(r, c)

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
                if self.state.board_at(r, c) is None:
                    self.compute_new_cell_possibilities(r, c)

                    if len(self.state.get_possible_for_cell(r, c)) == 1:
                        self.state.update_board(r, c, self.state.get_possible_for_cell(r, c)[0])
                else:
                    self.state.set_cell_possibilities(r, c, [self.state.board_at(r, c)])

    def compute_new_cell_possibilities(self, row, column):
        current_possible = set(self.state.row_remaining[row]).union(self.state.col_remaining[column])
        old_possible = set(self.state.get_possible_for_cell(row, column))

        # apply the updated information but intersect it with the old info so we don't go backward
        self.state.set_cell_possibilities(row, column, list(current_possible.intersection(old_possible)))

    def remove_row_possibility(self, row, value):
        if value in self.state.row_remaining[row]:
            self.state.row_remaining[row].remove(value)

            if len(self.state.row_remaining[row]) == 1:
                # We can solve a cell. Find which column it is.
                for col in range(9):
                    if self.state.board_at(row, col) is None:
                        self.state.update_board(row, col, self.state.row_remaining[row][0])

    def remove_col_possibility(self, col, value):
        if value in self.state.col_remaining[col]:
            self.state.col_remaining[col].remove(value)

            if len(self.state.col_remaining[col]) == 1:
                # We can solve a cell. Find which row it is.
                for row in range(9):
                    if not self.state.cell_solved(row, col):
                        self.state.update_board(row, col, self.state.col_remaining[col][0])

    def attempt_section(self) -> bool:
        changed = False

        # look at each of the 3x3 sections
        for start_row in range(0, 7, 3):
            for start_col in range(0, 7, 3):
                # changed = self.attempt_range(start_row, start_row + 3, start_col, start_col + 3) or changed
                changed = self.attempt_range((start_row, start_col), (start_row + 3, start_col + 3)) or changed

        return changed

    # start values are inclusive
    # end values are exclusive
    def attempt_range(self, start_cell: (int, int), end_cell: (int, int)) -> bool:
        """
        Solve as much as possible in a given section (defined by a range of cells)

        Arguments:
            start_cell: the (row, column) of the cell at the beginning of the range
            end_cell: the (row, column) of the cell at the end of the range (non-inclusive)
        """
        start_row = start_cell[0]
        start_col = start_cell[1]
        end_row = end_cell[0]
        end_col = end_cell[1]
        changed = False
        values_in_section = self.state.get_values_in_range((start_row, start_col), (end_row, end_col))

        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                # anything in the same section is not possible for this cell
                for val in values_in_section:
                    # remove it as a possibility unless this has been solved
                    if len(self.state.get_possible_for_cell(r, c)) != 1:
                        changed = self.state.mark_value_impossible(r, c, val)
                        if len(self.state.get_possible_for_cell(r, c)) == 1:
                            self.state.update_board(r, c, self.state.get_possible_for_cell(r, c)[0])

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
                # for each unknown cell
                if not self.state.cell_solved(r, c):
                    intersection = set(self.state.row_remaining[r]).intersection(self.state.col_remaining[c])
                    if len(intersection) == 1:
                        self.state.update_board(r, c, intersection.pop())
                        changed = True
        return changed

    def check_for_single_possibilities(self) -> bool:
        changed = False
        for r_num, row_vals in enumerate(self.state.row_remaining):
            # if there is only one possibility for the row, we can fill it in
            if len(row_vals) == 1:
                new_val = row_vals[0]
                unknown_cols = [i for i, v in enumerate(self.state.get_row(r_num)) if v is None]
                assert(len(unknown_cols) == 1)
                self.state.update_board(r_num, unknown_cols[0], new_val)
                changed = True

        for c_num, col_vals in enumerate(self.state.col_remaining):
            # if there is only one possibility for the column, we can fill it in
            if len(col_vals) == 1:
                new_val = col_vals[0]
                unknown_rows = [row_num for row_num, val in enumerate(self.state.get_column(c_num)) if val is None]
                assert(len(unknown_rows) == 1)
                self.state.update_board(unknown_rows[0], c_num, new_val)
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
