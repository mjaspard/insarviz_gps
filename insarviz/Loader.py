#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import time
import re
import numpy as np
import glob
import rasterio
from rasterio.enums import Resampling
from pyproj import Proj, transform
from affine import Affine

from PyQt5.QtCore import (
    QObject, pyqtSignal
    )


# data ######################################################################

class Loader(QObject):
    profile_changed = pyqtSignal(object)

    def __init__(self, stack_file):

        print("Loader -- create object")
        super().__init__()
        self.stack_file = stack_file
        print("Loader -- create object -- finished")
    def open(self, filename):
        """
        Open data file and store dataset.
        Print dataset attributes.

        Parameters
        ----------
        filename : str, path
            Name of the file to load (with path).

        Returns
        -------
        None.

        """
        print("Loader -- Open file")


        # Check if the open element is a directroy
        if os.path.isdir(filename): 
            target = "{}/*".format(filename)
            file_list = [x for x in glob.glob(target) if re.search(r"\d{8}T\d{6}.*bin$", x)]
            file_list.sort()
            # Read metadata of first file
            with rasterio.open(file_list[0]) as src0:
                meta = src0.meta

            # Update meta to reflect the number of layers
            meta.update(count = len(file_list))
            # Update meta to reflect the option 'nodata=0' that we use at line73
            meta.update(nodata = 0.0)

            # Read each layer and write it to stack
            with rasterio.open(self.stack_file, 'w', **meta) as dataset:
                for id, layer in enumerate(file_list, start=1):
                    with rasterio.open(layer) as src1:
                        dataset.write_band(id, src1.read(1))
                        date_str = re.search(r"\d{8}", src1.name)[0]
                        dataset.set_band_description(id, date_str)# Append a tupple
                        # print("add -- date: {} -- count = {}".format(date_str, id))
                # print("dataset descriptions = ",dataset.descriptions)


            self.dataset = rasterio.open(self.stack_file, nodata=0) # maxime add option to convert NaN
            # print("self dataset descriptions = ",self.dataset.descriptions)

        else:
            self.dataset = rasterio.open(filename, nodata=0)
        

        #continue
        # print("opened", self.dataset)
        profile = self.dataset.profile

        # for attr in profile:
        #     print(attr, profile[attr])
        # print("--> call profile_changed.emit(({}, {}))".format(filename, profile))
        self.profile_changed.emit((filename, profile))

        print("Loader -- Open file -- finished ")


    def __len__(self):
        """
        Length of dataset = number of bands/dates.

        Returns
        -------
        int
            number of band/dates.

        """
        return len(self.dataset.indexes)

    def _dates(self):
        """
        If dates are available in data file (or metadata in same location),
        get dates, otherwise make a list of band numbers.

        Returns
        -------
        _d : list
            -if dates are available in data file
            (or metadata in same location): list of dates
            - if not: range of band numbers

        """
        print("Loader -- _dates")
        if None in self.dataset.descriptions:
            # dates are not available (no metadata/aux file):
            _d = range(self.__len__())
            if self.dataset.profile["driver"] == 'ENVI':    # maxime : test load date 
                if re.search(r"\d{8}", self.dataset.name):
                    date_str = re.search(r"\d{8}", self.dataset.name)[0]
                    # print("Extract date = ", date_str)
                    _d = [date_str]
        else:
            _d = [d[-8:] for d in self.dataset.descriptions]

        return _d


    def load_band(self, i=0):
        """
        load band i from dataset
        print loading time

        Parameters
        ----------
        i : int, optional
            Band number to load. The default is 0.

        Returns
        -------
        band : array
            Loaded band data.
        TYPE
            nodata value in band i.
        TYPE
            type of data in band i.
        """  

        print("Loader -- load_band")
        dataset = self.dataset
        index = dataset.indexes[i]
        t0 = time.time()
        band = dataset.read(index,
                            out_shape=(dataset.height//1, dataset.width//1),
                            resampling=Resampling.nearest)
        t1 = time.time()
        # print('loaded band', i, 'in', t1-t0, 's')

        # geotiff opens with GTiff rasterio driver, must be flipped ud:
        if dataset.profile["driver"] == 'GTiff':
            band = np.flipud(band)
            return band, dataset.profile.get('nodata', None), dataset.dtypes[i]
 

        # add by maxime
        # geotiff opens with ENVI rasterio driver, must be flipped ud:
        if dataset.profile["driver"] == 'ENVI':
            band = np.flipud(band)
            return band, 0.0, dataset.dtypes[i] # maxime (dataset.profile.get('nodata', None) = nan with current dataset)


        


    def load_profile(self, i, j):
        """
        Load data corresponding to all bands/dates, at point (i,j)
        (texture/data coordinates)

        Parameters
        ----------
        i : float or int
            col number
        j : float or int
            row number

        Returns
        -------
        array
            dataset values at point (i,j) (in texture/data coordinates)
            for all bands/dates.

        """
        print("loader - load_profile, i = {} : j = {}".format(i, j))
        try:
            dataset = self.dataset
        except AttributeError:
            return []
        i, j = int(i), int(j)

        # geotiff opens with GTiff rasterio driver, is flipped ud
        if dataset.profile["driver"] == 'GTiff':
            j = dataset.shape[0] - (j+1)


        # geotiff opens with GTiff rasterio driver, is flipped ud (add by maxime)
        if dataset.profile["driver"] == 'ENVI':
            j = dataset.shape[0] - (j+1)


        data = dataset.read(dataset.indexes,
                            window=(
                                (j, j+1), (i, i+1))).reshape((self.__len__()))

        # set nodata to nan
        nd = dataset.profile['nodata']
        data[data == nd] = np.nan


        print("loader - load_profile -- finished")
        return data

    def get_metadata(self, filename):
        """
        creates a dictionnary containing all metadata entries,
        if a '.meta' file exists in same repo as the datacube file

        Parameters
        ----------
        filename : str
            name of the datacube file

        Returns
        -------
        None.

        """
        print("loader - get_metadata")
        metafilename = filename.split('.')[0] + '.meta'
        self.metadata = {}
        try:
            with open(metafilename) as f:
                for line in f:
                    (key, val) = line.split(sep=': ', maxsplit=1)
                    self.metadata[key] = val.strip()
        except FileNotFoundError:
            print('no metadatas file found')



###########################################################################################################################
###########################################################################################################################
###########################################################################################################################



class Loader_gps():




    def __init__(self, gps_folder, metadata):


        # Check if the open element is a directroy
        print("Loader_gps -- object creation")

        self.metadata = metadata
        # Read data from metadat
        self.crs = re.split(r":", str(self.metadata['crs']))[1]
        self.width = re.search(r"\d+", str(self.metadata['width']))[0]
        self.height = re.search(r"\d+", str(self.metadata['height']))[0]
        self.transf =  self.metadata['transform']




        #profile_changed = pyqtSignal(object)
        if os.path.isdir(gps_folder): 
            target = "{}/*".format(gps_folder)
            file_list = [x for x in glob.glob(target) if re.search(r".*\.txt$", x)]
            file_list.sort()

            # Create gps dictionary data
            self.gps_data = {}


            # Fill gps_data file by file
            for file in file_list:

                with open(file, 'r') as f:
                    # extract content of files
                    lines = f.readlines()
                    # extract station name
                    self.sta_name = re.split(r"\.", os.path.basename(file))[0]
                    # create subdirectory
                    self.gps_data[self.sta_name] = {}
                    # Fill subdirectory with staion name, vector time and value (x, y)
                    self.gps_data[self.sta_name]['date'] = self.get_gps_file_x_axis(lines)
                    self.gps_data[self.sta_name]['east'], self.gps_data[self.sta_name]['ref_east'] = self.get_gps_file_y_axis(lines, 6)
                    self.gps_data[self.sta_name]['north'], self.gps_data[self.sta_name]['ref_north']= self.get_gps_file_y_axis(lines, 7)
                    self.gps_data[self.sta_name]['up'], self.gps_data[self.sta_name]['ref_up'] = self.get_gps_file_y_axis(lines, 8)



                    # Convert GPS coordinate into same projection as deformation file
                    # inProj = Proj(init='epsg:3857')
                    # outProj = Proj(init=self.metadata['crs'])
                    # x1,y1 = self.ref_east,self.ref_north
                    # self.ref_east_pj, self.ref_north_pj = transform(inProj,outProj,x1,y1)

                    ref_east_pj, ref_north_pj = self.get_coord(lines)
                    # print("x = ({}/{})/{}".format(ref_east_pj, self.transf.c, self.transf.a))
                    # print("y = ({}/{})/{}".format(self.transf.f, ref_north_pj, self.transf.e))
                    if ref_east_pj != 0 and ref_north_pj != 0:
                        self.gps_data[self.sta_name]['ref_east_pj'] = ref_east_pj
                        self.gps_data[self.sta_name]['ref_north_pj'] = ref_north_pj
                        # Calculate mnaually position of station in the raster using transfrm data
                        self.gps_data[self.sta_name]['ref_east_ras'] = int((ref_east_pj - self.transf.c)/self.transf.a)
                        self.gps_data[self.sta_name]['ref_north_ras'] = int((self.transf.f - ref_north_pj)/abs(self.transf.e))
                        # The raster is inverted in insarviz for north orientation, the southest is 0 and northest the height value
                        self.gps_data[self.sta_name]['ref_north_ras'] = int(self.height) - self.gps_data[self.sta_name]['ref_north_ras']
                    else:                    
                        self.gps_data[self.sta_name]['ref_east_pj'] = 0
                        self.gps_data[self.sta_name]['ref_north_pj'] = 0
                        # Calculate mnaually position of station in the raster using transfrm data
                        self.gps_data[self.sta_name]['ref_east_ras'] = 0
                        self.gps_data[self.sta_name]['ref_north_ras'] = 0

                    # print("----------------------------------------------------------------")
                    # print("Data for {}:".format(self.sta_name))
                    # print(self.gps_data[self.sta_name])


        print("Loader_gps -- object creation -- finisehd")

    def get_gps_file_x_axis(self, lines):

        """ Function to extract time from gps file in 3 actios:
            1. extract date into an array the line containing informations
            2. convert date into time struct object
            3. convert date into float time from epoch
            """
        print("loader -- get_gps_file_x_axis")
        date_array = [re.search(r"\d{4}\s\d{2}\s\d{2}", x)[0] for x in lines if re.search(r"\d{4}\s\d{2}\s\d{2}", x)]
        date_array_py = [time.strptime(x, "%Y %m %d") for x in date_array]
        date_array_py = [time.mktime(x) for x in date_array_py]
        return date_array_py


    def get_gps_file_y_axis(self, lines, position):

        """ Function to extract specific data from gps file in 3 actios:
            1. extract East value from line containing informations
            2. Make vaule relative to the 1st one
            """
        print("loader -- get_gps_file_y_axis")
        orientation_array = [re.split(r"\s", x)[position] for x in lines if re.search(r"\d{4}\s\d{2}\s\d{2}", x)]
        orientation_array_rel = [(float(x) - float(orientation_array[0])) for x in orientation_array]
        # return orientation_array_rel, orientation_aray[0]
        return orientation_array_rel, orientation_array[0]

    def get_coord(self, lines):

        """ Function to extract specific data from gps file in 3 actios:
            1. extract coordinate from line containing informations
            2. Make vaule relative to the 1st one
            """
        print("loader -- get_coord")
        coord_x = 0
        coord_y = 0
        try:
            coord = [re.search(r"\d+.+\d+", x)[0] for x in lines if re.search(r"COORD", x)]
            # print(coord)
            # print(coord[0])

            coord_x = re.split(r"\s", str(coord[0]))[0]
            coord_y = re.split(r"\s", str(coord[0]))[1]
            # coord_x = int(re.search(r"\d*", coord_x)[0])
            # coord_y = int(re.search(r"\d*", coord_y)[0])
            # print(coord_x)
            # print(coord_y)
        except:
            print("Coordinate not found")
        return int(coord_x), int(coord_y)



    def load_profile(self, station):
        """
        Load data corresponding to all bands/dates, at point (i,j)
        (texture/data coordinates)

        Parameters
        ----------
        i : float or int
            col number
        j : float or int
            row number

        Returns
        -------
        array
            dataset values at point (i,j) (in texture/data coordinates)
            for all bands/dates.

        """
        print("loader_gps.py - load_profile, station = {}".format(station))

        data_date = self.gps_data[station]['date'] 
        data_north = self.gps_data[station]['north'] 
        data_east = self.gps_data[station]['east'] 
        data_up = self.gps_data[station]['up'] 


        return data_date, data_north, data_east, data_up

        print("loader_gps.py - load_profile -- finished")
























            