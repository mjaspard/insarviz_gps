#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# imports ###################################################################

from .AbstractMapView import *

from PyQt5.QtCore import QSize, pyqtSlot, pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPainter, QBrush

from ..Interaction import IDLE, DRAG, ZOOM, POINTS, LIVE, PROFILE, REF

from insarviz.utils import get_rectangle

from PyQt5.Qt import QRubberBand
from PyQt5.Qt import QRect

# map #######################################################################


class MapView(AbstractMapView):
    sig_map2plotw = pyqtSignal()
    cursor_changed = pyqtSignal(tuple)

    __name__ = 'MAP'

    def __init__(self, map_model, plot_model):
        """
        Generate Map, a QOpenGLWidget display of the displacement data. Zoom
        level can be interactively set through mouse wheel or right-click+drag.
        View position on the Map can be interactively set through left-click+
        drag. View is synchronized to Minimap.

        Parameters
        ----------
        map_model : QObject
            Model managing the data for Map and Minimap.
        plot_model : QObject
            Model managing the data for the plots.

        Returns
        -------
        None.

        """


        print("Mapview -- object creation")
        super().__init__(map_model)
        self.plot_model = plot_model

        self.resized.connect(self.update_size)
        self.update_size()

        self.all_pointer_xy = None
        self.lastPoint = None
        print("Mapview -- object creation -- finished")
        

    @pyqtSlot()
    def update_size(self):
        """
        Called when Map view size has changed, update Map Model's variables
        linked to Map size.

        Returns
        -------
        None.

        """
        print("Mapview -- update_size")
        self.model.resized(self.width(), self.height())

    # opengl
    def init_program(self):
        """
        Create program, shader, texture for OpenGL display

        Returns
        -------
        None.

        """
        print("Mapview -- init_program")
        program = create_program(
            create_shader(GL_FRAGMENT_SHADER, PALETTE_SHADER),
            create_shader(GL_FRAGMENT_SHADER, MAP_SHADER),
            )

        # selection texture
        glActiveTexture(GL_TEXTURE0+SEL_UNIT)
        set_uniform(program, 'selection', SEL_UNIT)
        return program

    def sizeHint(self):
        print("Mapview -- sizeHint")
        return QSize(300, 300)

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
        print("Mapview -- resizeGL")
        glViewport(0, 0, width, height)

        tw, th = self.model.tex_width, self.model.tex_height
        glMatrixMode(GL_TEXTURE)
        glLoadIdentity()
        glScale(1./tw, 1./th, 1.)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, width, 0, height, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        self.repaint()







    def paintGL(self):
        """
        Generate and display OpenGL texture for Map.

        Returns
        -------
        None.

        """
        print("Mapview -- paintGL")

        # band using OpenGL texturing
        glClear(GL_COLOR_BUFFER_BIT)
        glEnable(GL_TEXTURE_2D)

        glUseProgram(self.program)
        # selection texture
        glActiveTexture(GL_TEXTURE0+SEL_UNIT)
        glBindTexture(GL_TEXTURE_2D, self.model.sel_id)

        # band texture
        glActiveTexture(GL_TEXTURE0+DATA_UNIT)
        glBindTexture(GL_TEXTURE_2D, self.model.tex_id)

        cx, cy = self.model.cx, self.model.cy
        z = self.model.z
        w, h = self.width(), self.height()

        glMatrixMode(GL_TEXTURE)
        glPushMatrix()
        glTranslate(cx, cy, 0.)
        glScale(1./z, 1./z, 1.)
        glTranslate(-w//2, -h//2, 0.)

        glBegin(GL_TRIANGLE_STRIP)
        for x in [0, w]:
            for y in [0, h]:
                glTexCoord(x, y)
                glVertex(x, y)
        glEnd()
        glPopMatrix()
        glUseProgram(0)
        glDisable(GL_TEXTURE_2D)



        glBindTexture(GL_TEXTURE_2D, 0)

        # # overlay using QPainter
        # painter = QPainter(self)
        # for dx, dy, color in [
        #     (1, 1, QColor('black')),
        #     (0, 0, QColor('white')),
        # ]:
        #     painter.setPen(color)
        #     painter.drawText(10+dx, 20+dy, 'Map')



        # print(self.plot_model_gps.station_gps_data)

        # Draw each station on the map if needed
        try:
            if self.plot_model_gps.station_gps_data:
                print("Mapview -- draw_gps_station (all stations)")
                for station in self.plot_model_gps.station_gps_data.keys():
                    # print("station = ", station)
                    # print(self.plot_model_gps.station_gps_data[station]['x'])
                    # print(self.plot_model_gps.station_gps_data[station]['y'])

                    i = self.plot_model_gps.station_gps_data[station]['x']
                    j = self.plot_model_gps.station_gps_data[station]['y']

                    self.draw_gps_station(i, j, station)
        except:
            pass

    def draw_gps_station(self, i, j, station_name):



        color1 = 'yellow'
        color2 = 'black'
        color3 = 'green'

        if station_name ==  self.plot_model_gps.current_station:
            color1 = 'red'
            color3 = 'red'

        cx, cy = self.model.cx, self.model.cy
        z = self.model.z
        w, h = self.width(), self.height()
        # Display GPS stations
        # print("--------------------------------")
        # print("w = ", w)
        # print("h = ", h)

        # print("cx = ", cx)
        # print("cy = ", cy)
        # print("z = ", z)

        # Calculate pixel to draw gps station using raster coordinate(cx, cy), screen pixels size (w, h) and zoom (z = ration pixel_screen/pixel_raster)
        x_screen = (w/2) - ((cx - i) * z)
        y_screen = (h/2) + ((cy - j) * z)
        # print("x_screen = ", x_screen)
        # print("y_screen = ", y_screen)

        painter = QPainter(self)
        painter.fillRect(x_screen-3, y_screen-3, 6, 6, QColor(color1))
        for dx, dy, color in [
            (1, 1, QColor(color2)),
            (0, 0, QColor(color3)),]:
            painter.setPen(color)
            painter.drawText(x_screen+dx, y_screen+dy, station_name)

    def mousePressEvent(self, e):
        """
        Overload method
        Set interaction mode according to user interaction type:
        In Interactive mode:
            - Left-click: pan
            - Right-click: zoom
        In Points and Profile modes:
            - Left-click: select points whose data will be shown in plots
        In Reference mode:
            - Left-click: first click selecs one px to be used as ref,
            subsequent clicks extend ref zone to rectangle with last point and
            new points as opposing corners.
        Update Map Model and Plot Model values accordingly

        Parameters
        ----------
        e : QPoint
            Location of the pointer upon clicking.

        Returns
        -------
        None.

        """
        print("Mapview -- mousePressEvent")

        if (self.model.ready_for_POINTS or self.model.ready_for_PROFILE):
            QApplication.setOverrideCursor(Qt.CrossCursor)
        else:
            while QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()
                # QApplication.restoreOverrideCursor()



        # check if data loaded
        if self.model.i > -1:
            if self.model.map_istate == IDLE:
                # init position for drag/zoom
                self.p = self.p0 = e.x(), self.height() - e.y()

                # check if pointer on texture:
                i, j = self.model.get_texture_coordinate(e)
                if (0 <= i < self.model.tex_width) and (
                        0 <= j < self.model.tex_height):

                    if e.button() == Qt.LeftButton:
                        self.plot_model.pointer_ij = (i, j)
                        self.plot_model.update_pointer_values()

                        if self.model.ready_for_POINTS:
                            self.model.map_istate = POINTS

                            self.plot_model.plot_istate = POINTS
                            self.plot_model.update_values()
                            # draw points trace on Map:
                            self.model.show_points((i, j))
                            self.lastPoint = e.pos()

                        elif self.model.ready_for_PROFILE:
                            # draw profile trace on Map:
                            self.model.map_istate = \
                                self.plot_model.plot_istate = PROFILE
                            self.model.show_profile((i, j))
                            if self.model.all_pointers_ij is not None:
                                self.plot_model.all_pointer_ij = \
                                    self.model.all_pointers_ij
                            # draw plots:
                            self.plot_model.update_values(
                                profile_points=self.model.profile_points)

                        elif self.model.ready_for_REF:
                            self.model.map_istate = \
                                self.plot_model.plot_istate = REF
                            # second point of ref zone clicked:
                            if self.model.ref_pointers is not None:
                                # second click same as first, ref is 1px:
                                if (i, j) in self.model.ref_pointers:
                                    pass
                                # second different from first, ref is rectangle
                                else:
                                    self.model.ref_pointers = \
                                        get_rectangle(
                                            self.model.ref_pointers[-1],
                                            (i, j))
                                self.plot_model.ref_pointers = \
                                    self.model.ref_pointers
                            # first point:
                            else:
                                self.model.ref_pointers = \
                                    self.plot_model.ref_pointers = [(i, j)]
                            # show ref on map:
                            self.model.show_ref()
                            # update plots:
                            self.plot_model.update_ref_values(
                                self.plot_model.ref_pointers)

                        else:
                            # interactive navigation
                            self.model.map_istate = DRAG

                        self.sig_map2plotw.emit()

                    elif e.button() == Qt.RightButton:
                        self.model.map_istate = ZOOM

        print("Mapview -- mousePressEvent -- finished")

    def mouseMoveEvent(self, e):
        """
        Overload method
        Set interaction mode according to user interaction type and update
        Map view and model accordingly:
        In Interactive mode:
            - hovering: display tooltip: coordinates + data value(displacement)
            - Left-click+drag (pan): get new position and update Map view
            - Right-click+drag (zoom): get new zoom level and update Map view
        In Points mode:
            - Left-click (+ optional drag): highlight selected points on Map,
            send coordinates to MapModel, send signal to update plots
        In Profile mode:
            - Left-click: first click selects starting point of profile,
            subsequent clicks select end (or turning point) of profile, send
            coordinates to MapModel, send signal to update plots accordingly

        Parameters
        ----------
        e : QPoint
            Location of the pointer upon dragging.

        Returns
        -------
        None.

        """
        print("Mapview -- mouseMoveEvent")
        # change cursor to cross if Points or Profile tools selected:
        if (self.model.ready_for_POINTS or self.model.ready_for_PROFILE):
            QApplication.setOverrideCursor(Qt.CrossCursor)
        else:
            # restore default (arrow), "while" statement needed because Qt
            # maintains an internal stack of override cursors, and
            # restoreOverrideCursor only undoes the last one
            while QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()

        # check if data loaded
        if self.model.i > -1:
            i, j = self.model.get_texture_coordinate(e)
            # check if pointer on texture:
            if ((0 <= i < self.model.tex_width) and (
                    0 <= j < self.model.tex_height)):
                self.plot_model.pointer_ij = (i, j)
                self.plot_model.update_pointer_values()


                if self.model.map_istate == POINTS: # (self.model.ready_for_POINTS and e.button() == Qt.LeftButton):



                    # self.map_istate = POINTS
                    # self.plot_model.plot_istate = POINTS
                    self.plot_model.update_values()
                    # draw profile trace on Map:
                    self.model.show_points(self.plot_model.all_pointer_ij)
                    if len(self.plot_model.all_pointer_ij) > (
                            self.plot_model.nMaxPoints):
                        self.plot_model.all_pointer_ij = \
                                self.plot_model.all_pointer_ij[1:]
                    self.lastPoint = e.pos()


           


                elif self.model.map_istate == PROFILE:
                    # self.model.show_profile((i,j))
                    # TODO
                    # interactively update profile as cursor hovers before clicking end point
                    pass



                elif not self.model.ready_for_REF:
                    #interactive
                    self.plot_model.update_values()

                # plot selected data and refresh Map to show selection
                self.sig_map2plotw.emit()
                self.update()

                if self.model.map_istate == IDLE:
                    # info tooltip when hovering
                    p = self.mapToGlobal(e.pos())

                    QToolTip.showText(p, (
                        f"x:{i}"
                        f"\ny:{j}"
                        f"\ndisp:{self.plot_model.thispoint_thisdate_disp:.3f}"))
                    self.cursor_changed.emit((i, j))
                else:
                    # zoom or pan
                    x0, y0 = self.p0
                    x1, y1 = e.x(), self.height() - e.y()
                    dx, dy = x1-x0, y1-y0
                    if self.model.map_istate == DRAG:
                        self.model.pan(dx, dy)
                    elif self.model.map_istate == ZOOM:
                        self.model.zoom(dx-dy, *self.p)
                    self.p0 = x1, y1

        print("Mapview -- mouseMoveEvent -- finished")

    def mouseReleaseEvent(self, e):
        """
        Overload method
        Set interaction mode according to user interaction type and update
        Map view and model accordingly:
            interaction mode set back to default (idle), keep plots if was
            profiling.

        Parameters
        ----------
        e : QPoint
            Location of the pointer upon click release.

        Returns
        -------
        None.

        """
        # if self.interaction == DRAG:
        #     if e.button() == Qt.LeftButton:
        #         self.interaction = IDLE
        # elif self.interaction == ZOOM:
        #     if e.button() == Qt.RightButton:
        #         self.interaction = IDLE
        # elif self.interaction == POINTS:
        #     if (e.button() == Qt.LeftButton) and (
        #             (QApplication.keyboardModifiers() ==
        #               Qt.ControlModifier)):
        #         self.interaction = IDLE
        #         self.plot_model.plot_interaction = 0
        print("Mapview -- mouseReleaseEvent")


        if self.model.ready_for_POINTS:
            self.plot_model.plot_istate = IDLE
            self.model.map_istate = IDLE
        elif self.model.ready_for_PROFILE:
            self.plot_model.plot_istate = LIVE
            self.model.map_istate = IDLE
        else:
            self.plot_model.plot_istate = LIVE
            self.model.map_istate = IDLE


    # def show_gps_station(self, loader_gps):

    #     print("MapModel - show_gps_station")
    #     station_gps = loader_gps.gps_data.keys()
    #     station_gps_number = len(station_gps)
    #     station_gps_icon = numpy.zeros(station_gps_number, dtype = [ ("position", np.float32, 2),
    #                             ("color",    np.float32, 4)] )


              
  