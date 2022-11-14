#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# imports ###################################################################

import numpy as np

if True and False:
    import OpenGL
    OpenGL.ERROR_CHECKING = False
    OpenGL.ERROR_LOGGING = False
    OpenGL.ERROR_ON_COPY = True
    OpenGL.STORE_POINTERS = False

from OpenGL.GL import (
    GL_RGBA, GL_UNSIGNED_BYTE, GL_COLOR_BUFFER_BIT,
    GL_PROJECTION, GL_MODELVIEW, GL_TEXTURE,
    GL_TEXTURE0, GL_TEXTURE_1D, GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER, GL_TEXTURE_MIN_FILTER, GL_LINEAR,
    GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE, GL_REPEAT,
    GL_FRAGMENT_SHADER, GL_PIXEL_UNPACK_BUFFER, GL_STREAM_DRAW,
    GL_TRIANGLE_STRIP, GL_LINE_LOOP,
    glClear, glClearColor,
    glViewport, glMatrixMode, glLoadIdentity, glOrtho,
    glTranslate, glScale, glPushMatrix, glPopMatrix,
    glEnable, glDisable,
    glBegin, glEnd, glVertex,
    glUseProgram, glTexCoord,
    glActiveTexture, glBindTexture,
    glGenTextures, glTexParameter,
    glGenBuffers, glBindBuffer, glBufferData,
    glTexImage1D, glDeleteBuffers,
    )

from PyQt5.QtCore import (
    Qt, pyqtSignal, pyqtSlot,
    )

from PyQt5.QtGui import (
    QPainter, QColor, QPen,
    )

from PyQt5.QtWidgets import (
    QApplication, QOpenGLWidget, QWidget, QToolTip,
    )

from insarviz.map.gl_utils import *
from insarviz.map.Shaders import *

from insarviz.Interaction import IDLE, DRAG, ZOOM, POINTS, LIVE, PROFILE

# palette map ###############################################################


class AbstractMapView(QOpenGLWidget):
    """
    Abstract class for a map view, a QOpenGLWidget display of the
    displacement data, color coded using a palette
    """
    vs_changed = pyqtSignal()
    v_i, v_a = 0., 0.  # overall min and max

    def __init__(self, map_model):
        """
        Generate AbstractView.

        Parameters
        ----------
        model : QObject
            Model managing data for Map and Minimap views.

        Returns
        -------
        None.

        """
        super().__init__()
        self.model = map_model
        self.model.bounds_changed.connect(self.update)
        self.model.texture_changed.connect(self.update_texture)
        self.interaction = IDLE

    # opengl

    def init_program(self):
        """intialize and returns the glsl program for this view."""
        raise NotImplementedError

    def initializeGL(self):
        glClearColor(.5, .5, .5, 1.)
        self.program = self.init_program()
        glActiveTexture(GL_TEXTURE0+DATA_UNIT)
        set_uniform(self.program, 'values', DATA_UNIT)
        glActiveTexture(GL_TEXTURE0+PALETTE_UNIT)
        set_uniform(self.program, b'palette', PALETTE_UNIT)
        set_uniform(self.program, 'v_0', 0.)
        set_uniform(self.program, 'v_1', 1.)
        self.set_colormap()

    def update_vs(self):
        """update min and max to keep program in sync with model"""
        old_state = (self.v_i, self.v_a)
        v_i, v_a = self.model.tex_vi, self.model.tex_va
        set_uniform(self.program, 'v_i', v_i)
        set_uniform(self.program, 'v_a', v_a)
        self.v_i = min(self.v_i, v_i)
        self.v_a = max(self.v_a, v_a)
        if old_state != (self.v_i, self.v_a):
            self.vs_changed.emit()

    def set_colormap(self, colormap=b'\x00\x00\x00\xff\xff\xff\xff\xff'):
        self.makeCurrent()
        glActiveTexture(GL_TEXTURE0+PALETTE_UNIT)
        glBindTexture(GL_TEXTURE_1D, glGenTextures(1))
        glTexParameter(GL_TEXTURE_1D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameter(GL_TEXTURE_1D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameter(GL_TEXTURE_1D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
#       glTexParameter(GL_TEXTURE_1D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        pixel_buffer = glGenBuffers(1)
        glBindBuffer(GL_PIXEL_UNPACK_BUFFER, pixel_buffer)
        glBufferData(GL_PIXEL_UNPACK_BUFFER,
            len(colormap),
            colormap,
            GL_STREAM_DRAW)
        glTexImage1D(GL_TEXTURE_1D, 0, GL_RGBA,
            len(colormap)//4,
            0, GL_RGBA, GL_UNSIGNED_BYTE,
            None)
        glBindBuffer(GL_PIXEL_UNPACK_BUFFER, 0)
        glDeleteBuffers(1, [pixel_buffer])
        self.doneCurrent()
        self.repaint()

    @pyqtSlot(int)
    def update_black(self, v):
        set_uniform(self.program, 'v_0', float(v))
        self.update()

    @pyqtSlot(int)
    def update_white(self, v):
        set_uniform(self.program, 'v_1', float(v))
        self.update()

    @pyqtSlot()
    def update_texture(self):
        """
        Called when loading a new band/date from dataset file, update the
        texture

        Returns
        -------
        None.
        """
        self.makeCurrent()
        self.resizeGL(self.width(), self.height())
        self.update_vs()
        self.doneCurrent()
        # self.update()
        self.repaint()

    # interaction

    def wheelEvent(self, e):
        """
        Overload method
        Update zoom value in Map model according to wheel angle change for
        zoom level update on Map

        Parameters
        ----------
        e : QPoint
            Location of the pointer upon wheel event.

        Returns
        -------
        None.

        """

        x, y = e.x(), self.height()-e.y()
        ds = e.angleDelta().y()/8  # degrees
        self.model.zoom(ds, x, y)
