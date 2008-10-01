# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Hyperspectral image processing filters

This file is a repository of actions that operate on the HSI mode.
"""

import os, struct, mmap, math
from cStringIO import StringIO

import wx

from peppy.actions.minibuffer import *
from peppy.actions import *

from peppy.hsi.common import *
from peppy.hsi.filter import *


class ColormapAction(HSIActionMixin, RadioAction):
    """Color map from grayscale intensity to colors""" 
    name = "Color Map"
    default_menu = ("View", 601)

    items = ['None']
    items.extend(colors.getColormapNames())

    def getIndex(self):
        mode = self.mode
        filt = mode.colormapper
        #dprint(filt)
        if hasattr(filt, 'colormap_name'):
            val = filt.colormap_name
            return self.items.index(val)
        else:
            return 0

    def getItems(self):
        return self.__class__.items

    def action(self, index=-1, multiplier=1):
        assert self.dprint("index=%d" % index)
        mode = self.mode
        if index == 0:
            filt = RGBMapper()
        else:
            filt = PaletteMapper(self.items[index])
        mode.colormapper = filt
        mode.update()


class ContrastFilterAction(HSIActionMixin, RadioAction):
    name = "Contrast"
    tooltip = "Contrast adjustment method"
    default_menu = ("Filter", -300)

    items = ['No stretching', '1% Stretching', '2% Stretching', 'User-defined']

    def getIndex(self):
        mode = self.mode
        filt = mode.filter
        #dprint(filt)
        if hasattr(filt, 'contraststretch'):
            val = filt.contraststretch
            if val > 0.0001 and abs(val - 0.1) < 0.0001:
                return 1
            elif abs(val - 0.2) < 0.0001:
                return 2
            else:
                return 3
        else:
            return 0

    def getItems(self):
        return self.__class__.items

    def action(self, index=-1, multiplier=1):
        assert self.dprint("index=%d" % index)
        mode = self.mode
        if index == 0:
            filt = GeneralFilter(pos=0)
        elif index == 1:
            filt = ContrastFilter(0.1)
        elif index == 2:
            filt = ContrastFilter(0.2)
        else:
            self.setContrast(mode)
            return
        mode.filter = filt
        mode.update()

    def processMinibuffer(self, minibuffer, mode, percentage):
        assert self.dprint("returned percentage = %f" % percentage)
        filt = ContrastFilter(percentage)
        mode.filter = filt
        mode.update()
        
    def setContrast(self, mode):
        minibuffer = FloatMinibuffer(mode, self, label="Contrast [0.0 - 1.0]")
        mode.setMinibuffer(minibuffer)


class MedianFilterAction(HSIActionMixin, RadioAction):
    name = "Median Filter"
    tooltip = "Median filter"
    default_menu = ("Filter", 301)

    items = ['No median',
             'Median 3x1 pixel', 'Median 1x3 pixel', 'Median 3x3 pixel',
             'Median 5x1 pixel', 'Median 1x5 pixel', 'Median 5x5 pixel']

    def isEnabled(self):
        return bool(scipy_module())

    def getIndex(self):
        mode = self.mode
        filt = mode.filter
        assert self.dprint(filt)
        if isinstance(filt, MedianFilter1D):
            return filt.pos
        return 0

    def getItems(self):
        return self.__class__.items

    def action(self, index=-1, multiplier=1):
        assert self.dprint("index=%d" % index)
        mode = self.mode
        if index == 0:
            filt = GeneralFilter(pos=0)
        elif index == 1:
            filt = MedianFilter1D(3, 1, pos=index)
        elif index == 2:
            filt = MedianFilter1D(1, 3, pos=index)
        elif index == 3:
            filt = MedianFilter1D(3, 3, pos=index)
        elif index == 4:
            filt = MedianFilter1D(5, 1, pos=index)
        elif index == 5:
            filt = MedianFilter1D(1, 5, pos=index)
        elif index == 6:
            filt = MedianFilter1D(5, 5, pos=index)
        mode.filter = filt
        mode.update()


class GaussianFilterAction(HSIActionMixin, RadioAction):
    """2D Gaussian blur filter
    
    """
    name = "Gaussian"
    default_menu = ("Filter", 305)

    items = ['No filter', '5 Pixel Kernel', '10 Pixel Kernel', 'User-defined']

    def getIndex(self):
        mode = self.mode
        filt = mode.filter
        assert self.dprint(filt)
        if isinstance(filt, GaussianFilter):
            return filt.pos
        return 0

    def getItems(self):
        return self.__class__.items

    def action(self, index=-1, multiplier=1):
        assert self.dprint("index=%d" % index)
        mode = self.mode
        filt = None
        if index == 0:
            filt = GeneralFilter(pos=0)
        elif index == 1:
            filt = GaussianFilter(5, pos=index)
        elif index == 2:
            filt = GaussianFilter(10, pos=index)
        elif index == 3:
            minibuffer = IntMinibuffer(self.mode, self,
                                       label="Enter pixel radius:",
                                       initial = "10")
            self.mode.setMinibuffer(minibuffer)
        if filt:
            mode.filter = filt
            mode.update()

    def processMinibuffer(self, minibuffer, mode, value):
        dprint("Setting gaussian kernel to %s" % str(value))
        filt = GaussianFilter(value, pos=len(self.items) - 1)
        mode.filter = filt
        mode.update()


class ClippingFilterAction(HSIActionMixin, RadioAction):
    name = "Clipping Filter"
    tooltip = "Clip pixel values to limits"
    default_menu = ("Filter", -400)

    items = ['No Clipping',
             'Pixel > 0', '0 <= Pixel < 256', '0 <= Pixel < 1000',
             '0 <= Pixel < 10000',
             'User Defined']

    def getIndex(self):
        mode = self.mode
        filt = mode.filter
        assert self.dprint(filt)
        if isinstance(filt, ClipFilter):
            return filt.pos
        return 0

    def getItems(self):
        return self.__class__.items

    def action(self, index=-1, multiplier=1):
        assert self.dprint("index=%d" % index)
        mode = self.mode
        filt = None
        if index == 0:
            filt = GeneralFilter(pos=0)
        elif index == 1:
            filt = ClipFilter(0, pos=index)
        elif index == 2:
            filt = ClipFilter(0, 256, pos=index)
        elif index == 3:
            filt = ClipFilter(0, 1000, pos=index)
        elif index == 4:
            filt = ClipFilter(0, 10000, pos=index)
        elif index == 5:
            minibuffer = IntRangeMinibuffer(self.mode, self,
                                            label="Enter clipping min, max:",
                                            initial = "%d, %d" % (0,1000))
            self.mode.setMinibuffer(minibuffer)
        if filt:
            mode.filter = filt
            mode.update()

    def processMinibuffer(self, minibuffer, mode, pair):
        dprint("Setting clipping to %s" % str(pair))
        filt = ClipFilter(pair[0], pair[1], pos=len(self.items) - 1)
        mode.filter = filt
        mode.update()


class SubtractBandAction(HSIActionMixin, MinibufferAction):
    name = "Band Subtraction Filter"
    tooltip = "Subtract a band from the rest of the bands"
    default_menu = ("Filter", -500)
    
    key_bindings = None
    minibuffer = IntMinibuffer
    minibuffer_label = "Subtract Band:"

    def processMinibuffer(self, minibuffer, mode, band_num):
        """
        Callback function used to set the stc to the correct line.
        """
        mode = self.mode
        band_num = mode.cubeview.getIndex(band_num, user=True)
        band = mode.cube.getBand(band_num)
        mode.filter = SubtractFilter(band)
        mode.update()
