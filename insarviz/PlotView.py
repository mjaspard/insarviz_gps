#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pyqtgraph as pg
import numpy as np
import datetime

from PyQt5.QtCore import (
    pyqtSignal, pyqtSlot,
    )


from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout,
    QPushButton, QToolBar,
    QLabel, QCheckBox, QComboBox
    )

from insarviz.utils import (
    get_nearest
    )

from .Interaction import IDLE, DRAG, ZOOM, POINTS, LIVE, PROFILE, REF

from .custom_widgets import AnimatedToggle


# ITEMS ######################################################################

class TimeAxisItem(pg.DateAxisItem):
    """
    Based on pyqtgraph's DateAxisItem.
    Axis item that displays dates from unix timestamps, SI prefix
    for units is disabled and values are handled to be displayed in
    yyyy-mm-dd format.
    """

    def __init__(self, text, units):
        """
        Creates a new TimeAxisItem.

        Parameters
        ----------
        text : str
            text (without units) to display on the label for this axis
        units : str
            units for this axis
        """

        print("Plotview.py -- TimeAxisItem -- object creation")
        super().__init__()
        # to avoid unit scaling (unfit for dates) :
        self.enableAutoSIPrefix(False)
        self.setLabel(text=text, units=units)


class DateMarker(pg.InfiniteLine):
    """
    Based on pyqtgraph's InfiniteLine
    Vertical infinite line on plot, x-axis-position is synchronized with
    MainWindow's slider position
    overload some methods
    """

    sigposChanged = pyqtSignal(int)

    def __init__(self, pos, plot_model):
        """
        ...

        Parameters
        ----------
        pos : int, float (or QPointF)
            Position of the line, this can be a QPointF or a single value
            for vertical/horizontal lines.
        plot_model : QObject
            Model managing the data for the plots
        """
        print("Plotview.py -- DateMarker-- object creation")
        self.plot_model = plot_model

        super().__init__(pos=pos, angle=90, movable=True)

    def setPos(self, pos):
        """
        Overload function
        Position can only be set to one of the values of the dataset
        (on x-axis, ie a band# or date)

        Parameters
        ----------
        pos : int, float, QPoint
            position (approx.) where the line should be set

        Returns
        -------
        None.

        """
        print("Plotview.py -- DateMarker -- setPos")
        # this is needed when moving the marker, to make sure it can only
        # take values that correspond to dates/band numbers from the dataset:
        if not isinstance(pos, (int, float)) and (
                pos[0] not in self.plot_model.timestamps):
            pos, self.idx = get_nearest(self.plot_model.timestamps, pos[0])
        super().setPos(pos)

    def mouseDragEvent(self, ev):
        """
        Overload function
        emit signal that position changed, to update the position of the slider
        in MainWindow accordingly

        Parameters
        ----------
        ev : QEvent?


        Returns
        -------
        None.

        """
        print("Plotview.py -- DateMarker -- mouseDragEvent")
        super().mouseDragEvent(ev)
        self.sigposChanged.emit(self.idx)

    @pyqtSlot(int)
    def on_slider_changed(self, slidervalue):
        """
        Receive signal when MainWindow's slider position changed, update
        line position accordingly

        Parameters
        ----------
        slidervalue : int
            New position of slider tick.

        Returns
        -------
        None.

        """
        print("Plotview.py -- DateMarker -- on_slider_changed")
        current_date = self.plot_model.current_date
        self.setPos(pos=current_date)




# VIEWS ########################################################################################################################

class myPlotWindow(QWidget):
    """
    Window to display the plots
    """

    def __init__(self, plot_model, plottype):
        """
        New window to display the plots

        Parameters
        ----------
        plot_model : QObject
            model managing the data for the plots
        plottype : str
            type of plot, can be 'temporal' or 'spatial'

        Returns
        -------
        None
        """
        print("myPlotWindow -- object creation")
        super().__init__()
        self.plot_model = plot_model
        self.ptype = plottype
        self.initUI()
        print("myPlotWindow -- object creation -- finished")

    def initUI(self):
        """
        Initialize user interface

        """

        self.setWindowTitle((self.ptype + " profile").title())

        # init plot widget:
        self.plot_widget = myPlotWidget(plottype=self.ptype,
                                        plot_model=self.plot_model)

        # Toolbar:
        self.toolbar = QToolBar("Graph toolbar")
        self.zoom_button = QPushButton('Zoom')
        self.zoom_button.setCheckable(True)
        self.theme_switch = AnimatedToggle()
        self.theme_switch.toggled.connect(self.plot_widget.setStyle)

        self.toolbar.addWidget(self.zoom_button)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(QLabel('black'))
        self.toolbar.addWidget(self.theme_switch)
        self.toolbar.addWidget(QLabel('white'))
        self.toolbar.addSeparator()
        # if self. ptype == 'temporal':
        self.ref_tick = QCheckBox('Reference', self)
        self.ref_tick.setCheckable(False)
    # self.ref_tick.stateChanged.connect(
    #     lambda: self.plot_widget.connect_CurveClicked_Ref(
    #         self.ref_tick))
        self.ref_tick.stateChanged.connect(self.set_ref_status)
        self.toolbar.addWidget(self.ref_tick)

        # layout
        layout = QVBoxLayout()
        layout.setMenuBar(self.toolbar)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        # only for temporal plot:
        # check box to fix axes when hovering on Map:
        if self.ptype == 'temporal':
            self.check_axes = QCheckBox('Lock axes', self)
            self.check_axes.setToolTip("When checked, keep axes ranges while"
                                       " hovering on Map. Note that you can "
                                       " still zoom in/out on the plot.")
            self.check_axes.stateChanged.connect(
                lambda: self.ctrl_axes(self.check_axes))
            layout.addWidget(self.check_axes)
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

        # connect signals:
        self.zoom_button.toggled.connect(self.plot_widget.init_zoom)

    def ctrl_axes(self, box):
        print("myPlotWindow -- ctrl_axes")
        if box.isChecked():
            self.plot_widget.main_plot.autoBtn.mode = 'fix'
        else:
            self.plot_widget.main_plot.autoBtn.mode = 'auto'
        self.plot_widget.main_plot.autoBtnClicked()

    def on_button_clicked_clearplot(self):
        """
        called when clicking clear profile button in MainWindow
        remove and reset plots

        """
        print("myPlotWindow -- on_button_clicked_clearplot")
        if self.zoom_button.isChecked():
            self.plot_widget.removeItem(self.plot_widget.zoom_plot)
        self.zoom_button.setChecked(False)
        self.plot_widget.removeItem(self.plot_widget.main_plot)
        # keep track of style, init, re-set same style:+
        style = self.plot_widget.style
        self.plot_widget.initUI()
        self.plot_widget.setStyle(style)
        self.plot_model.plot_istate = 4
        if self.ptype == 'temporal':
            self.check_axes.setChecked(False)
            self.ref_tick.setChecked(False)
            # self.ref_tick.setVisible(False)
        self.plot_model.ref_curve_data = None
        self.plot_model.ref_curve_id = None
        self.plot_model.ref_pointers = None

    def set_ref_status(self):
        print("myPlotWindow -- set_ref_status")
        self.plot_model.ref_is_checked = self.ref_tick.isChecked()
        if (
                not self.plot_model.ref_is_checked and
                self.plot_model.plot_istate == 0):
            self.plot_model.ref_curve_id = None
            self.plot_widget.plotLoadedData()
        print("myPlotWindow -- set_ref_status -- finished")

# VIEWS ########################################################################################################################

class myPlotWidget(pg.GraphicsLayoutWidget):
    """
    Based on pyqtgraph's GraphicsLayoutWidget
    layout to display main and zoom plots
    """

    def __init__(self, plottype, plot_model):
        """
        ...

        Parameters
        ----------
        plottype : str
            type of plot, can be 'temporal' or 'spatial'
        plot_model :
            model managing the data for the plots

        """
        print("myPlotWidget -- object creation")
        super().__init__()
        self.plot_model = plot_model
        self.ptype = plottype

        self.initUI()
        print("myPlotWidget -- object creation -- finished")


    def initUI(self):
        """
        Initialize user interface: main plot and its items (curves), and
        current date marker

        """
        self.prev_points = None

        if self.ptype == 'temporal':
            self.main_plot = self.addPlot(
                title="<b>Temporal profile</b>\
                    <br>1 line/point on Map's profile")
            # x-axis:
            if isinstance(self.plot_model.timestamps, range):
                # dates not available: regular x-axis
                self.main_plot.setLabel('bottom',
                                        "Band/Date #")
            else:
                # dates available: x-axis is a TimeAxisItem
                self.main_plot.setAxisItems(
                    {'bottom': TimeAxisItem(text='Date',
                                            units='yyyy-mm-dd')})
            # y-axis:
            self.main_plot.showGrid(x=True, y=False, alpha=1.)
            # number of lines on plot:
            self.nPlots = self.plot_model.nMaxPoints
            # pen = [(idx, self.nPlots*1.3) for idx in range(self.nPlots)]
            # pen = [((idx)/(self.nPlots-0.1)) for idx in range(self.nPlots)]
            # pen = [(idx/self.nPlots*255) for idx in range(self.nPlots)]
            # pen = np.ones(self.nPlots)

            # vertical line as temporal marker synchronized with slider:
            self.date_marker = DateMarker(pos=self.plot_model.current_date,
                                          plot_model=self.plot_model)
            self.main_plot.addItem(self.date_marker)

            # interactive curve
            self.icurve = pg.PlotDataItem(pen=pg.mkPen((255, 0, 0), width=2),
                                          symbol='o',
                                          symbolSize=5,
                                          antialias=True)

            self.icurve.sigPointsClicked.connect(self.dataPointsClicked)
            self.main_plot.addItem(self.icurve)


        elif self.ptype == 'spatial':
            self.main_plot = self.addPlot(
                title="<b>Spatial profile</b><br>1 line/date<br>")
            self.main_plot.setLabel('bottom',
                                    "Distance along profile line",
                                    units='pixel')
            self.nPlots = self.plot_model.number_of_dates
            # pen = np.ones(self.nPlots)

        self.main_plot.setLabel('left',
                                "LOS Displacement",
                                units=self.plot_model.units)

        # plot curves init, all their data is None
        self.curves = []
        for idx in range(self.nPlots):
            self.curve = pg.PlotDataItem(pen='w', #pg.mkPen(
                                            #(255, 255, 255, pen[idx]),
                                            #width=2),
                                         symbol='o',
                                         symbolSize=5,
                                         antialias=True)
            self.curve.opts['name'] = idx
            self.curve.sigPointsClicked.connect(self.dataPointsClicked)
            # self.curve.sigClicked.connect(self.plotLoadedData_toRef)
            self.main_plot.addItem(self.curve)
            self.curves.append(self.curve)

        self.setStyle(0)

    @pyqtSlot(bool)
    def init_zoom(self, checked):
        """
        Initialize zoom plot: init selection ROI in main plot, creates new
        plot (zoom plot) with x-axis range synchronized with
        main plot's selection region, plot same data as main plot.
        Called when clicking 'Zoom' button in plot window.

        Parameters
        ----------
        checked : bool
            True if Zoom button is toggled

        """
        print("myPlotWidget -- init_zoom")
        current_style = self.style
        if checked:
            # selection region on main plot:
            # init on central 20% of data range:
            if self.ptype == 'temporal':
                xvals = self.plot_model.timestamps
            elif self.ptype == 'spatial':
                xvals = range(20)
            self.lr = pg.LinearRegionItem(
                np.percentile(
                    xvals,
                    [50 * (1 - 0.2), 50 * (1 + 0.2)]))
            self.main_plot.addItem(self.lr)

            # zoom plot init:
            self.zoom_plot = self.addPlot(title="Zoom on selected region")
            if self.ptype == 'temporal':
                if isinstance(self.plot_model.timestamps, range):
                    # dates not available: regular x-axis
                    self.zoom_plot.setLabel('bottom', "Band/Date #")
                else:
                    # dates available: x-axis is a TimeAxisItem
                    self.zoom_plot.setAxisItems(
                        {'bottom': TimeAxisItem(
                            text='Date', units='yyyy-mm-dd')})
                # pen = [(idx, self.nPlots*1.3) for idx in range(self.nPlots)]
            elif self.ptype == 'spatial':
                self.zoom_plot.setLabel('bottom',
                                        "Distance along profile line",
                                        units='pixel')
                # pen = np.ones(self.nPlots)

            self.icurve2 = pg.PlotDataItem(pen=pg.mkPen((255, 0, 0), width=2),
                                           symbol='o',
                                           symbolSize=5,
                                           antialias=True)
            self.icurve2.sigPointsClicked.connect(self.dataPointsClicked)
            self.zoom_plot.addItem(self.icurve2)

            self.curves2 = []
            for idx in range(self.nPlots):
                self.curve2 = pg.PlotDataItem(pen='w', #pen[idx],
                                              symbol='o',
                                              symbolSize=5,
                                              antialias=True)
                self.zoom_plot.addItem(self.curve2)
                self.curves2.append(self.curve2)

            if self.curves[0].dataBounds(1)[1] is not None:
                # data already plotted in main_plot, set same data in zoom plot
                self.plotLoadedData()

            self.lr.sigRegionChanged.connect(self.updateZoomPlot)
            self.zoom_plot.sigXRangeChanged.connect(self.updateZoomRegion)
            self.updateZoomPlot()
        else:
            self.main_plot.removeItem(self.lr)
            self.zoom_plot.hide()

        self.setStyle(current_style)
        print("myPlotWidget -- init_zoom -- finished")

    
    @pyqtSlot()
    def plotLoadedData(self):
        """
        Update plots with displacement data corresponding to
        points selected/hovered over on Map
        If reference curve (on plot) or reference zone (on map) are selected
        by the user, plot curves are adjusted to reference
        Called by mouseMoveEvent and MousePressEvent on Map

        """
        print("myPlotWidget -- plotLoadedData")
        # remove nodata message if any:
        try:
            self.main_plot.removeItem(self.nd_text)
            self.main_plot.autoRange()
        except Exception:
            # TODO: this looks dubious...check it?
            pass

        c = self.curves
        if self.parentWidget().zoom_button.isChecked():
            cz = self.curves2
        if self.ptype == 'temporal':
            x = np.array(self.plot_model.timestamps)
            y = self.plot_model.data_for_temporal_graph
            nb_lines = min(self.plot_model.pts_on_trace,
                           self.plot_model.nMaxPoints)
            # print("x = ",x)
            # print("y = ",y)
            # print("nb_lines = ",nb_lines)
            if self.plot_model.ref_curve_id is not None:
                y = y - self.plot_model.ref_curve_data
            elif self.plot_model.ref_pointers is not None:
                y = y - self.plot_model.ref_data
        elif self.ptype == 'spatial':
            y = self.plot_model.data_for_spatial_graph
            if self.plot_model.plot_istate != 4:
                # to prevent prb with nans:
                i = min(self.plot_model.pts_on_trace,
                        self.plot_model.nMaxPoints)
                x = self.plot_model.cumdistances[:i]
                try:
                    y = y[:, :i]
                except IndexError:
                    print('clear first')
                nb_lines = self.plot_model.number_of_dates

        # if all y is no data, display message:
        if np.isnan(y).all():
            # self.nd_text = pg.TextItem(text='no data',
            #                            anchor=(0.5, 0.5),
            #                            border='w',
            #                            fill=(0, 0, 255, 100))
            # self.nd_text.setPos(5., 5.)
            # self.main_plot.addItem(self.nd_text)
            # self.main_plot.setYRange(0., 10.)
            # self.main_plot.setXRange(0., 10.)
            x = np.array([0.])
            y = np.array([0.])

        # plot data:
        if self.plot_model.plot_istate == LIVE:
            if (not self.plot_model.ready_for_REF and
                not self.plot_model.ready_for_PROFILE and
                not self.plot_model.ready_for_POINTS):
                if self.ptype == 'temporal':
                    # live plotting
                    self.icurve.setData(x, y)
                    if self.parentWidget().zoom_button.isChecked():
                        self.icurve2.show()
                        self.icurve2.setData(x, y)

        # elif self.plot_model.plot_istate == REF:
        #     # self.plot_model.update_ref_values(self.plot_model.ref_pointers)
        #     pass
        else:
            # profiling
            try:
                self.icurve.hide()
                self.icurve2.hide()
            except AttributeError:
                pass
            for line in range(nb_lines):
                c[line].setData(x, y[line], name=str(line))
                if self.parentWidget().zoom_button.isChecked():
                    cz[line].setData(x, y[line], name=str(line))

        print("myPlotWidget -- plotLoadedData --finished")

    def updateZoomPlot(self):
        """
        Update zoom plot using new x-axis range set in main plot ROI

        Returns
        -------
        None
        """
        print("myPlotWidget -- updatezoomPlot")
        self.zoom_plot.setXRange(*self.lr.getRegion(), padding=0)

    def updateZoomRegion(self):
        """
        Update main plots's ROI to match zoom plot's new x-axis range

        Returns
        -------
        None
        """
        print("myPlotWidget -- updatezoomRegion")
        self.lr.setRegion(self.zoom_plot.getViewBox().viewRange()[0])

    def dataPointsClicked(self, points, ev):
        """
        Overloaded signal.
        Display coordinates of clicked data point and
        highlight clicked curve in the main plot.
        Receive param from sigPointsClicked signal on main plot's curves.

        Parameters
        ----------
        points : plotDataItem
            the 1st param name `first`
        ev : list
            list of SpotItems (see pyqtgraph doc) corresponding to the
            clicked point (or points?)

        Returns
        -------
        None
        """

        print("myPlotWidget -- dataPointsClicked")
        # points=plotDataItem (curve), ev=SpotItem (selected point on curve)

        # highlight point on Map:
        self.plot_model.map_model.show_points(
            pointers=self.plot_model.all_pointer_ij,
            highlight=points.name())
        # restore state of previous data selected:
        if self.prev_points:
            self.prev_points.setPen(self.saved_pen)
            try:
                # if prev clicked point for data info
                self.main_plot.removeItem(self.text)
                self.main_plot.removeItem(self.arrow)
            except AttributeError:
                # if prev clicked point for different ref
                pass

        # save state to be restored at next data selection:
        self.saved_pen = points.opts['pen']

        # highlight current data selection:
        points.setPen(width=4, color=(0, 255, 0))

        if (
                self.plot_model.ref_is_checked and
                self.ptype == 'temporal'):
            self.plot_model.ref_curve_id = int(points.name())
            self.plot_model.ref_curve_data = \
                self.plot_model.data_for_temporal_graph[
                    self.plot_model.ref_curve_id]
            self.plotLoadedData()

        else:
            # add selected data point info
            self.arrow = pg.ArrowItem(pos=(ev[0].pos()), angle=-90)
            self.main_plot.addItem(self.arrow)

            if self.ptype == 'temporal':
                t = datetime.datetime.utcfromtimestamp(
                    ev[0].pos().x()).strftime('%Y-%m-%d')
                self.text = pg.TextItem(text=(f"{t}"
                                              f"\n{ev[0].pos().y():.3f}"),
                                        anchor=(0.5, 1.5),
                                        border='w',
                                        fill=(0, 0, 255, 100))
            elif self.ptype == 'spatial':
                self.text = pg.TextItem(text=(f"{ev[0].pos().x():.3f}"
                                              f"\n{ev[0].pos().y():.3f}"),
                                        anchor=(0.5, 1.5),
                                        border='w',
                                        fill=(0, 0, 255, 100))

            self.main_plot.addItem(self.text)
            self.text.setPos(ev[0].pos())
            # ev[0].setSize(20)

        self.prev_points = points

    @pyqtSlot(bool)
    def setStyle(self, style):
        """
        Set the plot theme (light or dark).
        Called when clicking on theme button, alternate between dark and
        light.

        """
        print("myPlotWidget -- setStyle")
        self.style = style
        (ax1, ax2) = (self.main_plot.getAxis('bottom'),
                      self.main_plot.getAxis('left'))

        if self.style == 0:
            # black background
            self.setBackground('k')
            self.main_plot.setTitle(self.main_plot.titleLabel.text,
                                    color=.5)
            ax1.setPen(), ax2.setPen()
            ax1.setTextPen(), ax2.setTextPen()

            if self.ptype == 'temporal':
                self.main_plot.showGrid(x=True, y=False, alpha=1.)
                self.date_marker.setPen(pg.mkPen(color='w',
                                                 width=3.),)
                # pen = [(idx/self.nPlots*255) for idx in range(self.nPlots)]
                for i in range(self.nPlots):
                    self.curves[i].setPen(0.5)#(255, 255, 255, pen[i]))
            elif self.ptype == 'spatial':
                for i in self.main_plot.curves:
                    i.setPen(0.5)
                self.main_plot.curves[self.plot_model.date_number].setPen(
                    {'color': 'w', 'width': 4})

            try:
                self.zoom_plot.setTitle(self.zoom_plot.titleLabel.text,
                                        color=.5)
                (ax1z, ax2z) = (self.zoom_plot.getAxis('bottom'),
                                self.zoom_plot.getAxis('left'))
                ax1z.setPen(), ax2z.setPen()
                ax1z.setTextPen(), ax2z.setTextPen()
                # if self.ptype == 'spatial':
                for i in self.curves2:
                    i.setPen(0.5)
                if self.ptype == 'spatial':
                    self.curves2[self.plot_model.date_number].setPen(
                        {'color': 'w', 'width': 4})
            except AttributeError:
                pass

        else:
            # white background
            self.setBackground('w')
            self.main_plot.setTitle(self.main_plot.titleLabel.text, color='k')
            ax1.setPen('k'), ax2.setPen('k')
            ax1.setTextPen('k'), ax2.setTextPen('k')
            if self.ptype == 'temporal':
                self.main_plot.showGrid(x=True, y=False, alpha=1.)
                self.date_marker.setPen(pg.mkPen(color='k',
                                                 width=3.),)
                pen = [(idx/self.nPlots*255) for idx in range(self.nPlots)]
                for i in range(self.nPlots):
                    self.curves[i].setPen(0.5)#(0, 0, 0, pen[i]))
            elif self.ptype == 'spatial':
                for i in self.main_plot.curves:
                    i.setPen(0.5)
                self.main_plot.curves[self.plot_model.date_number].setPen(
                    {'color': 'k', 'width': 4})

            try:
                self.zoom_plot.setTitle(
                    self.zoom_plot.titleLabel.text, color='k')
                (ax1z, ax2z) = (self.zoom_plot.getAxis('bottom'),
                                self.zoom_plot.getAxis('left'))
                ax1z.setPen('k'), ax2z.setPen('k')
                ax1z.setTextPen('k'), ax2z.setTextPen('k')
                # if self.ptype == 'spatial':
                for i in self.curves2:
                    i.setPen(0.5)
                if self.ptype == 'spatial':
                    self.curves2[self.plot_model.date_number].setPen(
                    {'color': 'k', 'width': 4})

            except AttributeError:
                pass

        # update view: for some reason, just 'show' is not enough:
        self.repaint()
        # self.hide()
        # self.show()
        print("myPlotWidget -- setStyle -- finished")



# VIEWS ########################################################################################################################
# VIEWS ########################################################################################################################

class myPlotWindow_gps(QWidget):
    """
    Window to display the plots
    """

    def __init__(self, plot_model, plottype):
        """
        New window to display the plots

        Parameters
        ----------
        plot_model : QObject
            model managing the data for the plots
        plottype : str
            type of plot, can be 'temporal' or 'spatial'

        Returns
        -------
        None
        """
        print("myPlotWindow_gps -- object creation")
        super().__init__()
        self.plot_model = plot_model
        self.ptype = plottype
        self.initUI()
        print("myPlotWindow_gps -- object creation --  finished")

    def initUI(self):
        """
        Initialize user interface

        """

        self.setWindowTitle((self.ptype + " profile").title())

        # init plot widget:
        self.plot_widget = myPlotWidget_gps(plottype=self.ptype,
                                        plot_model=self.plot_model)

        # Toolbar:
        self.toolbar = QToolBar("Graph toolbar")
        # self.zoom_button = QPushButton('Zoom')
        # self.zoom_button.setCheckable(True)
        self.theme_switch = AnimatedToggle()
        self.theme_switch.toggled.connect(self.plot_widget.setStyle)

        # self.toolbar.addWidget(self.zoom_button)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(QLabel('black'))
        self.toolbar.addWidget(self.theme_switch)
        self.toolbar.addWidget(QLabel('white'))
        self.toolbar.addSeparator()
        if self. ptype == 'temporal':
            self.ref_tick = QCheckBox('Reference', self)
            self.ref_tick.setCheckable(True)
        # self.ref_tick.stateChanged.connect(
        #     lambda: self.plot_widget.connect_CurveClicked_Ref(
        #         self.ref_tick))
            self.ref_tick.stateChanged.connect(self.set_ref_status)
            self.toolbar.addWidget(self.ref_tick)
            self.toolbar.addSeparator()

            self.toolbar.addWidget(QLabel('Stations'))
            self.menu_station = QComboBox()
            self.menu_station.addItems(self.plot_model.station_gps)
            self.menu_station.currentIndexChanged.connect(self.update_station)
            self.toolbar.addWidget(self.menu_station)

            self.toolbar.addSeparator()
            self.toolbar.addWidget(QLabel('Stations'))
            self.menu_orientation = QComboBox()
            self.menu_orientation.addItems(['east', 'north', 'up'])
            self.menu_orientation.setCurrentText('up')
            self.menu_orientation.currentIndexChanged.connect(self.update_station)
            self.toolbar.addWidget(self.menu_orientation)

        # layout
        layout = QVBoxLayout()
        layout.setMenuBar(self.toolbar)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        # only for temporal plot:
        # check box to fix axes when hovering on Map:
        if self.ptype == 'temporal':
            self.check_axes = QCheckBox('Lock axes', self)
            self.check_axes.setToolTip("When checked, keep axes ranges while"
                                       " hovering on Map. Note that you can "
                                       " still zoom in/out on the plot.")
            self.check_axes.stateChanged.connect(
                lambda: self.ctrl_axes(self.check_axes))
            layout.addWidget(self.check_axes)
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

        # connect signals:
        # self.zoom_button.toggled.connect(self.plot_widget.init_zoom)

    def ctrl_axes(self, box):
        print("myPlotWindow_gps -- ctrl_axes")
        if box.isChecked():
            self.plot_widget.main_plot.autoBtn.mode = 'fix'
        else:
            self.plot_widget.main_plot.autoBtn.mode = 'auto'
        self.plot_widget.main_plot.autoBtnClicked()

    # def on_button_clicked_clearplot(self):
    #     """
    #     called when clicking clear profile button in MainWindow
    #     remove and reset plots

    #     """
    #     print("myPlotWindow_gps -- on_button_clicked_clearplot")
    #     if self.zoom_button.isChecked():
    #         self.plot_widget.removeItem(self.plot_widget.zoom_plot)
    #     self.zoom_button.setChecked(False)
    #     self.plot_widget.removeItem(self.plot_widget.main_plot)
    #     # keep track of style, init, re-set same style:+
    #     style = self.plot_widget.style
    #     self.plot_widget.initUI()
    #     self.plot_widget.setStyle(style)
    #     self.plot_model.plot_istate = 4
    #     if self.ptype == 'temporal':
    #         self.check_axes.setChecked(False)
    #         self.ref_tick.setChecked(False)
    #         # self.ref_tick.setVisible(False)
    #     self.plot_model.ref_curve_data = None
    #     self.plot_model.ref_curve_id = None
    #     self.plot_model.ref_pointers = None
    #     print("myPlotWindow_gps -- on_button_clicked_clearplot -- finished")

    def set_ref_status(self):
        print("myPlotWindow_gps -- set_ref_status")
        print("-- ref_tick = ", self.ref_tick.isChecked())
        self.plot_model.ref_is_checked = self.ref_tick.isChecked()
        if (
                not self.plot_model.ref_is_checked and
                self.plot_model.plot_istate == 0):

            self.plot_model.ref_curve_id = None
            self.plot_widget.plotLoadedData()

        else:
            self.plot_widget.plotLoadedData()
        print("myPlotWindow_gps -- set_ref_status finished")

    def update_station(self):
        """ Function call when station sselector has changed
        """
        print("myPlotWindow_gps -- update_station")


        # rinitialise reference option
        self.ref_tick.setChecked(False)
        # print(self.menu_station.currentText())
        self.plot_model.on_data_reloaded(self.menu_station.currentText(), self.menu_orientation.currentText())       # update selected gps station data and map
        # print("PlotView -- plot_istate = ", self.plot_model.plot_istate)
        self.plot_model.plot_istate = "LIVE"
        # print("PlotView -- plot_istate = ", self.plot_model.plot_istate)


        self.plot_widget.plotLoadedData()                                       # Plot selected gps station data


        print("myPlotWindow_gps -- update_station -- finished")




# VIEWS ########################################################################################################################
# VIEWS ########################################################################################################################



class myPlotWidget_gps(pg.GraphicsLayoutWidget):
    """
    Based on pyqtgraph's GraphicsLayoutWidget
    layout to display main and zoom plots
    """

    def __init__(self, plottype, plot_model):
        """
        ...

        Parameters
        ----------
        plottype : str
            type of plot, can be 'temporal' or 'spatial'
        plot_model :
            model managing the data for the plots

        """
        print("myPlotWidget_gps -- object creation")

        super().__init__()
        self.plot_model = plot_model
        self.ptype = plottype
        self.plot_ref = False
        self.plot_ref_y = 0
        self.plot_ref_y_gps = 0

        self.initUI()
        print("myPlotWidget_gps -- object creation -- finished")


    def initUI(self):
        """
        Initialize user interface: main plot and its items (curves), and
        current date marker

        """
        self.prev_points = None


        self.main_plot = self.addPlot(
            title="<b>Temporal profile</b>\
                <br>1 line/point on Map's profile")
        # x-axis:
        if isinstance(self.plot_model.timestamps, range):
            # dates not available: regular x-axis
            self.main_plot.setLabel('bottom',
                                    "Band/Date #")
        else:
            # dates available: x-axis is a TimeAxisItem
            self.main_plot.setAxisItems(
                {'bottom': TimeAxisItem(text='Date',
                                        units='yyyy-mm-dd')})
        # y-axis:
        self.main_plot.showGrid(x=True, y=False, alpha=1.)
        # number of lines on plot:
        self.nPlots = self.plot_model.nMaxPoints
        # pen = [(idx, self.nPlots*1.3) for idx in range(self.nPlots)]
        # pen = [((idx)/(self.nPlots-0.1)) for idx in range(self.nPlots)]
        # pen = [(idx/self.nPlots*255) for idx in range(self.nPlots)]
        # pen = np.ones(self.nPlots)

        # vertical line as temporal marker synchronized with slider:
        self.date_marker = DateMarker(pos=self.plot_model.current_date,
                                      plot_model=self.plot_model)
        self.main_plot.addItem(self.date_marker)

        # interactive curve
        self.icurve = pg.PlotDataItem(pen=pg.mkPen((255, 0, 0), width=2),
                                      symbol='o',
                                      symbolSize=5,
                                      antialias=True)
        self.icurve_gps = pg.PlotDataItem(pen=pg.mkPen((255, 255, 0), width=2),
                                      # symbol='o',
                                      symbolSize=2,
                                      antialias=True)

        self.icurve.sigPointsClicked.connect(self.dataPointsClicked)
        self.icurve_gps.sigPointsClicked.connect(self.dataPointsClicked)
        self.main_plot.addItem(self.icurve)
        self.main_plot.addItem(self.icurve_gps)



        # plot curves init, all their data is None
        self.curves = []
        for idx in range(self.nPlots):
            self.curve = pg.PlotDataItem(pen='w', #pg.mkPen(
                                            #(255, 255, 255, pen[idx]),
                                            #width=2),
                                         symbol='o',
                                         symbolSize=5,
                                         antialias=True)
            self.curve.opts['name'] = idx
            self.curve.sigPointsClicked.connect(self.dataPointsClicked)
            # self.curve.sigClicked.connect(self.plotLoadedData_toRef)
            self.main_plot.addItem(self.curve)
            self.curves.append(self.curve)

        self.setStyle(0)


    
    @pyqtSlot()
    def plotLoadedData(self):
        """
        Update plots with displacement data corresponding to
        points selected/hovered over on Map
        If reference curve (on plot) or reference zone (on map) are selected
        by the user, plot curves are adjusted to reference
        Called by mouseMoveEvent and MousePressEvent on Map

        """
        # remove nodata message if any:
        print("myPlotWidget_gps -- plotLoadData")
        try:
            self.main_plot.removeItem(self.nd_text)
            self.main_plot.autoRange()
        except Exception:
            # TODO: this looks dubious...check it?
            pass

        c = self.curves
        # if self.parentWidget().zoom_button.isChecked():
        #     cz = self.curves2
        if self.ptype == 'temporal':
            x = np.array(self.plot_model.timestamps)
            y = self.plot_model.data_for_temporal_graph

            x_gps = self.plot_model.thispoint_gps_date
            y_gps = self.plot_model.data_gps_for_temporal_graph 
            # print("y_gps length = ", len(y_gps))
            # y_gps = self.plot_model.thispoint_gps_up 


            nb_lines = min(self.plot_model.pts_on_trace,
                           self.plot_model.nMaxPoints)


            # print("x = ",x)
            # print("y = ",y)

            # print("x_gps = ",x_gps)
            # print("y_gps = ",y_gps)

            # print("nb_lines = ",nb_lines)

            # Aligne both curve on a new reference 0 by clicking on the deformation plot
            if self.plot_ref:

                # manage gps ref value finding the indice of closest point from timestamp of clickek events
                # Calculate new time series based on reference
                x_array = np.asarray(x)                                 # Convert timestamp array 
                idx = (np.abs(x_array - self.plot_ref_x)).argmin()      # extract index from points clicekd by user (or closest points)
                y_r = y - y[int(idx)]                   # substract from all points in y axis the y value at the index
                print("-----> y idx = ", idx)
                print("-----> y ref  = ", y[int(idx)])


                x_gps_array = np.asarray(x_gps)                         # Convert timestamp array 
                idx = (np.abs(x_gps_array - self.plot_ref_x)).argmin()  # extract index from points clicekd by user (or closest points)
                y_gps_r = [x - y_gps[int(idx)] for x in y_gps]          # substract from all points in y axis the y value at the index
                print("-----> y_gps idx = ", idx)
                print("-----> y_gps ref  = ", y_gps[int(idx)])


                if np.isnan(y_r).all():
                    x = np.array([0.])
                    y_r = np.array([0.])


            # if self.plot_model.ref_curve_id is not None:
            #     y = y - self.plot_model.ref_curve_data
            # elif self.plot_model.ref_pointers is not None:
            #     y = y - self.plot_model.ref_data


        elif self.ptype == 'spatial':
            y = self.plot_model.data_for_spatial_graph
            if self.plot_model.plot_istate != 4:
                # to prevent prb with nans:
                i = min(self.plot_model.pts_on_trace,
                        self.plot_model.nMaxPoints)
                x = self.plot_model.cumdistances[:i]
                try:
                    y = y[:, :i]
                except IndexError:
                    print('clear first')
                nb_lines = self.plot_model.number_of_dates

        # if all y is no data, display message:
        if np.isnan(y).all():
            # self.nd_text = pg.TextItem(text='no data',
            #                            anchor=(0.5, 0.5),
            #                            border='w',
            #                            fill=(0, 0, 255, 100))
            # self.nd_text.setPos(5., 5.)
            # self.main_plot.addItem(self.nd_text)
            # self.main_plot.setYRange(0., 10.)
            # self.main_plot.setXRange(0., 10.)
            x = np.array([0.])
            y = np.array([0.])



        # plot data:
        # if self.plot_model.plot_istate == LIVE:
        #     if (not self.plot_model.ready_for_REF and
        #         not self.plot_model.ready_for_PROFILE and
        #         not self.plot_model.ready_for_POINTS):
        #         if self.ptype == 'temporal':
        #             # live plotting
        if self.plot_ref:
            self.icurve.setData(x, y_r)
            self.icurve_gps.setData(x_gps, y_gps_r)
        else:
            self.icurve.setData(x, y)
            self.icurve_gps.setData(x_gps, y_gps)
        self.plot_ref = False


        # if self.parentWidget().zoom_button.isChecked():
        #     self.icurve2.show()
        #     self.icurve2.setData(x, y)

        # elif self.plot_model.plot_istate == REF:
        #     # self.plot_model.update_ref_values(self.plot_model.ref_pointers)
        #     pass
        # else:
        #     # profiling
        #     try:
        #         self.icurve.hide()
        #         self.icurve2.hide()
        #     except AttributeError:
        #         pass
        #     for line in range(nb_lines):
        #         c[line].setData(x, y[line], name=str(line))
        #         if self.parentWidget().zoom_button.isChecked():
        #             cz[line].setData(x, y[line], name=str(line))

        print("myPlotWidget_gps -- plotLoadData -- finished")

    # @pyqtSlot(bool)
    # def init_zoom(self, checked):
    #     """
    #     Initialize zoom plot: init selection ROI in main plot, creates new
    #     plot (zoom plot) with x-axis range synchronized with
    #     main plot's selection region, plot same data as main plot.
    #     Called when clicking 'Zoom' button in plot window.

    #     Parameters
    #     ----------
    #     checked : bool
    #         True if Zoom button is toggled

    #     """
    #     print("myPlotWidget_gps -- init_zoom")

    #     current_style = self.style
    #     if checked:
    #         # selection region on main plot:
    #         # init on central 20% of data range:
    #         if self.ptype == 'temporal':
    #             xvals = self.plot_model.timestamps
    #         elif self.ptype == 'spatial':
    #             xvals = range(20)
    #         self.lr = pg.LinearRegionItem(
    #             np.percentile(
    #                 xvals,
    #                 [50 * (1 - 0.2), 50 * (1 + 0.2)]))
    #         self.main_plot.addItem(self.lr)

    #         # zoom plot init:
    #         self.zoom_plot = self.addPlot(title="Zoom on selected region")
    #         if self.ptype == 'temporal':
    #             if isinstance(self.plot_model.timestamps, range):
    #                 # dates not available: regular x-axis
    #                 self.zoom_plot.setLabel('bottom', "Band/Date #")
    #             else:
    #                 # dates available: x-axis is a TimeAxisItem
    #                 self.zoom_plot.setAxisItems(
    #                     {'bottom': TimeAxisItem(
    #                         text='Date', units='yyyy-mm-dd')})
    #             # pen = [(idx, self.nPlots*1.3) for idx in range(self.nPlots)]
    #         elif self.ptype == 'spatial':
    #             self.zoom_plot.setLabel('bottom',
    #                                     "Distance along profile line",
    #                                     units='pixel')
    #             # pen = np.ones(self.nPlots)

    #         self.icurve2 = pg.PlotDataItem(pen=pg.mkPen((255, 0, 0), width=2),
    #                                        symbol='o',
    #                                        symbolSize=5,
    #                                        antialias=True)
    #         self.icurve2.sigPointsClicked.connect(self.dataPointsClicked)
    #         self.zoom_plot.addItem(self.icurve2)

    #         self.curves2 = []
    #         for idx in range(self.nPlots):
    #             self.curve2 = pg.PlotDataItem(pen='w', #pen[idx],
    #                                           symbol='o',
    #                                           symbolSize=5,
    #                                           antialias=True)
    #             self.zoom_plot.addItem(self.curve2)
    #             self.curves2.append(self.curve2)

    #         if self.curves[0].dataBounds(1)[1] is not None:
    #             # data already plotted in main_plot, set same data in zoom plot
    #             self.plotLoadedData()

    #         self.lr.sigRegionChanged.connect(self.updateZoomPlot)
    #         self.zoom_plot.sigXRangeChanged.connect(self.updateZoomRegion)
    #         self.updateZoomPlot()
    #     else:
    #         self.main_plot.removeItem(self.lr)
    #         self.zoom_plot.hide()

    #     self.setStyle(current_style)
    #     print("myPlotWidget_gps -- init_zoom -- finished")


    # def updateZoomPlot(self):
    #     """
    #     Update zoom plot using new x-axis range set in main plot ROI

    #     Returns
    #     -------
    #     None
    #     """
    #     print("myPlotWidget_gps -- updateZoomPlot")
    #     self.zoom_plot.setXRange(*self.lr.getRegion(), padding=0)

    # def updateZoomRegion(self):
    #     """
    #     Update main plots's ROI to match zoom plot's new x-axis range

    #     Returns
    #     -------
    #     None
    #     """
    #     print("myPlotWidget_gps -- updateZoomRegion")
    #     self.lr.setRegion(self.zoom_plot.getViewBox().viewRange()[0])

    def dataPointsClicked(self, points, ev):
        """
        Overloaded signal.
        Display coordinates of clicked data point and
        highlight clicked curve in the main plot.
        Receive param from sigPointsClicked signal on main plot's curves.

        Parameters
        ----------
        points : plotDataItem
            the 1st param name `first`
        ev : list
            list of SpotItems (see pyqtgraph doc) corresponding to the
            clicked point (or points?)

        Returns
        -------
        None
        """
        # points=plotDataItem (curve), ev=SpotItem (selected point on curve)

        # highlight point on Map:
        print("myPlotWidget_gps -- dataPointsClicked")

        # self.plot_model.map_model.show_points(
        #     pointers=self.plot_model.all_pointer_ij,
        #     highlight=points.name())
        # # restore state of previous data selected:
        # if self.prev_points:
        #     self.prev_points.setPen(self.saved_pen)
        #     try:
        #         # if prev clicked point for data info
        #         self.main_plot.removeItem(self.text)
        #         self.main_plot.removeItem(self.arrow)
        #     except AttributeError:
        #         # if prev clicked point for different ref
        #         pass

        # save state to be restored at next data selection:
        self.saved_pen = points.opts['pen']

        # highlight current data selection:
        # points.setPen(width=4, color=(0, 255, 0))

        if (
                self.plot_model.ref_is_checked and
                self.ptype == 'temporal'):

            # self.plot_model.ref_curve_id = int(points.name())
            # self.plot_model.ref_curve_data = \
            #     self.plot_model.data_for_temporal_graph[
            #         self.plot_model.ref_curve_id]
            self.plot_ref = True
            self.plot_ref_x = ev[0].pos().x()
            # self.plot_ref_y_gps = 
            self.plotLoadedData()

        # else:
        #     # add selected data point info
        #     self.arrow = pg.ArrowItem(pos=(ev[0].pos()), angle=-90)
        #     self.main_plot.addItem(self.arrow)

        #     if self.ptype == 'temporal':
        #         t = datetime.datetime.utcfromtimestamp(
        #             ev[0].pos().x()).strftime('%Y-%m-%d')
        #         self.text = pg.TextItem(text=(f"{t}"
        #                                       f"\n{ev[0].pos().y():.3f}"),
        #                                 anchor=(0.5, 1.5),
        #                                 border='w',
        #                                 fill=(0, 0, 255, 100))
        #     # elif self.ptype == 'spatial':
        #     #     self.text = pg.TextItem(text=(f"{ev[0].pos().x():.3f}"
        #     #                                   f"\n{ev[0].pos().y():.3f}"),
        #     #                             anchor=(0.5, 1.5),
        #     #                             border='w',
        #     #                             fill=(0, 0, 255, 100))

        #     self.main_plot.addItem(self.text)
        #     self.text.setPos(ev[0].pos())
        #     # ev[0].setSize(20)

        self.prev_points = points

        print("myPlotWidget_gps -- dataPointsClicked -- finished")

    @pyqtSlot(bool)
    def setStyle(self, style):
        """
        Set the plot theme (light or dark).
        Called when clicking on theme button, alternate between dark and
        light.

        """
        print("myPlotWidget_gps -- setStyle")
        self.style = style
        (ax1, ax2) = (self.main_plot.getAxis('bottom'),
                      self.main_plot.getAxis('left'))

        if self.style == 0:
            # black background
            self.setBackground('k')
            self.main_plot.setTitle(self.main_plot.titleLabel.text,
                                    color=.5)
            ax1.setPen(), ax2.setPen()
            ax1.setTextPen(), ax2.setTextPen()

            if self.ptype == 'temporal':
                self.main_plot.showGrid(x=True, y=False, alpha=1.)
                self.date_marker.setPen(pg.mkPen(color='w',
                                                 width=3.),)
                # pen = [(idx/self.nPlots*255) for idx in range(self.nPlots)]
                for i in range(self.nPlots):
                    self.curves[i].setPen(0.5)#(255, 255, 255, pen[i]))
            elif self.ptype == 'spatial':
                for i in self.main_plot.curves:
                    i.setPen(0.5)
                self.main_plot.curves[self.plot_model.date_number].setPen(
                    {'color': 'w', 'width': 4})

            # try:
            #     self.zoom_plot.setTitle(self.zoom_plot.titleLabel.text,
            #                             color=.5)
            #     (ax1z, ax2z) = (self.zoom_plot.getAxis('bottom'),
            #                     self.zoom_plot.getAxis('left'))
            #     ax1z.setPen(), ax2z.setPen()
            #     ax1z.setTextPen(), ax2z.setTextPen()
            #     # if self.ptype == 'spatial':
            #     for i in self.curves2:
            #         i.setPen(0.5)
            #     if self.ptype == 'spatial':
            #         self.curves2[self.plot_model.date_number].setPen(
            #             {'color': 'w', 'width': 4})
            # except AttributeError:
            #     pass

        else:
            # white background
            self.setBackground('w')
            self.main_plot.setTitle(self.main_plot.titleLabel.text, color='k')
            ax1.setPen('k'), ax2.setPen('k')
            ax1.setTextPen('k'), ax2.setTextPen('k')
            if self.ptype == 'temporal':
                self.main_plot.showGrid(x=True, y=False, alpha=1.)
                self.date_marker.setPen(pg.mkPen(color='k',
                                                 width=3.),)
                pen = [(idx/self.nPlots*255) for idx in range(self.nPlots)]
                for i in range(self.nPlots):
                    self.curves[i].setPen(0.5)#(0, 0, 0, pen[i]))
            elif self.ptype == 'spatial':
                for i in self.main_plot.curves:
                    i.setPen(0.5)
                self.main_plot.curves[self.plot_model.date_number].setPen(
                    {'color': 'k', 'width': 4})

            # try:
            #     self.zoom_plot.setTitle(
            #         self.zoom_plot.titleLabel.text, color='k')
            #     (ax1z, ax2z) = (self.zoom_plot.getAxis('bottom'),
            #                     self.zoom_plot.getAxis('left'))
            #     ax1z.setPen('k'), ax2z.setPen('k')
            #     ax1z.setTextPen('k'), ax2z.setTextPen('k')
            #     # if self.ptype == 'spatial':
            #     for i in self.curves2:
            #         i.setPen(0.5)
            #     if self.ptype == 'spatial':
            #         self.curves2[self.plot_model.date_number].setPen(
            #         {'color': 'k', 'width': 4})

            # except AttributeError:
            #     pass

        # update view: for some reason, just 'show' is not enough:
        self.repaint()
        # self.hide()

        print("myPlotWidget_gps -- setStyle -- finished")
