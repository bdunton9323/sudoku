

# TODO: if I made this a class that stores the possibles and board I wouldn't have to pass everything around so much
def solve(board: list[list]):
    # start with any number possible in any cell and filter down
    row_possible = [[i for i in range(1, 10)] for _ in range(1, 10)]
    col_possible = [[i for i in range(1, 10)] for _ in range(1, 10)]

    # cell_possibles[row][col] gives the possible values for each cell
    cell_possible = [[[i for i in range(1, 10)] for _ in range(1, 10)] for _ in range(1, 10)]

    update_possibilities(row_possible, col_possible, cell_possible, board)

    # Apply a series of filters until we can't get anymore. After that we have to start guessing and seeing
    # where it goes.
    changed = True
    while changed:
        changed = False

        if check_intersections(row_possible, col_possible, board):
            update_possibilities(row_possible, col_possible, cell_possible, board)
            changed = True

        pretty_print(board)

        if check_known(row_possible, col_possible, board):
            update_possibilities(row_possible, col_possible, cell_possible, board)
            changed = True

        pretty_print(board)

        # Can't repeat a number within a 3x3 section, so filter the possibilities
        if attempt_section(row_possible, col_possible, cell_possible, board):
            update_possibilities(row_possible, col_possible, cell_possible, board)
            changed = True

    pretty_print(board)
    print_stats(row_possible, col_possible)


def update_possibilities(row_possible, col_possible, cell_possible, board):
    update_rows_and_columns_from_board(row_possible, col_possible, board)
    update_cells_from_rows_and_columns(cell_possible, row_possible, col_possible)
    update_rows_and_columns_from_cells(row_possible, col_possible, cell_possible)


def update_rows_and_columns_from_board(row_possible, col_possible, board):
    for r in range(9):
        for c in range(9):
            cell_value = board[r][c]

            if cell_value in row_possible[r]:
                row_possible[r].remove(cell_value)

            if cell_value in col_possible[c]:
                col_possible[c].remove(cell_value)


def update_rows_and_columns_from_cells(row_possible, col_possible, cell_possible):
    for r in range(9):
        possible_from_cells = set()
        for c in range(9):
            possible_from_cells.update(cell_possible[r][c])
        row_possible[r] = list(possible_from_cells.intersection(row_possible[r]))

    for c in range(9):
        possible_from_cells = set()
        for r in range(9):
            possible_from_cells.update(cell_possible[r][c])
        col_possible[c] = list(possible_from_cells.intersection(col_possible[c]))


def update_cells_from_rows_and_columns(cell_possible, row_possible, col_possible):
    for r in range(9):
        for c in range(9):
            # TODO: the possibility list should probably all be sets
            cell_possible[r][c] = list(set(row_possible[r]).union(col_possible[c]).intersection(set(cell_possible[r][c])))


def init_row_possibilities(board):
    possible_by_row = [[i for i in range(1, 10)] for _ in range(1, 10)]
    for r in range(9):
        row = board[r]
        for c in range(9):
            cell_value = row[c]
            if cell_value in possible_by_row[r]:
                possible_by_row[r].remove(cell_value)
    return possible_by_row


def init_col_possibilities(board):
    possible_by_col = [[i for i in range(1, 10)] for _ in range(1, 10)]
    for c in range(9):
        col = board[c]
        for r in range(9):
            cell_value = col[r]
            if cell_value in possible_by_col[c]:
                possible_by_col[c].remove(cell_value)
    return possible_by_col


def attempt_section(row_possible, col_possible, cell_possible, board):
    changed = False

    # look at each of the 3x3 sections
    changed = attempt_range(row_possible, col_possible, cell_possible, board, 0, 3, 0, 3) or changed
    changed = attempt_range(row_possible, col_possible, cell_possible, board, 0, 3, 3, 6) or changed
    changed = attempt_range(row_possible, col_possible, cell_possible, board, 0, 3, 6, 9) or changed

    changed = attempt_range(row_possible, col_possible, cell_possible, board, 3, 6, 0, 3) or changed
    changed = attempt_range(row_possible, col_possible, cell_possible, board, 3, 6, 3, 6) or changed
    changed = attempt_range(row_possible, col_possible, cell_possible, board, 3, 6, 6, 9) or changed

    changed = attempt_range(row_possible, col_possible, cell_possible, board, 6, 9, 0, 3) or changed
    changed = attempt_range(row_possible, col_possible, cell_possible, board, 6, 9, 3, 6) or changed
    changed = attempt_range(row_possible, col_possible, cell_possible, board, 6, 9, 6, 9) or changed

    return changed


# start values are inclusive
# end values are exclusive
def attempt_range(row_possible, col_possible, cell_possible, board, start_row, end_row, start_col, end_col):
    values_in_section = []

    changed = False
    for r in range(start_row, end_row):
        for c in range(start_col, end_col):
            if board[r][c] is not None:
                values_in_section.append(board[r][c])

    for r in range(start_row, end_row):
        for c in range(start_col, end_col):
            for val in values_in_section:
                if val in cell_possible[r][c]:
                    cell_possible[r][c].remove(val)
                    if len(cell_possible[r][c]) == 0:
                        changed = True
                        # if this space is already solved, there is bug somewhere
                        if board[r][c] is not None:
                            print("stop")
                        assert(board[r][c] is None)
                        board[r][c] = val

    return changed


def check_intersections(row_possible, col_possible, board) -> bool:
    """
    If A is the set of possible values for row i, and B is the set of possible values in column j, then
    intersect(Ai, Bj) are the possible values for cell i,j.
    """
    changed = False
    for r in range(9):
        for c in range(9):
            # if it's known already, skip it
            if board[r][c] is not None:
                continue

            # TODO: I think this is where it's failing. Maybe I need to collect all the changes and remove them all at the end
            #   so that it doesn't whittle away everything
            intersection = [v for v in row_possible[r] if v in col_possible[c]]
            # if this happens, something is invalid
            assert(len(intersection) != 0)
            if len(intersection) == 1:
                board[r][c] = intersection[0]
                row_possible[r].remove(intersection[0])
                col_possible[c].remove(intersection[0])
                changed = True
    return changed


def check_known(row_possible, col_possible, board):
    changed = False
    for r_num, row_vals in enumerate(row_possible):
        # if there is only one possibility for the row, we can fill it in
        if len(row_vals) == 1:
            new_val = row_vals[0]
            unknowns = [i for i, v in enumerate(board[r_num]) if v is None]
            assert(len(unknowns) == 1)
            board[r_num][unknowns[0]] = new_val
            changed = True

    for c_num, col_vals in enumerate(col_possible):
        # if there is only one possibility for the column, we can fill it in
        if len(col_vals) == 1:
            new_val = col_vals[0]
            unknowns = [i for i, row in enumerate(board) if row[c_num] is None]
            assert(len(unknowns) == 1)
            board[unknowns[0]][c_num] = new_val
            changed = True

    return changed


def print_stats(row_possible, col_possible):
    for i, r in enumerate(row_possible):
        print("row :", i, r)

    for i, c in enumerate(col_possible):
        print("col: ", i, c)


def pretty_print(board):
    for row in board:
        str_list = [str(v) for v in row]
        print(', '.join(str_list).replace('None', ' '))
    print()


def main():
    x = None
    solve(
        [[x, x, x, 8, x, 5, x, 1, 3],
         [x, x, x, 2, x, 3, 6, x, x],
         [6, x, x, x, 9, x, 2, x, 4],
         [x, x, x, x, x, x, x, x, 5],
         [x, 4, x, 1, x, x, 7, x, 6],
         [2, 5, 6, 3, x, 4, 8, 9, x],
         [5, 9, x, x, x, 7, 1, x, 2],
         [1, x, 2, x, 8, x, 4, 7, x],
         [x, x, 4, 9, 1, x, x, 3, 8]
         ]
    )

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()