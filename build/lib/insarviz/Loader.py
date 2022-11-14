#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import time

import numpy as np

import rasterio
from rasterio.enums import Resampling

from PyQt5.QtCore import (
    QObject, pyqtSignal
    )


# data ######################################################################

class Loader(QObject):
    profile_changed = pyqtSignal(object)

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
        self.dataset = rasterio.open(filename)
        print("opened", self.dataset)
        profile = self.dataset.profile
        for attr in profile:
            print(attr, profile[attr])
        self.profile_changed.emit((filename, profile))

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
        if None in self.dataset.descriptions:
            # dates are not available (no metadata/aux file):
            _d = range(self.__len__())
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
        dataset = self.dataset
        index = dataset.indexes[i]
        t0 = time.time()
        band = dataset.read(index,
                            out_shape=(dataset.height//1, dataset.width//1),
                            resampling=Resampling.nearest)
        t1 = time.time()
        print('loaded band', i, 'in', t1-t0, 's')

        # geotiff opens with GTiff rasterio driver, must be flipped ud:
        if dataset.profile["driver"] == 'GTiff':
            band = np.flipud(band)

        return band, dataset.profile.get('nodata', None), dataset.dtypes[i]

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
        try:
            dataset = self.dataset
        except AttributeError:
            return []
        i, j = int(i), int(j)

        # geotiff opens with GTiff rasterio driver, is flipped ud
        if dataset.profile["driver"] == 'GTiff':
            j = dataset.shape[0] - (j+1)

        data = dataset.read(dataset.indexes,
                            window=(
                                (j, j+1), (i, i+1))).reshape((self.__len__()))
        
        # set nodata to nan
        nd = dataset.profile['nodata']
        data[data == nd] = np.nan

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
        metafilename = filename.split('.')[0] + '.meta'
        self.metadata = {}
        try:
            with open(metafilename) as f:
                for line in f:
                    (key, val) = line.split(sep=': ', maxsplit=1)
                    self.metadata[key] = val.strip()
        except FileNotFoundError:
            print('no metadata file found')
