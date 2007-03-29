#!/usr/bin/env python

import os, sys

import gdal

if __name__=='__main__':
    args = sys.argv[1:]
    if len(args)==0:
        args=['cubes/minicube.bil']

    for name in args:
        print "trying %s" % name
        dataset = gdal.Open(name, gdal.GA_ReadOnly)
        if dataset is not None:
            print "opened %s" % name
            dtype = dataset.GetRasterBand(1).DataType
            bytes = dataset.ReadRaster(1,1,1,1,buf_type=dtype)
        else:
            print "couldn't open %s" % name

    print "exiting"
    
