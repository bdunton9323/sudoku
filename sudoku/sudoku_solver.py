from solver import Solver


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
