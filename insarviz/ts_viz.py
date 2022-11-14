#!/usr/bin/env python3

import logging
import os, re

from PyQt5.QtWidgets import (
    QSizePolicy, QApplication, QLabel, QWidget,
    QSlider, QMainWindow, QFileDialog, QToolBar,
    QDockWidget, QSpinBox, QAction, QActionGroup,
    QHeaderView, QVBoxLayout, QHBoxLayout,
    )

from PyQt5.QtGui import (
    QPixmap, QFont, QIcon,
    )

from PyQt5.QtCore import (
    Qt, QCoreApplication,
    pyqtSlot,
    )

from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView
from PyQt5.QtGui import QPainter


from insarviz.Loader import Loader
from insarviz.Loader import Loader_gps
from insarviz.PaletteView import Palette
from insarviz.map.MapModel import MapModel
from insarviz.map.MapView import MapView
from insarviz.map.MinimapView import MinimapView
from insarviz.PlotModel import PlotModel, PlotModel_gps
from insarviz.PlotView import myPlotWindow, myPlotWindow_gps
import insarviz.version as version

import numpy as np

from insarviz.Interaction import IDLE, DRAG, ZOOM, PROFILE, LIVE
from insarviz.utils import openUrl
from insarviz.custom_widgets import FileInfoWidget

# from insarviz.GraphicScene_example_rectangle_resize import GraphicsRectItem
from PyQt5.Qt import QRubberBand
from PyQt5.Qt import QRect

logging.getLogger("rasterio").setLevel(logging.WARNING) # original WARNING
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Docstring for MainWindow. """

    def __init__(self, filename=None, config_dict=None, stack_file=None):
        """
        :filename: the file to load
        :config_dict: the configuration dictionary
        """

        print("MainWindow -- object creation")
        super().__init__()
        self.config_dict = config_dict
        self.stack_file = stack_file
        # print("stack_file = ", stack_file)
        if self.stack_file:
            self.keep_stack = True
        else:
            self.keep_stack = False
            self.stack_file = "stack.tif"
        self.initUI(filename)
        self.filename = filename

        print("MainWindow -- object creation -- finished")

    def initUI(self, filename):
        """
        initialize user interface

        :filename: the file to load
        :returns: None

        """
        # various init:
        self.setWindowTitle("InsarViz")
        self.setMouseTracking(True)
        self.setDockNestingEnabled(True)
        self.plotw_t = None
        self.plotw_t_gps = None

        # Loader:
        loader = Loader(self.stack_file)

        # Models:
        nMaxPoints = 30
        self.map_model = MapModel(loader, nMaxPoints)
        self.plot_model = PlotModel(loader, nMaxPoints)
        self.plot_model.map_model = self.map_model
        self.map_model.plot_model = self.plot_model

        # Map:
        self.map_widget = MapView(self.map_model, self.plot_model)
        # force initializeGL, needed if file specified upon app launch:
        self.map_widget.show()
        self.map_widget.setMouseTracking(True)
        self.map_widget.cursor_changed.connect(self.update_cursor_info)

        # Minimap
        self.minimap_widget = MinimapView(self.map_model)
        # force initializeGL, needed if file specified upon app launch:
        self.minimap_widget.show()
        self.minimap_dock_widget = QDockWidget('General view', self)
        self.minimap_dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea)
        self.minimap_dock_widget.setWidget(self.minimap_widget)

        # Palette
        self.palette_widget = Palette(self.map_widget, self.minimap_widget)

        # Palette dock widget
        self.palette_dock_widget = QDockWidget('Colormap', self)
        self.palette_dock_widget.setAllowedAreas(Qt.RightDockWidgetArea)
        self.palette_dock_widget.setWidget(self.palette_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.palette_dock_widget)

        # dates slider:
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setMinimum(-1)  # change from 0 to -1 to see change to 0
        self.slider.setValue(-1)    # initialise to -1 to see change to 0
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(1)
        self.slider.valueChanged.connect(self.display_date) # original
        #self.slider.valueChanged.connect(self.display_date2)
        # allow arrow keys press to change date:
        self.slider.setFocusPolicy(Qt.StrongFocus)

        # current date label:
        self.date_label = QLabel('Click Open to load data')
        self.date_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.date_label.setMaximumHeight(20)
        self.band_setter = QSpinBox()
        self.band_setter.valueChanged.connect(self.slider.setValue)

        # Logo & version
        self.logo_widget = QLabel(self)
        scriptDir = os.path.dirname(
            os.path.dirname(os.path.realpath(__file__)))
        pix = QPixmap(scriptDir + os.path.sep + 'doc/images/logo_insarviz.png')
        self.logo_widget.setPixmap(
            pix.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_text_widget = QLabel(f"InsarViz v.{version.__version__}", self)
        logo_text_widget.setFont(QFont("Arial", 15, QFont.Bold))
        layout_logo = QHBoxLayout()
        layout_logo.addWidget(self.logo_widget)
        layout_logo.addWidget(logo_text_widget)
        layout_logo.addStretch()
        logoandtext_widget = QWidget()
        logoandtext_widget.setLayout(layout_logo)
        self.logo_dockwidget = QDockWidget('', self)
        self.logo_dockwidget.setWidget(logoandtext_widget)
        self.logo_dockwidget.setMaximumHeight(70)
        self.logo_dockwidget.setFeatures(QDockWidget.NoDockWidgetFeatures)
        # remove title bar:
        self.logo_dockwidget.setTitleBarWidget(QWidget())

        # Point info
        self.info_widget = QLabel('x=  , y=  ,z=  ')
        self.info_widget.setMargin(3)
        self.info_dockwidget = QDockWidget('Information', self)
        self.info_dockwidget.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.info_dockwidget.setWidget(self.info_widget)

        # Info tree
        self.fileinfo_widget = FileInfoWidget()
        self.fileinfo_dockwidget = QDockWidget('Contents', self)
        self.fileinfo_dockwidget.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.fileinfo_dockwidget.setWidget(self.fileinfo_widget)
        self.fileinfo_widget.header().setStretchLastSection(False)
        self.fileinfo_widget.header().setSectionResizeMode(
            QHeaderView.ResizeToContents)
        self.fileinfo_widget.expandAll()
        loader.profile_changed.connect(self.fileinfo_widget.update_fileinfo)

        # Main layout:
        main_layout = QVBoxLayout()
        time_layout = QHBoxLayout()
        time_layout.addWidget(self.date_label)
        time_layout.addWidget(self.band_setter)
        time_layout.addWidget(self.slider)
        main_layout.addLayout(time_layout)
        main_layout.addWidget(self.map_widget)
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        main_widget.resize(250, 250)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.logo_dockwidget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.info_dockwidget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.fileinfo_dockwidget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.minimap_dock_widget)

        # Profile toolbar
        self.plotting_toolbar = QToolBar("Plotting toolbar")
        self.plotting_toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        action_group = QActionGroup(self)
        self.inter_action = QAction("Interactive", self)
        self.inter_action.setIcon(QIcon(
            scriptDir + os.path.sep + 'icons/cursor.png'))
        self.inter_action.setCheckable(True)
        self.inter_action.setChecked(False)
        self.inter_action.triggered.connect(
            lambda: self.plot_model.set_plot_interaction(LIVE))
        self.inter_action.trigger()
        self.inter_action.triggered.connect(
            lambda: self.map_model.set_map_interaction(IDLE))
        self.inter_action.triggered.connect(
            lambda: self.plotw_t.ref_tick.setChecked(False))

        self.points_action = QAction("Points", self)
        self.points_action.setIcon(QIcon(
            scriptDir + os.path.sep + 'icons/points.png'))
        self.points_action.setIconText("Points")
        self.points_action.setCheckable(True)
        self.points_action.toggled.connect(self.map_model.set_ready_for_POINTS)
        self.points_action.toggled.connect(self.plot_model.set_ready_for_POINTS)

        self.prof_action = QAction("Profile", self)
        self.prof_action.setIcon(QIcon(
            scriptDir + os.path.sep + 'icons/profile.png'))
        self.prof_action.setIconText("Profile")
        self.prof_action.setCheckable(True)
        self.prof_action.toggled.connect(self.map_model.set_ready_for_PROFILE)
        self.prof_action.toggled.connect(self.plot_model.set_ready_for_PROFILE)

        self.ref_action = QAction("Reference", self)
        self.ref_action.setIcon(QIcon(
            scriptDir + os.path.sep + 'icons/ref.png'))
        self.ref_action.setIconText("Reference")
        self.ref_action.setCheckable(True)
        self.ref_action.toggled.connect(self.map_model.set_ready_for_REF)
        self.ref_action.toggled.connect(self.plot_model.set_ready_for_REF)
        self.ref_action.toggled.connect(
            lambda checked: self.plotw_t.ref_tick.setChecked(False))
        self.ref_action.toggled.connect(
            lambda checked: self.plotw_t.ref_tick.setCheckable(False))

        clear_action = QAction("Clear all", self)
        clear_action.triggered.connect(self.on_button_clicked_clear_plot)
        action_group.addAction(self.inter_action)
        action_group.addAction(self.points_action)
        action_group.addAction(self.prof_action)
        action_group.addAction(self.ref_action)
        # spacers to center buttons:
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        spacer2 = QWidget()
        spacer2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plotting_toolbar.addWidget(spacer)
        self.plotting_toolbar.addAction(self.inter_action)
        self.plotting_toolbar.addAction(self.points_action)
        self.plotting_toolbar.addAction(self.prof_action)
        self.plotting_toolbar.addAction(self.ref_action)
        self.plotting_toolbar.addAction(clear_action)
        self.plotting_toolbar.addWidget(spacer2)

        self.addToolBar(self.plotting_toolbar)
        self.plotting_toolbar.hide()

        # Menu
        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)

        imenu = menubar.addMenu('InsarViz')
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.on_button_clicked_quit)
        quit_action.setShortcut('Ctrl+Q')
        imenu.addAction(quit_action)
        menubar.addSeparator()

        filemenu = menubar.addMenu('File')
        open_action = QAction("Open", self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.on_button_clicked_open)
        filemenu.addAction(open_action)

        # add by maxime an option to open all binary in a folder
        openFolder_action = QAction("Open ENVI Folder", self)
        openFolder_action.setShortcut('Ctrl+P')
        openFolder_action.triggered.connect(self.on_button_clicked_openFolder)
        filemenu.addAction(openFolder_action)

        openGpsFolder_action = QAction("Open GPS Folder", self)
        openGpsFolder_action.setShortcut('Ctrl+G')
        openGpsFolder_action.triggered.connect(self.on_button_clicked_openGpsFolder)
        filemenu.addAction(openGpsFolder_action)

        viewmenu = menubar.addMenu('View')
        self.plot_act = QAction("Plotting", self)
        self.plot_act.setCheckable(True)
        self.plot_act.setChecked(False)
        self.plot_act.setEnabled(False)
        self.plot_act.toggled.connect(self.show_plot_window)
        self.plot_act.setShortcut('Ctrl+P')

        self.plot_gps_act = QAction("GPS Comparison", self)
        self.plot_gps_act.setCheckable(True)
        self.plot_gps_act.setChecked(False)
        self.plot_gps_act.setEnabled(False)
        self.plot_gps_act.toggled.connect(self.show_plot_window_gps)

        viewmenu.addAction(self.plot_act)
        viewmenu.addAction(self.plot_gps_act)


        self.minimap_action = QAction("General View", self)
        self.minimap_action.setCheckable(True)
        self.minimap_action.setChecked(True)
        self.minimap_action.toggled.connect(
            self.minimap_dock_widget.setVisible)
        self.minimap_dock_widget.visibilityChanged.connect(
            self.minimap_action.setChecked)
        viewmenu.addAction(self.minimap_action)
        self.colormap_action = QAction("Colormap", self)
        self.colormap_action.setCheckable(True)
        self.colormap_action.setChecked(True)
        self.colormap_action.toggled.connect(
            self.palette_dock_widget.setVisible)
        self.palette_dock_widget.visibilityChanged.connect(
            self.colormap_action.setChecked)

        viewmenu.addAction(self.colormap_action)

        hmenu = menubar.addMenu('Help')
        help_action = QAction("Documentation", self)
        help_action.triggered.connect(openUrl)
        help_action.setShortcut('Ctrl+Shift+H')
        hmenu.addAction(help_action)

        # loading directly if file specified upon app launch:
        self.current_filename = filename
        logger.debug(f"current_filename = {self.current_filename}")
        if self.current_filename is not None:
            self.load_data(self.current_filename)

        # show main window and minimap, focus on mainwindow
        self.show()
        self.resize(900, 700)
        self.activateWindow()

    def load_data(self, filename):
        """
        Load data from file filename.

        Parameters
        ----------
        filename : str
            name of the file to be loaded.

        Returns
        -------
        None.

        """
        print("MainWindow --> load data")
        logger.info(f"GUI: loading {self.current_filename}")
        # launch loader and update models
        self.map_model.loader.open(filename=filename)
        self.map_model.loader.get_metadata(filename=filename)
        self.plot_model.on_data_loaded()
        # set date slider's range to data's and current date to middle of data
        self.slider.setMaximum(len(self.map_model.loader)-1)
        # print("    ---> set sliders Maximum = ",(len(self.map_model.loader)))
        # self.slider.setMaximum(len(self.map_model.loader))
        self.slider.setValue(len(self.map_model.loader)//2) # original
        # print("    ---> set sliders value = ",len(self.map_model.loader))
        # self.slider.setValue(len(self.map_model.loader)) # original
        #self.slider.setValue(10) 
        # should launch display_date here under that will launch map_model.show_band --> which load band in loader.py
        # But it is not with envi because no change detected slider...
        self.band_setter.setRange(0, len(self.map_model.loader)-1)
        # enable plot button in menu:
        self.plot_act.setEnabled(True)
        

        print("MainWindow --> load data - finished")



    def load_gps_data(self, foldername):
        """
        Load gps data from file filename.

        Parameters
        ----------
        filename : Deformation tiff filename
        foldername: Folder name containing gps data

        Returns
        -------
        None.

        """
        nMaxPoints = 30

        # if self.filename:
        #     loader = Loader(self.filename)
        # else:
        #     loader = Loader(self.stack_file)

        print("MainWindow --> load_gps_data")


        metadata = self.map_model.loader.dataset.profile
        loader_gps = Loader_gps(foldername, metadata)


   
        # Create object
        self.plot_model_gps = PlotModel_gps(self.map_model.loader, loader_gps, nMaxPoints)


        # Set object "MapView" to self.plot_model_gps in order to refresh screen ans gps station status when selected station change
        self.plot_model_gps.map_widget = self.map_widget
        # Set object self.plot_model_gps to MapView in order to get access to gps data (coordinate and selection) to disply on map 
        self.map_widget.plot_model_gps = self.plot_model_gps
        # Load data into object
        self.plot_model_gps.on_data_loaded()

        self.plot_gps_act.setEnabled(True)

        # Write the gps data in MapVieW object in order to draw station on mam
        for station in loader_gps.gps_data.keys():
            self.plot_model_gps.station_gps_data[station] = {}
            self.plot_model_gps.station_gps_data[station]['x'] = loader_gps.gps_data[station]['ref_east_ras']
            self.plot_model_gps.station_gps_data[station]['y'] = loader_gps.gps_data[station]['ref_north_ras']


        # self.map_model.show_gps_station(loader_gps)
        print("MainWindow --> load_gps_data --> finished")


    def display_date(self):
        """
        display the current band's date (if available)
        """
        print("MainWindow --> display_date")
        date_number = self.slider.value()
        self.plot_model.date_number = date_number
        self.plot_model.current_date = self.plot_model.timestamps[date_number]

        self.map_model.show_band(i=date_number)

        if isinstance(self.plot_model.dates[date_number], int):
            self.date_label.setText(
                'Band #')

        # update spatial plot
        else:
            self.date_label.setText(
                f"{self.plot_model.dates[date_number].date()} - Band #")
        self.band_setter.setValue(date_number)

        try:
            self.plotw_s.plot_widget.setStyle(self.plotw_s.plot_widget.style)
        except AttributeError:
            pass


        print("MainWindow --> display_date --> finished")

    @pyqtSlot(tuple)
    def update_cursor_info(self, coord):
        print("MainWindow -- update_cursor_info")
        """
        update point information (x, y, value) in Informations widget as
        cursor hovers over Map

        Parameters
        ----------
        coord : tuple
            data coordinates of the point currently hovered over.

        Returns
        -------
        None.

        """
        i, j = coord
        self.info_widget.setText(
            f"x:{i}, y:{j}, val:{self.plot_model.thispoint_thisdate_disp:.6f}") # original 3f

    def KeyPressEvent(self, e):
        print("MainWindow -- KeyPressEvent")
        """
        handle keypressevent, right and left arrow keys change band

        Parameters
        ----------
        e : event
            right- or left-arrow key press event

        Returns
        -------
        None.

        """
        nb_dates = len(self.dates)

        if e.key() == Qt.Key_Right:
            self.slider.setValue(min(self.slider.value() + 1, nb_dates))
        if e.key() == Qt.Key_Left:
            self.slider.setValue(max(self.slider.value() - 1, 0))

    def show_plot_window(self, checked):
        print("MainWindow  -- show_plot_window")
        """
        Show plot window when Profile submenu in Main Window is checked,
        hide it if submenu unchecked.

        Parameters
        ----------
        checked : bool
            boolean describing whether the Profile button is checked

        Returns
        -------
        None.

        """

        if checked:
            if self.plotw_t is None:
                # create plot window:
                self.dockplotw_t = QDockWidget('Temporal plot', self)
                self.dockplotw_t.setAllowedAreas(Qt.RightDockWidgetArea)
                self.dockplotw_s = QDockWidget('Spatial plot', self)
                self.dockplotw_s.setAllowedAreas(Qt.RightDockWidgetArea)
                self.plotw_t = myPlotWindow(plottype='temporal',
                                            plot_model=self.plot_model)
                self.map_widget.sig_map2plotw.connect(
                    self.plotw_t.plot_widget.plotLoadedData)
                self.plotw_s = myPlotWindow(plottype='spatial',
                                            plot_model=self.plot_model)
                self.map_widget.sig_map2plotw.connect(
                    self.plotw_s.plot_widget.plotLoadedData)

                self.dockplotw_t.setWidget(self.plotw_t)
                self.dockplotw_s.setWidget(self.plotw_s)
                self.addDockWidget(Qt.RightDockWidgetArea, self.dockplotw_t)
                self.addDockWidget(Qt.RightDockWidgetArea, self.dockplotw_s)
                self.splitDockWidget(self.palette_dock_widget,
                                     self.dockplotw_t,
                                     Qt.Horizontal)
                self.splitDockWidget(self.dockplotw_t,
                                     self.dockplotw_s,
                                     Qt.Vertical)
                self.prof_action.toggled.connect(
                    self.plotw_t.ref_tick.setCheckable)
                self.points_action.toggled.connect(
                    self.plotw_t.ref_tick.setCheckable)

            self.dockplotw_t.show()
            self.dockplotw_s.show()
            self.plot_model.plot_interaction = 1
            self.plotting_toolbar.show()

            # connect to slider:
            self.slider.valueChanged.connect(
                self.plotw_t.plot_widget.date_marker.on_slider_changed)
            self.plotw_t.plot_widget.date_marker.sigposChanged.connect(
                self.slider.setValue)
        else:
            self.dockplotw_t.hide()
            self.dockplotw_s.hide()
            self.plot_model.plot_interaction = 0
            self.plotting_toolbar.hide()

        print("MainWindow  -- show_plot_window -- finished")



    def show_plot_window_gps(self, checked):


        """
        Show comparison between GPS data and deformation

        Parameters
        ----------
        checked : bool
            boolean describing whether the Profile button is checked

        Returns
        -------
        None.

        """

        print("MainWindow  -- show_plot_window_gps")


        if checked:
            if self.plotw_t_gps is None:
                # create plot window:
                self.dockplotw_t_gps = QDockWidget('Temporal plot', self)
                self.dockplotw_t_gps.setAllowedAreas(Qt.RightDockWidgetArea)

                self.plotw_t_gps = myPlotWindow_gps(plottype='temporal',
                                            plot_model=self.plot_model_gps)


                self.plotw_t_gps.plot_widget.plotLoadedData()

                self.map_widget.sig_map2plotw.connect(
                    self.plotw_t_gps.plot_widget.plotLoadedData)




                self.dockplotw_t_gps.setWidget(self.plotw_t_gps)

                self.addDockWidget(Qt.RightDockWidgetArea, self.dockplotw_t_gps)

                self.splitDockWidget(self.palette_dock_widget,
                                     self.dockplotw_t_gps,
                                     Qt.Horizontal)

                # self.prof_action.toggled.connect(
                    # self.plotw_t.ref_tick.setCheckable)
                # self.points_action.toggled.connect(
                    # self.plotw_t.ref_tick.setCheckable)

            self.dockplotw_t_gps.show()

            # self.plot_model.plot_interaction = 1
            # self.plotting_toolbar.show()

            # connect to slider:
            self.slider.valueChanged.connect(
                self.plotw_t_gps.plot_widget.date_marker.on_slider_changed)
            self.plotw_t_gps.plot_widget.date_marker.sigposChanged.connect(
                self.slider.setValue)
        else:
            self.dockplotw_t_gps.hide()
            self.plot_model.plot_interaction = 0
            self.plotting_toolbar.hide()

        print("MainWindow  -- show_plot_window_gps -- finished")

    def on_button_clicked_quit(self):


        """
        Quit application when 'Quit' is clicked in menu

        Returns
        -------
        None.

        """
        print("MainWindow  -- on_button_clicked_quit")

        hdr_file = re.sub('.tif', '.hdr', self.stack_file)
        xml_file = re.sub('(.tif)', r'\1.aux.xml', self.stack_file)
        files_to_delete = [self.stack_file, hdr_file, xml_file]
        for file in files_to_delete:
            if (os.path.exists(file)) and not self.keep_stack:
                os.remove(file)
                print("delete stack.tif file")
        print('\n *** Thank you for using InsarViz, see you soon! ***'
              '\n')
        QApplication.quit()

    # add this function by maxime
    def on_button_clicked_openFolder(self):

        """
       Open dialog window to select folder containing envi file

        Returns
        -------
        None.

        """

        print("MainWindow  -- on_button_clicked_openFolder")
        self.current_folder = str(QFileDialog.getExistingDirectory(self,
                                                                "Select file"))

        if self.current_folder:
            self.load_data(self.current_folder)
        else:
            print('no folder selected')

        print("MainWindow  -- on_button_clicked_openFolder -- finished")

    # add this function by maxime
    def on_button_clicked_openGpsFolder(self):

        """
        Open dialog window to select folder containing gps file

        Returns
        -------
        None.

        """
        print("MainWindow  -- on_button_clicked_openGpsFolder")
        self.current_gps_folder = str(QFileDialog.getExistingDirectory(self,
                                                                "Select file"))

        if self.current_gps_folder:
            self.load_gps_data(self.current_gps_folder)
        else:
            print('no gps folder selected')

        print("MainWindow  -- on_button_clicked_openGpsFolder --finished")

    def on_button_clicked_open(self):

        """
        Open dialog window to select file to be loaded

        Returns
        -------
        None.

        """

        print("MainWindow -- on_button_clicked_open")
        self.current_filename, _ = QFileDialog.getOpenFileName(self,
                                                               "Select file")
        

        if self.current_filename:
            self.load_data(self.current_filename)
        else:
            print('no file selected')


        print("MainWindow -- on_button_clicked_open -- finished")

    def on_button_clicked_clear_plot(self):

        """
        Clear plots and profile line on main window's map when 'Clear profiles
        button is clicked.

        Returns
        -------
        None.

        """

        print("MainWindow-- on_button_clicked_clear_plot")
        self.plot_model.plot_interaction = 1
        self.plot_model.clear_data()
        # clear profile line on Map
        self.map_model.selection = np.zeros(
            (self.map_model.tex_height, self.map_model.tex_width, 2),
            dtype='float32')
        self.map_model.update_selection()
        self.map_model.show_band(self.map_model.i)

        self.map_model.profile_points = []
        self.map_model.ref_pointers = None

        # clear plots
        self.plotw_t.on_button_clicked_clearplot()
        self.plotw_s.on_button_clicked_clearplot()
        self.show_plot_window(True)

        self.inter_action.setChecked(True)
        print("MainWindow-- on_button_clicked_clear_plot -- finished")

    # add by maxime to delete stack.tiff if needed after closing the app
    def closeEvent(self, * args, ** kwargs):
        print("MainWindow -- closeEvent ")
        super(QMainWindow, self).closeEvent( * args, ** kwargs)
        hdr_file = re.sub('.tif', '.hdr', self.stack_file)
        xml_file = re.sub('(.tif)', r'\1.aux.xml', self.stack_file)
        files_to_delete = [self.stack_file, hdr_file, xml_file]
        for file in files_to_delete:
            if (os.path.exists(file)) and not self.keep_stack:
                os.remove(file)
                print("delete stack.tif file")
        print("MainWindow -- closeEvent-- finished")


def main():
    print("ts_viz -- Main")
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    import argparse
    parser = argparse.ArgumentParser(
        description="insar timeseries visualisation")
    parser.add_argument("-v", type=int, default=3,
                        help=("set logging level:"
                              "0 critical, 1 error, 2 warning,"
                              "3 info, 4 debug, default=info"))
    parser.add_argument("-i",
                        type=str,
                        default=None,
                        help="input filename")
    parser.add_argument("-p",
                        type=str,
                        default=None,
                        help="directory that contains user defined plugins")
    parser.add_argument("-k", "--keep",
                        type=str,
                        help="Keep tiff file")
#     parser.add_argument("-c", type=str, default=None,
#                     help="config directory. default $HOME/.config/insarviz")
    args = parser.parse_args()

    logging_translate = [logging.CRITICAL,
                         logging.ERROR,
                         logging.WARNING,
                         logging.INFO,
                         logging.DEBUG]
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging_translate[args.v])
    logger = logging.getLogger(__name__)
    app = QApplication([])

    logger.info(f"loading {args.i}")
    # config = read_config(args.c)
    config = None
    if args.p:
        config = {"plugin_directory": args.p}
        logger.info(f"adding {args.p} as plugin_directory")

    # print("args = ",args)
    if args.keep:
        stack_file = args.keep
    else:
        stack_file = False

    # print("config = ",config)

    ex = MainWindow(filename=args.i,
                    config_dict=config,
                    stack_file=stack_file)
    app.exec_()


if __name__ == '__main__':
    main()
