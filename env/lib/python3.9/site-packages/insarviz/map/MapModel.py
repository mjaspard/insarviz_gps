#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# imports ###################################################################

from PyQt5.QtCore import (
    QObject, pyqtSignal, pyqtSlot
    )

from OpenGL.GL import (
    glEnable, glGenTextures, glBindTexture,
    glTexParameter, glTexImage2D, glGenerateMipmap,
    glDisable, GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER,
    GL_NEAREST, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR,
    GL_LUMINANCE_ALPHA, GL_FLOAT,
    glActiveTexture, GL_TEXTURE0,
    )

import numpy as np
from scipy.interpolate import interp1d


from insarviz.map.Shaders import (
    DATA_UNIT, SEL_UNIT, PALETTE_UNIT
    )

from pyqtgraph import ImageItem

from insarviz.utils import get_neighbors_idxs

from insarviz.Interaction import IDLE, DRAG, ZOOM, POINTS, LIVE, PROFILE

from insarviz.bresenham import line

# map model #################################################################


class MapModel(QObject):
    """
    Model managing data for Map and Minimap
    """
    tex_id = 0  # tex id for data layer
    tex_width = 512
    tex_height = 512
    tex_vi = 0.  # min
    tex_va = 1.  # max

    sel_id = 0  # tex id for selection layer
    selection = None  # selection layer

    profile_points = []  # points selected by user for profile

    # signals
    texture_changed = pyqtSignal()
    bounds_changed = pyqtSignal()
    init_histo_vals = pyqtSignal(tuple)

    # init values for center and scale (zoom level)
    cx = tex_width // 2
    cy = tex_height // 2
    z = 1.

    i = -1           # current band

    # state variables
    map_istate = IDLE
    ready_for_POINTS = False
    ready_for_PROFILE = False
    ready_for_REF = False

    all_pointers_ij = None
    ref_pointers = None

    def __init__(self, loader, nMaxPoints):
        """MapModel

        Parameters
        ----------
        loader : QObject
            Loader used to load dataset from file.

        Returns
        -------
        None
        """

        super().__init__()
        self.loader = loader
        self.nMaxPoints = nMaxPoints
        self.textures = {}
        self.histograms = {}

    def show_band(self, i):
        """
        Load, generate (if not existing) and show the texture of the ith band.

        Parameters
        ----------
        i : int
            Band/date number to be loaded and shown.

        Returns
        -------
        None.

        """
        self.i = i

        # band data
        try:  # looking up cache
            (self.tex_id,
             self.tex_width, self.tex_height,
             self.tex_vi, self.tex_v5,
             self.tex_v95, self.tex_va,
             ) = self.textures[i]

        except KeyError:
            band, nd, dtype = self.loader.load_band(i)
            assert dtype == 'float32'

            # band data
            if nd is None:
                bg = np.zeros_like(band)
            else:
                bg = (band == nd)

            v_i, v_5, v_95, v_a = np.percentile(band[~bg], [0, 5, 95, 100])
            v = (band-v_i)/(v_a-v_i)

            h, w = band.shape
            z = np.ones((h, w, 2), dtype='float32')
            z[:, :, 0] = v
            z[:, :, 1][bg] = 0.

            # band texture
            glEnable(GL_TEXTURE_2D)
            texture_id = glGenTextures(1)
            glActiveTexture(GL_TEXTURE0+DATA_UNIT)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glTexParameter(GL_TEXTURE_2D,
                           GL_TEXTURE_MAG_FILTER,
                           GL_NEAREST)
            glTexParameter(GL_TEXTURE_2D,
                           GL_TEXTURE_MIN_FILTER,
                           GL_LINEAR_MIPMAP_LINEAR)

            glTexImage2D(
                GL_TEXTURE_2D,
                0, GL_LUMINANCE_ALPHA,
                w, h, 0,
                GL_LUMINANCE_ALPHA,
                GL_FLOAT,
                z
                )
            glGenerateMipmap(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)

            # store band texture param
            self.textures[i] = (
                self.tex_id,
                self.tex_width, self.tex_height,
                self.tex_vi, self.tex_v5,
                self.tex_v95, self.tex_va,
                ) = (
                    texture_id,
                    w, h,
                    v_i, v_5,
                    v_95, v_a,
                    )

            # make and store histogram:
            band[bg] = np.nan
            iband = ImageItem(band)
            self.hist = iband.getHistogram()
            self.histograms[i] = self.hist

        if len(self.textures) == 1:  # first band loading
            self.cx = self.tex_width // 2
            self.cy = self.tex_height // 2
            self.z = 1.
            self.bounds_changed.emit()
            # set colorbar histogram levels to current 5/95th percentiles
            self.init_histo_vals.emit((self.tex_v5, self.tex_v95,))
            self.update_selection()

        self.texture_changed.emit()

    def show_points(self, pointers, highlight=None):
        """ update selected points values for selection texture,
        launch map update to show currently selected points

         Parameters
        ----------
        pointers : tuple, array
            tuple or nMaxPoints+1-by-2 array with all currently selected
            points texture coordinates + oldest previously selected point,
            to be unselected on Map
        highlight : None or int
            None or id of the curve selected by user on plots to be
            highlighted, corresponding point on Map is highlighted accordingly

         """
        # reset formerly highlighted point:
        self.selection[self.selection == 2] = 0

        if isinstance(pointers, tuple):
            self.selection[int(pointers[1]), pointers[0]] = 1
        elif len(pointers) > self.nMaxPoints:
            self.selection[int(pointers[-1, 1]), int(pointers[-1, 0])] = 1
            self.selection[int(pointers[0, 1]), int(pointers[0, 0])] = 0
        else:
            coord = (pointers[np.max(np.nonzero(pointers)), 0],
                     pointers[np.max(np.nonzero(pointers)), 1])
            self.selection[int(coord[1]), int(coord[0])] = 1

        # highlight point if clicked on temporal plot:
        # highlight is curve name (number) on temporal plot
        if highlight is not None:
            # indexes of point on Map corresponding to highlighted curve:
            a, b = pointers[int(highlight), 1], pointers[int(highlight), 0]
            # indexes of pixels surrounding this point on the Map:
            neighbors = get_neighbors_idxs(self.selection,
                                           (a, b),
                                           2)
            mymask = np.zeros((self.selection.shape))
            mymask[neighbors] = 1.
            mymask[self.selection == 1] = 0.
            self.selection[mymask == 1.] = 2.

        self.update_selection()

    def show_profile(self, pointers):
        """
        first point selected by user (start): shows in red as in show_points
        second point (end): shows full line between first and second
        for that, must calculate all points forming straight line
        between start and end (using bresenham algorithm)

        Parameters
        ----------
        pointers : tuple
            radar coordinates (i, j) of selected point.

        Returns
        -------
        None.

        """

        # reset formerly highlighted point:
        self.selection[self.selection == 2] = 0

        # starting from second point, get points between new and last selected
        # to draw line:
        if self.selection.sum() > 1.:
            line_points = line(*self.profile_points[-1], *pointers)
            self.profile_points += line_points[1:]

            # subsample if more than nMaxPoints:
            if len(self.profile_points) > self.nMaxPoints:
                self.all_pointers_ij = self.subsample_profile(
                    self.profile_points)


            # add points to selection for display on map:
            for point in self.profile_points:
                self.selection[int(point[1]), int(point[0])] = 1.
            for point in self.all_pointers_ij:
                self.selection[int(point[1]), int(point[0])] = 5.

        else:  # first point
            self.profile_points.append(pointers)
            # add current point to selection:
            self.selection[int(pointers[1]), pointers[0]] = 1.

        self.update_selection()

    def subsample_profile(self, points):
        """


        Parameters
        ----------
        points : array
            n-by-2 array of x,y coordinates of all points in the profile line.

        Returns
        -------
        array
            nMaxPoints-by-2 array of x,y coordinates of (sub)equally distant
            subsamples on the profile line.

        """

        x = np.array(points)[:,0]
        y = np.array(points)[:,1]

        distance = np.cumsum(np.sqrt( np.ediff1d(x, to_begin=0)**2 + np.ediff1d(y, to_begin=0)**2 ))
        distance = distance/distance[-1]

        fx, fy = interp1d(distance, x), interp1d(distance, y)

        alpha = np.linspace(0, 1, self.nMaxPoints)
        x_regular = np.round(fx(alpha)).astype(int)
        y_regular = np.round(fy(alpha)).astype(int)

        return np.array([x_regular, y_regular]).T

    def show_ref(self):
        """
        adds points (1px or rectangle) selected as ref to selection
         """
        # # reset formerly highlighted point:
        # self.selection[self.selection == 2] = 0

        for p in range(len(self.ref_pointers)):
            self.selection[int(self.ref_pointers[p][1]),
                           int(self.ref_pointers[p][0])] = -1.

        self.update_selection()

    def update_selection(self):
        """
        update selection layer (to be called when map size is known).
        """
        glEnable(GL_TEXTURE_2D)
        glActiveTexture(GL_TEXTURE0+SEL_UNIT)
        if self.sel_id == 0:
            self.sel_id = glGenTextures(1)
            self.selection = np.zeros(
                (self.tex_height, self.tex_width, 2),
                dtype='float32')
            glTexParameter(GL_TEXTURE_2D,
                           GL_TEXTURE_MAG_FILTER,
                           GL_NEAREST)
            glTexParameter(GL_TEXTURE_2D,
                           GL_TEXTURE_MIN_FILTER,
                           GL_LINEAR_MIPMAP_LINEAR)
        glBindTexture(GL_TEXTURE_2D, self.sel_id)
        glTexImage2D(
            GL_TEXTURE_2D,
            0, GL_LUMINANCE_ALPHA,
            self.tex_width, self.tex_height, 0,
            GL_LUMINANCE_ALPHA,
            GL_FLOAT,
            self.selection
            )
        glGenerateMipmap(GL_TEXTURE_2D)
        glActiveTexture(GL_TEXTURE0+DATA_UNIT)
        glBindTexture(GL_TEXTURE_2D, self.tex_id)
        glDisable(GL_TEXTURE_2D)

        self.texture_changed.emit()

    def resized(self, width, height):
        """
        Called when Map is resized, update width/height values and emit
        bounds_changed signal.

        Parameters
        ----------
        width : int
            New map width, in pixels.
        height : int
            New map height, in pixels.

        """
        self.map_width = width
        self.map_height = height
        self.bounds_changed.emit()

    # pan/zoom
    def zoom(self, ds, x=None, y=None):
        """
        Called by MouseMoveEvent and wheelEvent on Map. Update Map variables
        for display at new zoom level.

        Parameters
        ----------
        ds : float?
            zoom change (mouse wheel angle in degrees or
                         right-click+drag distance).
        x : int, optional
            x-axis position of the zoom change focal point.
            The default is None.
        y : int, optional
            y-axis position of the zoom change focal point.
            The default is None.

        Returns
        -------
        None.

        """

        dz = np.exp(ds*.01)
        self.z *= dz

        if x is not None:
            w, h = self.map_width, self.map_height
            self.cx += (x-w//2)/self.z * (dz-1.)
            self.cy += (y-h//2)/self.z * (dz-1.)
        self.bounds_changed.emit()

    def pan(self, dx, dy):
        """
        Called by MouseMoveEvent on Map. Update Map variables
        for display at new position.

        Parameters
        ----------
        dx : int
            change in Map view position along x-axis.
        dy : int
            change in Map view position along y-axis.

        Returns
        -------
        None.

        """
        self.cx -= dx/self.z
        self.cy -= dy/self.z
        self.bounds_changed.emit()

    def get_texture_coordinate(self, e):
        """
        Transform screen coord to texture coord : invert calculation of Map's
        paintGL().

        Parameters
        ----------
        e : QMouseEvent
            event which screen coordinates are to be transformed to
            texture coord

        Returns
        -------
        tuple
            texture coordinates
        """
        # screen coordinates:
        x, y = e.x(), self.map_height - e.y()  # y-axis inverted

        i = (x - self.map_width // 2) / self.z + self.cx
        j = (y - self.map_height // 2) / self.z + self.cy

        return (int(i), int(j))

    def set_map_interaction(self, val):
        self.map_istate = val
        assert self.map_istate in [0, 1, 2, 3, 5], \
            'map interaction: wrong value'

    @pyqtSlot(bool)
    def set_ready_for_POINTS(self, checked):
        self.ready_for_POINTS = checked

    @pyqtSlot(bool)
    def set_ready_for_PROFILE(self, checked):
        self.ready_for_PROFILE = checked

    @pyqtSlot(bool)
    def set_ready_for_REF(self, checked):
        self.ready_for_REF = checked
