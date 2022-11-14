# -*- coding: utf-8 -*-

"""Bresenham algorithm for line drawing."""


def line(x0, y0, x1, y1):
    """returns list of indices of pixels for the line from (x0, y0) to (x1, y1)

    both ends are included.

    Parameters
    ----------
    x0 : int
        row of first point
    y0 : int
        col of first point
    x1 : int
        row of second point
    y1 : int
        col of second point

    Examples
    --------
    >>> from insarviz.bresenham import line
    >>> import numpy as np
    >>> X0, Y0, X1, Y1 = 0, 0, 4, 3
    >>> res = line(X0, Y0, X1, Y1)
    >>> print(res, type(res)==list, type(res[0])==tuple)
    [(0, 0), (1, 1), (2, 2), (3, 2), (4, 3)] True True
    """

    idxs = []
    dx, dy = x1-x0, y1-y0

    xsign = 1 if dx > 0 else -1
    ysign = 1 if dy > 0 else -1

    dx, dy = abs(dx), abs(dy)

    if dx > dy:
        xx, xy, yx, yy = xsign, 0, 0, ysign
    else:
        dx, dy = dy, dx
        xx, xy, yx, yy = 0, ysign, xsign, 0

    D = 2*dy - dx
    y = 0

    for x in range(dx + 1):
        idxs += [(x0 + x*xx + y*yx, y0 + x*xy + y*yy)]
        if D >= 0:
            y += 1
            D -= 2*dx
        D += 2*dy
    return idxs


# example:
# import numpy as np
# X0, Y0, X1, Y1 = 0, 0, 4, 3
# res = line(X0, Y0, X1, Y1)
# print(res, type(res)==list, type(res[0])==tuple)

# selmap = np.zeros((15,5))
# for i in res:
#     selmap[i] = 1.

# print('selmap: \n', selmap)


# X1, Y1, X2, Y2 = 4, 3, 8, 3
# res2 = line(X1, Y1, X2, Y2)
# print(res2)

# for i in res2:
#     selmap[i] = 1.

# print('selmap 2nd time: \n', selmap)

# X2, Y2, X3, Y3 = 8, 3, 7, 0
# res3 = line(X2, Y2, X3, Y3)
# print(res3)

# for i in res3:
#     selmap[i] = 1.

# print('selmap 3nd time: \n', selmap)