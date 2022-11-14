#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# imports ###################################################################

from .AbstractMapView import *

from PyQt5.QtCore import QSize, QPoint
from PyQt5.QtGui import (
    QPolygon, QPainter, QPen,
    QColor
    )
import math
# mini map ##################################################################


class MinimapView(AbstractMapView):
    """
    Minimap
    This is a general view of the data, in greyscale. A white rectangle
    shows the area cureently displayed in Map (zoom/pan synchronized).
    """

    # closing behaviour

    sigClosing = pyqtSignal(bool)
    __name__ = 'MINIMAP'

    def closeEvent(self, a0):
        """
        Overload method
        send signal that Minimap window was closed, uncheck Minimap button
        """
        super().closeEvent(a0)
        self.sigClosing.emit(False)

    # opengl

    def init_program(self):
        """
        Create program, shader, texture for OpenGL display

        Returns
        -------
        None.

        """
        program = create_program(
            create_shader(GL_FRAGMENT_SHADER, PALETTE_SHADER),
            create_shader(GL_FRAGMENT_SHADER, MINIMAP_SHADER),
        )
        return program

    def sizeHint(self):
        return QSize(100, 100)

    def resizeGL(self, width, height):
        """
        Resize OpenGL view according to new settings

        Parameters
        ----------
        width : int
            new view width.
        height : int
            new view height.

        Returns
        -------
        None.

        """
        glViewport(0, 0, width, height)
        wr = width/height
        tw, th = self.model.tex_width, self.model.tex_height
        tr = tw/th

        if tr > wr:
            w, h = 1., 1./wr
        else:
            w, h = wr, 1.
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, w, 0, h, -1, 1)
        glTranslate(w/2., h/2., 0.)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        if tr > wr:
            glScale(1., 1./tr, 1.)
        else:
            glScale(tr, 1., 1.)
        glTranslate(-.5, -.5, 0.)

    def paintGL(self):
        """
        Generate and display OpenGL texture for Map.

        Returns
        -------
        None.

        """
        print("Mini Mapview -- paintGL")

        # band using OpenGL texturing
        glClear(GL_COLOR_BUFFER_BIT)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_TEXTURE_1D)

        glUseProgram(self.program)
        glActiveTexture(GL_TEXTURE0+DATA_UNIT)
        glBindTexture(GL_TEXTURE_2D, self.model.tex_id)

        glBegin(GL_TRIANGLE_STRIP)
        for x in [0, 1]:
            for y in [0, 1]:
                glTexCoord(x, y)
                glVertex(x, y)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glUseProgram(0)

        x, y, z = self.model.cx, self.model.cy, self.model.z
        tw, th = self.model.tex_width, self.model.tex_height
        ww, wh = self.model.map_width, self.model.map_height
        x1, x2 = x-ww/2./z, x+ww/2./z
        y1, y2 = y-wh/2./z, y+wh/2./z

        glPushMatrix()
        glScale(1./tw, 1./th, 1.)
        glBegin(GL_LINE_LOOP)
        glVertex(x1, y1)
        glVertex(x1, y2)
        glVertex(x2, y2)
        glVertex(x2, y1)
        glEnd()
        glPopMatrix()





        # glBindTexture(GL_TEXTURE_2D, 0)

        # overlay orbit+LOS symbol using QPainter
        # if info available from metadata file
        try:
            assert(self.model.loader.metadata['Antenna_side'] in (
                'LEFT', 'RIGHT'))
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)  # does not work...

            # symbol is made of two perpendicular arrows, orbit arrow and LOS
            # arrow (which starts at orbit arrow's mid-point)
            # drawn twice, in black and in white to improve readability
            for dx, dy, color in [
                    (1, 1, QColor('black')),
                    (0, 0, QColor('white'))]:

                painter.setPen(QPen(color, 2))
                painter.setBrush(color)
                painter.pen().setWidth(10)

                center_pt = QPoint(self.width()-25+dx, self.height()-25+dy)

                # drawing points
                (orb_start,
                 orb_end,
                 los_end) = self.make_orbit_LOS_symbol(center_pt)
                los_start = center_pt

                # orbit arrow:
                painter.drawLine(orb_start, orb_end)
                rotation = math.degrees(
                    math.atan2(orb_start.y()-orb_end.y(),
                               orb_end.x()-orb_start.x())) + 90
                arrowhead_poly = [
                    QPoint(orb_end.x()+5*math.sin(math.radians(rotation)),
                           orb_end.y()+5*math.cos(math.radians(rotation))),
                    QPoint(orb_end.x()+5*math.sin(math.radians(rotation-120)),
                           orb_end.y()+5*math.cos(math.radians(rotation-120))),
                    QPoint(orb_end.x()+5*math.sin(math.radians(rotation+120)),
                           orb_end.y()+5*math.cos(math.radians(rotation+120)))]
                painter.drawPolygon(QPolygon(arrowhead_poly))

                # LOS arrow:
                painter.drawLine(los_start, los_end)
                rotation = math.degrees(
                    math.atan2(los_start.y()-los_end.y(),
                               los_end.x()-los_start.x())) + 90
                arrowhead_poly = [
                    QPoint(los_end.x()+4*math.sin(math.radians(rotation)),
                           los_end.y()+4*math.cos(math.radians(rotation))),
                    QPoint(los_end.x()+4*math.sin(math.radians(rotation-120)),
                           los_end.y()+4*math.cos(math.radians(rotation-120))),
                    QPoint(los_end.x()+4*math.sin(math.radians(rotation+120)),
                           los_end.y()+4*math.cos(math.radians(rotation+120)))]
                painter.drawPolygon(QPolygon(arrowhead_poly))

        except (AssertionError, AttributeError, KeyError):
            # no metadata or wrong format
            pass

    # interaction
    def draw_gps_station(self):

        print("MinimapView -- draw_gps_station")
        # Display GPS stations
        x = 20
        y = 20
        painter = QPainter(self)
        for dx, dy, color in [
            (1, 1, QColor('white')),
            (0, 0, QColor('black')),]:
            painter.fillRect(x, y, 5, 5, QColor('green'))
            painter.drawText(x+dx, y+dy, 'Station Name')


    def mousePressEvent(self, e):
        """
        Overload method
        Set interaction mode according to user interaction type:
            - Left-click: pan
            - Right-click: zoom
        Update Map Model values accordingly

        Parameters
        ----------
        e : QPoint
            Location of the pointer upon clicking.

        Returns
        -------
        None.

        """
        # check if data loaded
        if self.model.i > -1:
            if self.interaction == IDLE:
                self.p0 = e.x(), self.height()-e.y()
                if e.button() == Qt.LeftButton:
                    self.interaction = DRAG
                elif e.button() == Qt.RightButton:
                    self.interaction = ZOOM

    def mouseMoveEvent(self, e):
        """
        Overload method
        Set interaction mode according to user interaction type and update
        Minimap view and Map model accordingly:
            - Left-click+drag (pan): get new position and update Minimap view
            - Right-click+drag (zoom): get new zoom level and update Minimap
            view


        Parameters
        ----------
        e : QPoint
            Location of the pointer upon dragging.

        Returns
        -------
        None.

        """
        if self.interaction == IDLE:
            # unused?
            pass
        else:
            x0, y0 = self.p0
            x1, y1 = e.x(), self.height()-e.y()

            dx, dy = x1-x0, y1-y0

            if self.interaction == DRAG:
                ww, wh = self.width(), self.height()
                tw, th = self.model.tex_width, self.model.tex_height
                wr = ww/wh
                tr = tw/th
                if tr > wr:
                    dy *= tr/wr
                else:
                    dx *= wr/tr
                z = self.model.z

                dx *= tw/ww*z
                dy *= th/wh*z

                self.model.pan(-dx, -dy)
            elif self.interaction == ZOOM:
                self.model.zoom(dx-dy, *self.p0)
            self.p0 = x1, y1

    def mouseReleaseEvent(self, e):
        """
        Overload method
        Set interaction mode according to user interaction type and update
        Minimap view and Map model accordingly:
            interaction mode set back to default (idle)

        Parameters
        ----------
        e : QPoint
            Location of the pointer upon click release.


        Returns
        -------
        None.

        """

        if self.interaction == DRAG:
            if e.button() == Qt.LeftButton:
                self.interaction = IDLE
        elif self.interaction == ZOOM:
            if e.button() == Qt.RightButton:
                self.interaction = IDLE

    def make_orbit_LOS_symbol(self, center_pt):
        """
        determine the coordinates or the points for the symbol representing
        the satellite's orbit direction and LOS in the Minimap

        Symbol for ASCENDING RIGHT:

        Orbit direction
        ^
        |
        |
        |-> LOS
        |
        |

        Parameters
        ----------
        center_pt : QPoint
            center point for the symbol (near bottom-right corner of Minimap)

        Returns
        -------
        orb_start : QPoint
            starting point of the orbit arrow.
        orb_end : QPoint
            end point of the orbit arrow.
        los_end : QPoint
            end point of the LOS arrow.

        """

        # ASCENDING:
        if self.model.loader.metadata['Orbit_direction'] == 'ASCENDING':
            orb_start = QPoint(center_pt.x() + 4, center_pt.y() + 15)
            orb_end = QPoint(center_pt.x() - 4, center_pt.y() - 15)
            if self.model.loader.metadata['Antenna_side'] == 'RIGHT':
                los_end = QPoint(center_pt.x() + 3, center_pt.y() - 1)
            elif self.model.loader.metadata['Antenna_side'] == 'LEFT':
                los_end = QPoint(center_pt.x() - 3, center_pt.y() + 1)

        elif self.model.loader.metadata['Orbit_direction'] == 'DESCENDING':
            orb_start = QPoint(center_pt.x() + 4, center_pt.y() - 15)
            orb_end = QPoint(center_pt.x() - 4, center_pt.y() + 15)
            if self.model.loader.metadata['Antenna_side'] == 'RIGHT':
                los_end = QPoint(center_pt.x() - 3, center_pt.y() - 1)
            elif self.model.loader.metadata['Antenna_side'] == 'LEFT':
                los_end = QPoint(center_pt.x() + 3, center_pt.y() + 1)
        else:
            print('unrecognized orbit/LOS parameters')

        return (orb_start, orb_end, los_end)
