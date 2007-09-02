#!/usr/bin/env python

import os, sys
from utils import *

try:
    import gdal
    USE_GDAL = True
except:
    USE_GDAL = False

class TestGDAL:
    def setUp(self):
        self.path = localfile('data/test1.bil')

    def testLoad(self):
        if USE_GDAL:
            dataset = gdal.Open(self.path, gdal.GA_ReadOnly)
            dtype = dataset.GetRasterBand(1).DataType
            bytes = dataset.ReadRaster(1,1,1,1,buf_type=dtype)
