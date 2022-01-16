import time


class Solver(object):
    def __init__(self, board, expected_solution=None):
        self.board = board
        self.expected_solution = expected_solution

        # start with any number possible in any cell and filter down
        self.row_possible = [[i for i in range(1, 10)] for _ in range(1, 10)]
        self.col_possible = [[i for i in range(1, 10)] for _ in range(1, 10)]

        # cell_possibles[row][col] gives the possible values for each cell
        self.cell_possible = [[[i for i in range(1, 10)] for _ in range(1, 10)] for _ in range(1, 10)]

    def init_row_possibilities(self):
        possible_by_row = [[i for i in range(1, 10)] for _ in range(1, 10)]
        for r in range(9):
            row = self.board[r]
            for c in range(9):
                cell_value = row[c]
                if cell_value in possible_by_row[r]:
                    possible_by_row[r].remove(cell_value)
        return possible_by_row

    def init_col_possibilities(self):
        possible_by_col = [[i for i in range(1, 10)] for _ in range(1, 10)]
        for c in range(9):
            col = self.board[c]
            for r in range(9):
                cell_value = col[r]
                if cell_value in possible_by_col[c]:
                    possible_by_col[c].remove(cell_value)
        return possible_by_col

    def solve(self):
        start_time = time.time()

        self.update_possibilities()

        # Apply a series of filters until we can't get anymore. After that we have to start guessing and seeing
        # where it goes.
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

        end_time = time.time()
        self.pretty_print()
        self.print_stats(num_iterations, end_time - start_time)

    def update_possibilities(self):
        # the board itself is the primary source of truth. Everything else is just for convenience
        self.update_rows_and_columns_from_solved_cells()
        self.update_cell_possibilities()
        self.update_row_column_possibilities()

        self.assert_consistency()

    def assert_consistency(self):
        for r in range(8):
            for c in range(8):
                if self.board[r][c] is not None:
                    assert(self.board[r][c] not in self.row_possible)
                    assert(self.board[r][c] not in self.col_possible)
                    assert(self.board[r][c] not in self.cell_possible)
                    assert(len(self.cell_possible[r][c]) == 1)

                    if self.expected_solution is not None:
                        assert(self.board[r][c] == self.expected_solution[r][c])

    def update_rows_and_columns_from_solved_cells(self):
        for r in range(9):
            for c in range(9):
                cell_value = self.board[r][c]

                if cell_value in self.row_possible[r]:
                    self.remove_row_possibility(r, cell_value)

                if cell_value in self.col_possible[c]:
                    self.remove_col_possibility(c, cell_value)

    def update_row_column_possibilities(self):
        for r in range(9):
            possible_from_cells = set()
            # what is possible for the row is the union of what is avaible in every cell
            for c in range(9):
                # If a cell has been solved, skip it. Only interetsted in what is *left* for a row.
                if len(self.cell_possible[r][c]) != 1:
                    possible_from_cells.update(self.cell_possible[r][c])
            # TODO: the problem is that when cell_possible[r][c] is 1, we remove it from row_possible, and then it uses
            #       the fact that it's not possible later on in the intersection calculation
            self.row_possible[r] = list(possible_from_cells.intersection(self.row_possible[r]))

        for c in range(9):
            possible_from_cells = set()
            for r in range(9):
                # If a cell has been solved, skip it. Only interetsted in what is *left* for a row.
                if len(self.cell_possible[r][c]) != 1:
                    possible_from_cells.update(self.cell_possible[r][c])
            self.col_possible[c] = list(possible_from_cells.intersection(self.col_possible[c]))

    def update_cell_possibilities(self):
        for r in range(9):
            for c in range(9):
                if self.board[r][c] is None:
                    # TODO: the possibility list should probably all be sets to avoid copyinng the data
                    self.cell_possible[r][c] = list(
                        set(self.row_possible[r])
                        .union(self.col_possible[c])
                        .intersection(set(self.cell_possible[r][c])))

                    if len(self.cell_possible[r][c]) == 1:
                        self.update_board(r, c, self.cell_possible[r][c][0])
                else:
                    self.cell_possible[r][c] = [self.board[r][c]]

    def update_board(self, row, column, value):
        if self.expected_solution is not None:
            assert(value == self.expected_solution[row][column])

        self.board[row][column] = value
        if value in self.row_possible:
            self.row_possible.remove(value)
        if value in self.col_possible:
            self.col_possible.remove(value)
        self.cell_possible[row][column] = [value]

    def remove_row_possibility(self, row, value):
        if value in self.row_possible[row]:
            self.row_possible[row].remove(value)

            if len(self.row_possible[row]) == 1:
                # We can solve a cell. Find which column it is.
                for col in range(8):
                    if self.board[row][col] is None:
                        self.update_board(row, col, self.row_possible[row][0])

    def remove_col_possibility(self, col, value):
        if value in self.col_possible[col]:
            self.col_possible[col].remove(value)

            if len(self.col_possible[col]) == 1:
                # We can solve a cell. Find which row it is.
                for row in range(8):
                    if self.board[row][col] is None:
                        self.update_board(row, col, self.col_possible[col][0])

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
                    if val in self.cell_possible[r][c]:
                        self.cell_possible[r][c].remove(val)
                        if len(self.cell_possible) == 1:
                            self.update_board(r, c, val)
                            changed = True

                        if len(self.cell_possible[r][c]) == 0:
                            # if there are no more possibiliites, yet this cell has not been solved, there is a bug
                            assert(self.board[r][c] is not None)

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

                intersection = [v for v in self.row_possible[r] if v in self.col_possible[c]]
                if len(intersection) == 1:
                    self.update_board(r, c, intersection[0])
                    changed = True
        return changed

    def check_known(self):
        changed = False
        for r_num, row_vals in enumerate(self.row_possible):
            # if there is only one possibility for the row, we can fill it in
            if len(row_vals) == 1:
                new_val = row_vals[0]
                unknowns = [i for i, v in enumerate(self.board[r_num]) if v is None]
                assert(len(unknowns) == 1)
                self.board[r_num][unknowns[0]] = new_val
                changed = True

        for c_num, col_vals in enumerate(self.col_possible):
            # if there is only one possibility for the column, we can fill it in
            if len(col_vals) == 1:
                new_val = col_vals[0]
                unknowns = [i for i, row in enumerate(self.board) if row[c_num] is None]
                assert(len(unknowns) == 1)
                self.board[unknowns[0]][c_num] = new_val
                changed = True

        return changed

    def print_stats(self, num_iterations, millis):
        print("Solved in", num_iterations, "iterations")
        print("Took", round(millis, 4), "milliseconds")

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
                characters.append(' ')
            if (i + 1) % 3 == 0 and i < len(row) - 1:
                characters.append(' ')
        return ' '.join(characters)

def main():
    x = None
    solver = Solver(
        [[x, x, x, 8, x, 5, x, 1, 3],
         [x, x, x, 2, x, 3, 6, x, x],
         [6, x, x, x, 9, x, 2, x, 4],
         [x, x, x, x, x, x, x, x, 5],
         [x, 4, x, 1, x, x, 7, x, 6],
         [2, 5, 6, 3, x, 4, 8, 9, x],
         [5, 9, x, x, x, 7, 1, x, 2],
         [1, x, 2, x, 8, x, 4, 7, x],
         [x, x, 4, 9, 1, x, x, 3, 8]],

        [[4, 2, 7, 8, 6, 5, 9, 1, 3],
         [9, 1, 5, 2, 4, 3, 6, 8, 7],
         [6, 8, 3, 7, 9, 1, 2, 5, 4],
         [8, 7, 1, 6, 2, 9, 3, 4, 5],
         [3, 4, 9, 1, 5, 8, 7, 2, 6],
         [2, 5, 6, 3, 7, 4, 8, 9, 1],
         [5, 9, 8, 4, 3, 7, 1, 6, 2],
         [1, 3, 2, 5, 8, 6, 4, 7, 9],
         [7, 6, 4, 9, 1, 2, 5, 3, 8]]
    )
    solver.solve()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
