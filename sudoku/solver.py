from exceptions import ConstraintViolationError
from solver_state import SolverState
from stats import StatsTracker


class Solver(object):
    """
    Solves a Sudoku puzzle.

    The algorithm is structured as follows:
        1. Use the known cells to figure out what is possible in each row, column, 3x3 section, and cell
        2. Use the updated information to rule out possibilities and solve cells.
        3. Repeat 2 until we cannot get any more. Easier puzzles will be solved at this point.
        4. If it is still not solved, pick an empty cell and arbitrarily choose one of its possible values
        5. Repeat from step 1. If the assumption in step 4 resulted in an illegal board, revert and try a new value
        6. Repeat step 5 until board is solved.
    """
    def __init__(self, board, expected_solution=None):
        self.state = SolverState(board)
        self.expected_solution = expected_solution

    def solve(self):
        stats = StatsTracker()

        stats.start_timer()
        self.solve_recursively(stats, 0)
        stats.stop_timer()

        board_printer = BoardPrinter(self.state.board, self.expected_solution)

        if self.state.is_solved() and self.expected_solution and self.state.matches_expected(self.expected_solution):
            self.print_success_stats(stats)
            board_printer.pretty_print()
        else:
            self.print_failure_stats(stats)
            if self.expected_solution:
                board_printer.print_diff()

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

        for row in range(9):
            for col in range(9):
                # scan to the first unsolved space
                if self.state.is_cell_solved(row, col):
                    continue

                state_before_all_guesses = self.state.copy()

                for guess in self.state.get_choices_for_cell(row, col):
                    state_before_this_guess = self.state.copy()

                    # if this guess was invalid from the start, then move on
                    try:
                        self.state.update_board(row, col, guess)
                    except ConstraintViolationError:
                        self.state = state_before_this_guess

                    # if this guess did not eventually lead to a correct solution, then the guess was wrong
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

            # Check the intersections between the possible row and column values at each cell. If any have a single
            # point of intersection then we can solve it.
            if self.check_intersections():
                self.make_consistent()
                changed = True

            # Check to see if any cell has only one possible value
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

                if cell_value in self.state.get_choices_for_row(r):
                    self.remove_row_possibility(r, cell_value)

                if cell_value in self.state.get_choices_for_col(c):
                    self.remove_col_possibility(c, cell_value)

    def update_row_column_possibilities(self):
        """
        Brings the row and column choices into sync with the individual cell possibilites
        """
        for r in range(9):
            # what is possible for the row is what is possible in the cells in the row AND possible for row
            possible_from_cells = self.state.get_choices_for_cells_in_row(r)
            row_choices = self.state.get_choices_for_row(r)
            self.state.set_choices_for_row(r, list(set(row_choices).intersection(possible_from_cells)))

        for c in range(9):
            possible_from_cells = self.state.get_choices_for_cells_in_col(c)
            col_choices = self.state.get_choices_for_col(c)
            self.state.set_choices_for_col(c, list(set(col_choices).intersection(possible_from_cells)))

    def update_cell_possibilities(self):
        for r in range(9):
            for c in range(9):
                if self.state.board_at(r, c) is None:
                    self.compute_new_cell_possibilities(r, c)

                    if len(self.state.get_choices_for_cell(r, c)) == 1:
                        self.state.update_board(r, c, self.state.get_choices_for_cell(r, c)[0])
                else:
                    self.state.set_choices_for_cell(r, c, [self.state.board_at(r, c)])

    def compute_new_cell_possibilities(self, row, column):
        current_possible = set(self.state.get_choices_for_row(row)).union(self.state.get_choices_for_col(column))
        old_possible = set(self.state.get_choices_for_cell(row, column))

        # apply the updated information but intersect it with the old info so we don't go backward
        self.state.set_choices_for_cell(row, column, list(current_possible.intersection(old_possible)))

    def remove_row_possibility(self, row, value):
        if value in self.state.get_choices_for_row(row):
            self.state.mark_impossible_in_row(row, value)

            if len(self.state.get_choices_for_row(row)) == 1:
                # We can solve a cell. Find which column it is.
                for col in range(9):
                    if self.state.board_at(row, col) is None:
                        self.state.update_board(row, col, self.state.get_choices_for_row(row)[0])

    def remove_col_possibility(self, col, value):
        if value in self.state.get_choices_for_col(col):
            self.state.mark_impossible_in_col(col, value)

            if len(self.state.get_choices_for_col(col)) == 1:
                # We can solve a cell. Find which row it is.
                for row in range(9):
                    if not self.state.is_cell_solved(row, col):
                        self.state.update_board(row, col, self.state.get_choices_for_col(col)[0])

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
        values_in_section = self.state.get_unique_values_in_section((start_row, start_col), (end_row, end_col))

        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                # remove it as a possibility unless this has been solved
                if len(self.state.get_choices_for_cell(r, c)) != 1:
                    # anything in the same section is not possible for this cell
                    for val in values_in_section:
                        changed = self.state.mark_impossible_in_cell(r, c, val)
                        if len(self.state.get_choices_for_cell(r, c)) == 1:
                            self.state.update_board(r, c, self.state.get_choices_for_cell(r, c)[0])

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
                # for each unknown cell, intersect the possibilities for that row and column
                if not self.state.is_cell_solved(r, c):
                    row_choices = self.state.get_choices_for_row(r)
                    col_choices = self.state.get_choices_for_col(c)
                    intersection = set(row_choices).intersection(col_choices)
                    if len(intersection) == 1:
                        self.state.update_board(r, c, intersection.pop())
                        changed = True
        return changed

    def check_for_single_possibilities(self) -> bool:
        changed = False
        for r in range(9):
            remaining = self.state.get_choices_for_row(r)
            # if there is only one possibility for the column, we can fill it in on the board
            if len(remaining) == 1:
                unknown_cols = [i for i, v in enumerate(self.state.get_row(r)) if v is None]
                assert (len(unknown_cols) == 1)
                self.state.update_board(r, unknown_cols[0], remaining[0])
                changed = True

        for c in range(9):
            remaining = self.state.get_choices_for_col(c)
            # if there is only one possibility for the column, we can fill it in on the board
            if len(remaining) == 1:
                unknown_rows = [row_num for row_num, val in enumerate(self.state.get_column(c)) if val is None]
                assert(len(unknown_rows) == 1)
                self.state.update_board(unknown_rows[0], c, remaining[0])
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
    # ANSI escape sequence for colored text in terminal
    RED = '\033[91m'
    END_COLOR = '\033[0m'

    def __init__(self, result_board: list[list[int]], expected_board=None):
        if expected_board is not None and len(expected_board) != len(result_board):
            raise ValueError
        self.actual_board = result_board
        self.expected_board = expected_board

    def pretty_print(self):
        for i, row in enumerate(self.actual_board):
            print(self.format_row(row))
            if (i + 1) % 3 == 0:
                print(''.join([' ' for _ in range(26)]))

    def print_diff(self):
        for r, row in enumerate(self.actual_board):
            wrong_indexes = []
            for c in range(len(self.actual_board[r])):
                if self.actual_board[r][c] != self.expected_board[r][c]:
                    wrong_indexes.append(c)
                    print(f"{r, c} was {self.actual_board[r][c]} but expected {self.expected_board[r][c]}")
            print(self.format_row(row, wrong_indexes))
            if (r + 1) % 3 == 0:
                print(''.join([' ' for _ in range(26)]))

    def format_row(self, row: list[int], wrong_indexes=None) -> str:
        if wrong_indexes is None:
            wrong_indexes = []

        cells = []
        for i, v in enumerate(row):
            cell_value = str(v) if v else '.'

            if i in wrong_indexes:
                cells.append(self.RED + cell_value + self.END_COLOR)
            else:
                cells.append(cell_value)

            if (i + 1) % 3 == 0 and i < len(row) - 1:
                cells.append(' ')
        return ' '.join(cells)
