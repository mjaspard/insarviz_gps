#!/usr/bin/env python3

from PyQt5.QtCore import (
    QObject, pyqtSlot,
    )

import numpy as np
import datetime

from insarviz.Interaction import IDLE, DRAG, ZOOM, POINTS, LIVE, PROFILE


class PlotModel(QObject):

    def __init__(self, loader, nMaxPoints):
        """
        Model for plots
        get and transform date/band values (timestamps, datetime or int)
        get and prepare data for plots
        (temporal plot = time/band vs displacement;
         spatial plot = distance along trace vs displacement)

        Parameters
        ----------
        loader : QObject
            Loader used to extract the dataset from a file

        Returns
        -------
        None.

        """
        print("PlotModel -- create object")
        super().__init__()

        self.loader = loader

        # variables
        self.disp = None
        self.nMaxPoints = nMaxPoints  # 30 max number of points on profile

        # updated by MouseMoveEvent on Map
        self.pointer_ij = None
        self.current_date = None
        self.date_number = None
        self.all_pointer_ij = None  # record

        # data for graphs:
        self.data_for_temporal_graph = []
        self.data_for_spatial_graph = []
        self.cumdistances = []
        self.timestamps = []

        # interaction state of map for plots:
        self.plot_istate = IDLE

        self.ref_curve_id = None
        self.ref_is_checked = False

        self.ref_pointers = None
        self.ready_for_REF = False
        self.ready_for_PROFILE = False
        self.ready_for_POINTS = False

        self.pts_on_trace = 0



        print("PlotModel - create object -- finished")

    def on_data_loaded(self):
        """
        called by MainWindow when loading new data
        format date/band values from loaded dataset


        Returns
        -------
        None.

        """
        print("PlotModel. -- on_data_load")
        if isinstance(self.loader._dates(), range):
            # print("test max is isinstance:" + " - " + str(self.loader._dates()))
            self.timestamps = range(len(self.loader._dates()))
            self.dates = self.timestamps
        else:
            # print("test max is not isinstance:" + " - " + str(self.loader._dates()))
            self.timestamps = [
                datetime.datetime.strptime(x, "%Y%m%d").timestamp()
                for x in self.loader._dates()]
            self.dates = [
                datetime.datetime.strptime(x, "%Y%m%d")
                for x in self.loader._dates()]

        self.number_of_dates = self.loader.__len__()
        # print('# of dates = ', self.number_of_dates)
        # print("self.timestamps = ", self.timestamps)
        # print("self.dates = ", self.dates )
        # from metadata, if existing:
        try:
            self.units = self.loader.metadata['Value_unit']
        except (AttributeError, KeyError):
            self.units = 'Undefined units'
        # print('self.units  = ', self.units )
        print("PlotModel. -- on_data_load -- finished")





    @pyqtSlot(tuple)
    def update_pointer_values(self):
        """
        load current pointer data (for plots)
        launched by mouseMoveEvent and MousePressEvent on Map

        Returns
        -------
        None.

        """
        print("PlotModel. -- update_pointer_values")
        # load data for all dates at current pointer's position:
        self.thispoint_disp = self.loader.load_profile(
            self.pointer_ij[0],
            self.pointer_ij[1])

        # print(self.pointer_ij[0])
        # print(self.pointer_ij[1])
        # print(self.thispoint_disp)
        # to display on Map's tooltip:
        self.thispoint_thisdate_disp = self.thispoint_disp[self.date_number]
        print("PlotModel. -- update_pointer_values -- finished")

    def update_ref_values(self, ref_pointers):
        """
        update values to be used as ref for plotting data
        if one px selected, its data is the ref
        if more than one px selected (rectangle), mean of all px data is ref

        Parameters
        ----------
        ref_pointers : list
            list of tuple (i, j) coordinates of ref point(s).

        Returns
        -------
        None.

        """
        print("PlotModel. -- update_ref_values")
        if len(ref_pointers) == 1:
            self.ref_data = self.loader.load_profile(
                ref_pointers[0][0],
                ref_pointers[0][1])

        else:
            all_ref_data = np.empty((len(ref_pointers),
                                     self.number_of_dates))
            for i in range(len(ref_pointers)):
                all_ref_data[i] = self.loader.load_profile(
                    ref_pointers[i][0],
                    ref_pointers[i][1])
            self.ref_data = all_ref_data.mean(axis=0)
            print("PlotModel. -- update_ref_values -- finished")

    def update_values(self, profile_points=None):
        """
        update values for plots :
        if interactive tool selected:
            displacement corresponding to current pointer position;
        if points:
            all selected positions and corresponding data
            for temporal and spatial plots; if number of selected points
            exceedes limit, earliest selected positions are erased;
        if profile:
            if number of points between points selected as start and end of
            profile is under limit, all selected positions and corresponding
            data for temporal and spatial plots
            if is over the limit, downsample (random) within those

        Returns
        -------
        None.

        """
        print("PlotModel -- update_values")
        if self.plot_istate == POINTS:
            # print("PlotModel.py -- self.plot_istate == POINTS")
            if self.all_pointer_ij is None:
                # first point:
                # init various variables and fill them with first point's value
                self.all_pointer_ij = np.zeros((self.nMaxPoints, 2), dtype=int)
                self.all_pointer_ij[0] = self.pointer_ij
                self.distances = np.zeros(self.nMaxPoints)
                self.cumdistances = np.zeros(self.nMaxPoints)
                self.pts_on_trace = 1
                # init and fill data for graph
                self.data_for_temporal_graph = np.full(
                    (self.nMaxPoints, self.number_of_dates),
                    np.nan)
                self.data_for_temporal_graph[0] = np.array(self.thispoint_disp)
            else:
                # print("PlotModel.py -- self.all_pointer_ij is NOT None")
                # more than one point:
                # check if point already in all_pointer_ij list:
                if not (self.pointer_ij == self.all_pointer_ij).all(1).any():
                    # check if number of points exceedes limit
                    if self.pts_on_trace < self.nMaxPoints:
                        # fill data
                        i = self.pts_on_trace
                        self.all_pointer_ij[i] = self.pointer_ij
                        # calculate distance with previous point
                        dist = np.array(
                            [np.sqrt(
                                np.power(
                                    (self.all_pointer_ij[i, 0] -
                                     self.all_pointer_ij[i-1, 0]),
                                    2)
                                + (np.power(
                                    (self.all_pointer_ij[i, 1] -
                                     self.all_pointer_ij[i-1, 1]),
                                    2)))])
                        self.distances[i] = dist

                        self.data_for_temporal_graph[i, :] = np.array(
                            self.thispoint_disp)
                        # self.pts_on_trace += 1
                    else:
                        # nMaxPoints reached, shift data to left and
                        # fill last slot
                        self.all_pointer_ij = (
                            np.concatenate((self.all_pointer_ij,
                                            np.array(self.pointer_ij).reshape(
                                                (1, 2)))))
                        dist = np.array(
                            [np.sqrt(

                                    (self.all_pointer_ij[-1, 0] -
                                     self.all_pointer_ij[-2, 0])**2

                                + (self.all_pointer_ij[-1, 1] -
                                    self.all_pointer_ij[-2, 1])**2)])
                        self.distances = np.concatenate((self.distances,
                                                         dist))[1:]
                        self.distances[0] = 0.
                        self.data_for_temporal_graph[0:-1, :] = (
                            self.data_for_temporal_graph[1:, :])
                        self.data_for_temporal_graph[-1, :] = (
                            self.thispoint_disp)

                    self.cumdistances = np.cumsum(self.distances)
                    self.pts_on_trace += 1

            self.data_for_spatial_graph = \
                self.data_for_temporal_graph.transpose()

        elif self.plot_istate == PROFILE:
            # print("PlotModel.py -- self.plot_istate == PROFILE")
            if len(profile_points) == 1:
                # first point
                self.all_pointer_ij = np.zeros((self.nMaxPoints, 2), dtype=int)
                self.all_pointer_ij[0] = self.pointer_ij
                self.distances = np.zeros(self.nMaxPoints)
                self.cumdistances = np.zeros(self.nMaxPoints)
                self.pts_on_trace = 1

                self.data_for_temporal_graph = np.full(
                    (self.nMaxPoints, self.number_of_dates),
                    np.nan)
                self.data_for_temporal_graph[0] = np.array(self.thispoint_disp)
            else:
                # more than one point
                if len(profile_points) <= self.nMaxPoints:
                    # fill all_pointers with points from profile
                    self.all_pointer_ij[:len(profile_points)] = profile_points
                    self.pts_on_trace = len(profile_points)

                else:
                    # more than nMaxPoints, subsample profile line(s)
                    # sample the indices of all points along traced profile
                    # ind = np.random.choice(range(1,
                    #                              len(list(profile_points))-1),
                    #                        self.nMaxPoints-2,
                    #                        replace=False)
                    # self.all_pointer_ij[0] = profile_points[0]
                    # self.all_pointer_ij[-1] = profile_points[-1]
                    # self.all_pointer_ij[1:-1] = [
                    #     profile_points[i] for i in sorted(ind)]
                    self.pts_on_trace = self.nMaxPoints

                # load displacement for all points
                # put into data_for_temporal_graph
                self.data_for_temporal_graph = np.full(
                    (self.nMaxPoints, self.number_of_dates),
                    np.nan)
                for p in range(self.pts_on_trace):
                    self.data_for_temporal_graph[p] = np.array(
                        self.loader.load_profile(*self.all_pointer_ij[p]))

                # calculate distances, cumulative distances
                for p in range(1, self.pts_on_trace):
                    self.distances[p] = np.sqrt(
                        (self.all_pointer_ij[p, 0] -
                         self.all_pointer_ij[p-1, 0])**2
                        + (self.all_pointer_ij[p, 1] -
                           self.all_pointer_ij[p-1, 1])**2)
                self.cumdistances = np.cumsum(self.distances)

            # in all cases where Profile or Points tool is active
            # data for spatial graph is transpose of data for temporal graph
            self.data_for_spatial_graph = \
                self.data_for_temporal_graph.transpose()

        elif self.plot_istate == LIVE:
            print("PlotModel.py -- self.plot_istate == LIVE")
            if (not self.ready_for_REF and
                not self.ready_for_PROFILE and
                not self.ready_for_POINTS):
                # interactive drawing
                self.pts_on_trace = 1
                self.data_for_temporal_graph = self.thispoint_disp
                # self.data_for_spatial_graph = np.full((1), np.nan)

        print("PlotModel -- update_values -- finished")


    def clear_data(self):
        """
        clear data to reset plots
        called when clicking clear profile button

        Returns
        -------
        None.

        """
        print("PlotModel -- clear data")
        self.disp = None
        self.all_pointer_ij = None
        self.data_for_temporal_graph = []
        self.data_for_spatial_graph = []
        self.cumdistances = []
        self.ref_curve_id = None
        print("PlotModel -- clear data -- finished")

    def set_plot_interaction(self, val):
        print("PlotModel -- set_plot_interaction")
        self.plot_istate = val
        assert self.plot_istate in [0, 3, 4, 5], \
            'plot interaction: wrong value'

    @pyqtSlot(bool)
    def set_ready_for_POINTS(self, checked):
        print("PlotModel -- set_ready_for_POINTS")
        self.ready_for_POINTS = checked

    @pyqtSlot(bool)
    def set_ready_for_PROFILE(self, checked):
        print("PlotModel -- set_ready_for_PROFILE")
        self.ready_for_PROFILE = checked

    @pyqtSlot(bool)
    def set_ready_for_REF(self, checked):
        print("PlotModel -- set_ready_for_REF")
        self.ready_for_REF = checked



########################################################################################################
########################################################################################################
########################################################################################################


class PlotModel_gps(QObject):

    def __init__(self, loader, loader_gps, nMaxPoints):
        """
        Model for plots
        get and transform date/band values (timestamps, datetime or int)
        get and prepare data for plots
        (temporal plot = time/band vs displacement;
         spatial plot = distance along trace vs displacement)

        Parameters
        ----------
        loader : QObject
            Loader used to extract the dataset from a file

        Returns
        -------
        None.

        """
        print("PlotModel_gps -- Creation object")
        super().__init__()

        self.loader = loader
        self.loader_gps = loader_gps

        # variables
        self.disp = None
        self.nMaxPoints = nMaxPoints  # 30 max number of points on profile

        # updated by MouseMoveEvent on Map
        self.pointer_ij = None
        self.current_date = None
        self.date_number = None
        self.all_pointer_ij = None  # record

        # data for graphs:
        self.data_for_temporal_graph = []
        self.data_gps_for_temporal_graph = []
        self.cumdistances = []
        self.timestamps = []
        self.timestamps_gps = []


        # interaction state of map for plots:
        self.plot_istate = IDLE

        self.ref_curve_id = None
        self.ref_is_checked = False

        self.ref_pointers = None
        self.ready_for_REF = False
        self.ready_for_PROFILE = False
        self.ready_for_POINTS = False

        self.pts_on_trace = 0

        self.station_gps = []
        self.station_gps_data = {}
        self.menu_orientation = 'up'

        print("PlotModel_GPS. -- object creation --finisehd")


    def on_data_loaded(self):
        """
        called by MainWindow when loading new data
        format date/band values from loaded dataset


        Returns
        -------
        None.

        """
        print("PlotModel_GPS. -- on_data_loaded")
        if isinstance(self.loader._dates(), range):
            # print("test max is isinstance:" + " - " + str(self.loader._dates()))
            self.timestamps = range(len(self.loader._dates()))
            self.dates = self.timestamps
        else:
            # print("test max is not isinstance:" + " - " + str(self.loader._dates()))
            self.timestamps = [
                datetime.datetime.strptime(x, "%Y%m%d").timestamp()
                for x in self.loader._dates()]
            self.dates = [
                datetime.datetime.strptime(x, "%Y%m%d")
                for x in self.loader._dates()]

        self.number_of_dates = self.loader.__len__()
        # print('# of dates = ', self.number_of_dates)
        # print("self.timestamps = ", self.timestamps)
        # print("self.dates = ", self.dates )
        # from metadata, if existing:
        try:
            self.units = self.loader.metadata['Value_unit']
        except (AttributeError, KeyError):
            self.units = 'Undefined units'
        # print('self.units  = ', self.units )

        # print(self.loader_gps.gps_data.keys())
        self.station_gps = self.loader_gps.gps_data.keys()

        self.current_station = list(self.loader_gps.gps_data.keys())[0]
        # print("PlotModel_GPS. -- on_data_load  -- station = ", self.current_station)
        self.current_x = self.loader_gps.gps_data[self.current_station]['ref_east_ras']
        self.current_y = self.loader_gps.gps_data[self.current_station]['ref_north_ras']


        # print("PlotModel_GPS. -- on_data_load  -- x = {} : y = {}".format(self.current_x, self.current_y))
        # print(self.current_x)
        # print(self.current_y)
        self.update_pointer_values()
        print("PlotModel_GPS. -- on_data_load -- finished")

    def on_data_reloaded(self, station, orientation):
        """
        called by MainWindow when loading new data
        format date/band values from loaded dataset


        Returns
        -------
        None.

        """
        print("PlotModel_GPS. -- on_data_reload")

        # Update selected station and selected orientation for gps data
        self.current_station = station
        self.menu_orientation = orientation


        # print("PlotModel_GPS. -- on_data_reload  -- station = ", self.current_station)
        self.current_x = self.loader_gps.gps_data[self.current_station]['ref_east_ras']
        self.current_y = self.loader_gps.gps_data[self.current_station]['ref_north_ras']

        # print("PlotModel_GPS. -- on_data_reload  -- x = {} : y = {}".format(self.current_x, self.current_y))
        # print(self.current_x)
        # print(self.current_y)

        # Refresh map to display in red the selected station
        self.map_widget.paintGL()


        self.update_pointer_values()
        print("PlotModel_GPS. -- on_data_reload -- finished")


    # @pyqtSlot(tuple)
    def update_pointer_values(self):
        """
        load current pointer data (for plots)
        launched by mouseMoveEvent and MousePressEvent on Map

        Returns
        -------
        None.

        """
        print("PlotModel_GPS. -- update_pointer_values")
        # load data for all dates at current pointer's position:
        self.thispoint_disp = self.loader.load_profile(
            self.current_x,
            self.current_y)


        self.thispoint_gps_date, self.thispoint_gps_east, self.thispoint_gps_north, self.thispoint_gps_up = self.loader_gps.load_profile(self.current_station)


        # print("gps_date = ",self.thispoint_gps_date)
        # print("gps_east = ",self.thispoint_gps_east)

        # print(self.thispoint_disp)
        # print(self.thispoint_gps_east)

        # to display on Map's tooltip:
        self.thispoint_thisdate_disp = self.thispoint_disp[self.date_number]

        self.update_values()
        print("PlotModel_GPS. -- update_pointer_values -- finished")


    def update_ref_values(self, ref_pointers):
        """
        update values to be used as ref for plotting data
        if one px selected, its data is the ref
        if more than one px selected (rectangle), mean of all px data is ref

        Parameters
        ----------
        ref_pointers : list
            list of tuple (i, j) coordinates of ref point(s).

        Returns
        -------
        None.

        """
        print("PlotModel_GPS. -- update_ref_values")

        if len(ref_pointers) == 1:
            self.ref_data = self.loader.load_profile(
                ref_pointers[0][0],
                ref_pointers[0][1])

        else:
            all_ref_data = np.empty((len(ref_pointers),
                                     self.number_of_dates))
            for i in range(len(ref_pointers)):
                all_ref_data[i] = self.loader.load_profile(
                    ref_pointers[i][0],
                    ref_pointers[i][1])
            self.ref_data = all_ref_data.mean(axis=0)
        print("PlotModel_GPS. -- update_ref_values -- finished")

    def update_values(self, profile_points=None):
        """


        Returns
        -------
        None.

        """
        print("PlotModel_GPS. -- update_values")

     
        self.pts_on_trace = 1
        self.data_for_temporal_graph = self.thispoint_disp
        # print(self.data_for_temporal_graph)

        if self.menu_orientation == "east":
            self.data_gps_for_temporal_graph = self.thispoint_gps_east
        elif self.menu_orientation == "north":
            self.data_gps_for_temporal_graph = self.thispoint_gps_north
        elif self.menu_orientation == "up":
            self.data_gps_for_temporal_graph = self.thispoint_gps_up    
        # self.data_gps_for_temporal_graph = self.thispoint_gps_up
        # self.data_for_spatial_graph = np.full((1), np.nan)


        print("PlotModel_GPS. -- update_values -- finished")

    def clear_data(self):
        """
        clear data to reset plots
        called when clicking clear profile button

        Returns
        -------
        None.

        """
        print("PlotModel_GPS. -- clear data")
        self.disp = None
        self.all_pointer_ij = None
        self.data_for_temporal_graph = []
        self.data_for_spatial_graph = []
        self.cumdistances = []
        self.ref_curve_id = None

    def set_plot_interaction(self, val):
        print("PlotModel_GPS. -- set_plot_interaction")
        self.plot_istate = val
        assert self.plot_istate in [0, 3, 4, 5], \
            'plot interaction: wrong value'

    @pyqtSlot(bool)
    def set_ready_for_POINTS(self, checked):
        print("PlotModel_GPS. -- set_ready_for_POINTS")
        self.ready_for_POINTS = checked

    @pyqtSlot(bool)
    def set_ready_for_PROFILE(self, checked):
        print("PlotModel_GPS. -- set_ready_for_PROFILE")
        self.ready_for_PROFILE = checked

    @pyqtSlot(bool)
    def set_ready_for_REF(self, checked):
        print("PlotModel_GPS. -- set_ready_for_REF")
        self.ready_for_REF = checked
