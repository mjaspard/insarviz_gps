#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Miscellaneous utils

# imports ###################################################################

import numpy as np
from itertools import product

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices

# utils #####################################################################

def get_nearest(array, value):
    """
    Look into an array to find the nearest value to input value.
    Nearest is defined as minimal absolute difference between tested values.
    Returns array value and index of the nearest array value.

    Example:
        a = numpy.array((1, 5, 13, 7))
        get_nearest(a, 8)
        (7, 3)
        get_nearest(a, 1.23)
        (1, 0)

    Parameters
    ----------
    array : array
        Array where to look for the nearest value.
    value : int or float
        Value whose nearest value we want to find in the array.

    Returns
    -------
    array[idx], idx : tuple
        Nearest value found in array, index of nearest value found in array.

    """
    array = np.asarray(array)
    idx = (np.abs(array-value)).argmin()
    return array[idx], idx


def get_neighbors_idxs(array, target, radius):
    """
    Get the indices (col, line) of the values neighboring a target index in an
    array, with a given radius
    Returns a tuple containing ((list of cols), (list of lines)) of the
    indexes to facilitate indexing in the array.
    NB: The target's index is excluded.

    Example
    -------
    mat = numpy.arange(36).reshape((6, 6))
    >> mat
    array([[ 0,  1,  2,  3,  4,  5],
           [ 6,  7,  8,  9, 10, 11],
           [12, 13, 14, 15, 16, 17],
           [18, 19, 20, 21, 22, 23],
           [24, 25, 26, 27, 28, 29],
           [30, 31, 32, 33, 34, 35]])

    tar = (1,2)
    neighbors = get_neighbors_idxs(mat, tar, 2)
    mat[neighbors] = -999

    >> neighbors
    ((0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3),
     (0, 1, 2, 3, 4, 0, 1, 3, 4, 0, 1, 2, 3, 4, 0, 1, 2, 3, 4))

    >> mat
    array([[-999, -999, -999, -999, -999,    5],
           [-999, -999,    8, -999, -999,   11],
           [-999, -999, -999, -999, -999,   17],
           [-999, -999, -999, -999, -999,   23],
           [  24,   25,   26,   27,   28,   29],
           [  30,   31,   32,   33,   34,   35]])

    Parameters
    ----------
    array : 2d array
        the array from which the neighbors indexes are extracted.
    target : tuple
        the target index which neighbors are looked for in the array.
    radius : int
        number of neighbors (away from target, in each direction, diagonals
        included) to be extracted.

    Returns
    -------
    tuple
        tuple of (list of cols, list of lines) of the neighbors' indexes.

    """
    a, b = target[0], target[1]
    neighbors = [(i, j) for i in range(a-radius, a+radius+1) for j in range(
        b-radius, b+radius+1) if i > -1 and j > -1 and j < len(
            array[0]) and i < len(array)]
    neighbors.remove((a, b))
    return tuple(zip(*neighbors))


def get_rectangle(point_1, point_2):
    """
    Given the indices of two input points point_1 and point_2, returns a list
    of the indices (col, line) of the pixels forming the rectangle between
    those corner points (the sides of the rectangle are parallel to col and
    line axes).

    Example
    -------
    get_rectangle([0,0],[2,3])
    >>> [(0, 0),
         (0, 1),
         (0, 2),
         (0, 3),
         (1, 0),
         (1, 1),
         (1, 2),
         (1, 3),
         (2, 0),
         (2, 1),
         (2, 2),
         (2, 3)]

    get_rectangle([0,0],[2,3]) == get_rectangle([2,3], [0,0])
    >>> True

    get_rectangle([2,3],[2,3])
    [(2, 3)]

    Parameters
    ----------
    point_1 : tuple or list
        indices (col, line) of the first point.
    point_2 : TYPE
        indices (col, line) of the second point.

    Returns
    -------
    tuple
        tuple of lists (col, line) of indices of all points forming the
        rectangle.

    """
    min_x = min(point_1[0], point_2[0])
    max_x = max(point_1[0], point_2[0])
    min_y = min(point_1[1], point_2[1])
    max_y = max(point_1[1], point_2[1])

    x_coords = [x for x in range(min_x, max_x + 1)]
    y_coords = [y for y in range(min_y, max_y + 1)]

    return list(product(x_coords, y_coords))

def openUrl(self):
    """
    open url of documentation

    Returns
    -------
    None.

    """
    url = QUrl('https://deformvis.gricad-pages.univ-grenoble-alpes.fr/insarviz/index.html')  # noqa
    if not QDesktopServices.openUrl(url):
        QMessageBox.warning(self, 'Open Url', 'Could not open url')
