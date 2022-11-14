# -*- coding: utf-8 -*-
"""
unit tests for insarviz io
"""

import logging
import unittest
from pathlib import Path

import insarviz.Loader as ts_loader


logger = logging.getLogger(__name__)

class TestTSIO(unittest.TestCase):

    """Test the import of new data"""

    def test_load_flatsim(self):
        "Test the loading of geotiff ts data cube as produced by flatsim "
        curr_dir = Path(__file__).resolve().parent
        small_tiff = curr_dir / "data" / "GDM_DTs_geo_20190517_20190926_8rlks_crop_cmp.tiff"
        logger.debug(f"test_load_nsbas on file {small_tiff}")
        loader = ts_loader.Loader()
        loader.open(small_tiff)
        data = loader.dataset
        logger.debug(f"load flatsim: shape found: {data.shape}")
        self.assertEqual(data.shape[0], 600)
        self.assertEqual(data.shape[1], 600)
        self.assertEqual(data.count, 17)
        self.assertEqual(data.driver, 'GTiff')
        self.assertEqual(data.nodata, 0.0)
        self.assertEqual(data.transform[0], 0.001111112)

        # test loader.dataset.profile

    def test_load_nsbas(self):
        "Test the loading of ts data cube as produced by nsbas "
        curr_dir = Path(__file__).resolve().parent
        small_nsbas = curr_dir / "data" / "data_cube_ridgecrest_crop/depl_cumule"
        logger.debug(f"test_load_nsbas on file {small_nsbas}")
        loader = ts_loader.Loader()
        loader.open(small_nsbas)
        data = loader.dataset
        logger.debug(f"load flatsim: shape found: {data.shape}")
        self.assertEqual(data.shape[0], 700)
        self.assertEqual(data.shape[1], 800)
        self.assertEqual(data.count, 17)
        self.assertEqual(data.driver, 'ENVI')
        self.assertEqual(data.nodata, 9999.0)
        self.assertEqual(data.descriptions[0], '20190517')
