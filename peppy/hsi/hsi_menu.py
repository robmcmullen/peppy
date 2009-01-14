# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Hyperspectral mode actions

This file is a repository of actions that operate on the HSI mode.
"""

import os, struct, mmap
from cStringIO import StringIO

import wx
import wx.stc as stc
import wx.lib.newevent

from peppy.actions.minibuffer import *
from peppy.actions import *
from peppy.major import *
from peppy.stcinterface import *

from peppy.lib.iconstorage import *
from peppy.lib.bitmapscroller import *

from peppy.hsi.common import *
from peppy.hsi.subcube import *
from peppy.hsi.filter import *
from peppy.hsi.view import *

# hsi mode and the plotting utilities require numpy, the check for which is
# handled by the major mode wrapper
import numpy


class PrevBand(HSIActionMixin, OnDemandActionNameMixin, SelectAction):
    name = "Prev Band"
    default_menu = ("View", -200)
    icon = 'icons/hsi-band-prev.png'
    key_bindings = {'default': "C-p"}
    
    def getMenuItemName(self):
        return _("Prev %s") % self.mode.cubeview.imageDirectionLabel
    
    def getMenuItemHelp(self, name):
        return _("Go to previous %s in the cube") % self.mode.cubeview.imageDirectionLabel.lower()
    
    def getToolbarIconName(self):
        return self.mode.cubeview.prev_index_icon
    
    def isEnabled(self):
        for band in self.mode.cubeview.indexes:
            # check if any of the display bands is at the low limit
            if band < 1:
                return False
        # nope, still room to decrement all bands
        return True

    def action(self, index=-1, multiplier=1):
        #assert self.dprint("Previous band!!!")
        mode = self.mode
        if mode.cubeview.prevIndex():
            mode.update(refresh=False)

class NextBand(HSIActionMixin, OnDemandActionNameMixin, SelectAction):
    name = "Next Band"
    tooltip = "Next Band"
    default_menu = ("View", 201)
    icon = 'icons/hsi-band-next.png'
    key_bindings = {'default': "C-n"}
    
    def getMenuItemName(self):
        return _("Next %s") % self.mode.cubeview.imageDirectionLabel
    
    def getMenuItemHelp(self, name):
        return _("Go to next %s in the cube") % self.mode.cubeview.imageDirectionLabel.lower()
    
    def getToolbarIconName(self):
        return self.mode.cubeview.next_index_icon
    
    def isEnabled(self):
        for band in self.mode.cubeview.indexes:
            # check if any of the display bands is at the high limit
            if band >= self.mode.cubeview.max_index:
                return False
        # nope, still room to advance all bands
        return True

    def action(self, index=-1, multiplier=1):
        assert self.dprint("Next band!!!")
        mode = self.mode
        if mode.cubeview.nextIndex():
            mode.update(refresh=False)

class GotoBand(HSIActionMixin, OnDemandActionNameMixin, MinibufferAction):
    name = "Goto Band"
    default_menu = ("View", 202)
    
    key_bindings = {'default': 'M-g',}
    minibuffer = IntMinibuffer
    minibuffer_label = "Goto Band:"

    def getMenuItemName(self):
        return _("Goto %s") % self.mode.cubeview.imageDirectionLabel
    
    def getMenuItemHelp(self, name):
        return _("Goto a specified %s in the cube") % self.mode.cubeview.imageDirectionLabel.lower()
    
    def processMinibuffer(self, minibuffer, mode, band):
        """
        Callback function used to set the stc to the correct line.
        """
        
        # stc counts lines from zero, but displayed starting at 1.
        #dprint("goto line = %d" % line)
        if mode.cubeview.gotoIndex(band, user=True):
            mode.update(refresh=False)

class SelectBand(HSIActionMixin, OnDemandActionMixin, RadioAction):
    """Select a band to view by name"""
    name = "View Band"
    default_menu = ("View", 205)

    def initPreHook(self):
        self.cubeview = CubeView(self.mode, None)

    def getNonInlineName(self):
        return _("View %s") % self.cubeview.imageDirectionLabel
    
    def updateOnDemand(self):
        self.cubeview = self.mode.cubeview
        self.dprint()
        self.dynamic()
    
    def getHash(self):
        hash = (self.cubeview, self.cubeview.imageDirectionLabel)
        self.dprint(hash)
        return hash

    def getIndex(self):
        if self.cubeview is not None:
            indexes = self.cubeview.getIndexes()
            return indexes[0]
        return 0
    
    def getItems(self):
        if self.cubeview is not None:
            items = self.cubeview.getIndexNames()
        else:
            items = []
        self.dprint(items)
        return items

    def action(self, index=-1, multiplier=1):
        if self.mode.cubeview.gotoIndex(index):
            self.mode.update(refresh=False)


class BandSlider(HSIActionMixin, SliderAction):
    name = "Seek Band"
    default_menu = ("View", 210)
    
    slider_width = 200
    
    def isEnabled(self):
        return self.mode.cubeview.max_index > 1
    
    def updateToolOnDemand(self):
        """Override so we can set the tooltip depending on the view direction"""
        name = _("Seek %s") % self.mode.cubeview.imageDirectionLabel
        self.slider.SetToolTip(wx.ToolTip(name))
        SliderAction.updateToolOnDemand(self)
    
    def getSliderValues(self):
        return self.mode.cubeview.indexes[0], 0, self.mode.cubeview.max_index
    
    def OnSliderMove(self, evt):
        index = evt.GetPosition()
        text = self.mode.cubeview.getBandLegend(index)
        self.mode.setStatusText(text)
        if self.mode.immediate_slider_updates:
            if self.mode.cubeview.gotoIndex(index, user=False):
                self.mode.update()
    
    def action(self, index=-1, multiplier=1):
        #dprint("index=%d" % index)
        if self.mode.immediate_slider_updates and index == self.mode.cubeview.indexes[0]:
            # don't refresh the window if the index hasn't changed from the
            # last update
            return
        if self.mode.cubeview.gotoIndex(index, user=False):
            self.mode.update(refresh=False)

class BandSliderUpdates(HSIActionMixin, ToggleAction):
    """Refresh image during slider dragging"""
    name = "Refresh While Dragging Slider"
    default_menu = ("View", 211)

    def isChecked(self):
        return self.mode.immediate_slider_updates
    
    def action(self, index=-1, multiplier=1):
        self.mode.immediate_slider_updates = not self.mode.immediate_slider_updates


class SwapEndianAction(HSIActionMixin, ToggleAction):
    """Swap the endianness of the data"""
    name = "Swap Endian"
    default_menu = ("View", 309)

    def isChecked(self):
        return self.mode.swap_endian
    
    def action(self, index=-1, multiplier=1):
        self.mode.swap_endian = not self.mode.swap_endian
        self.mode.update()


class ShowPixelValues(HSIActionMixin, ToggleAction):
    name = "Show Pixel Values"
    default_menu = ("View", -900)

    def isChecked(self):
        return self.mode.show_value_at_cursor
    
    def action(self, index=-1, multiplier=1):
        self.mode.show_value_at_cursor = not self.mode.show_value_at_cursor


class TestSubset(HSIActionMixin, SelectAction):
    name = "Test HSI Spatial Subset"
    default_menu = ("&Help/Tests", 888)
    key_bindings = {'default': "C-t"}
    
    testcube = 1
    
    def getTempName(self):
        name = "test%d" % self.__class__.testcube
        self.__class__.testcube += 1
        return self.getDatasetPath(name)
    
    def action(self, index=-1, multiplier=1):
        cube = self.mode.cube
        name = self.getTempName()
        fh = vfs.make_file(name)
        subcube = SubCube(cube)
        subcube.subset(0,cube.lines/2,0,cube.samples/2,0,cube.bands/2)
        fh.setCube(subcube)
        self.frame.open(name)


class SpatialSubset(HSIActionMixin, SelectAction):
    name = "Spatial Subset"
    default_menu = ("Tools", -200)
    
    testcube = 1
    
    def isEnabled(self):
        if self.mode.cubeview.__class__ == CubeView and self.mode.selector.__class__ == RubberBand:
            x, y, w, h = self.mode.selector.getSelectedBox()
            return w > 1 and h > 1
        return False
    
    def getTempName(self):
        name = "spatial_subset%d" % self.__class__.testcube
        self.__class__.testcube += 1
        return self.getDatasetPath(name)
    
    def action(self, index=-1, multiplier=1):
        cube = self.mode.cube
        name = self.getTempName()
        fh = vfs.make_file(name)
        subcube = SubCube(cube)
        sample, line, ds, dl = self.mode.selector.getSelectedBox()
        subcube.subset(line, line+dl, sample, sample+ds, 0, cube.bands)
        fh.setCube(subcube)
        # must close file handle or it won't be registered with the DatasetFS
        # file system
        fh.close()
        self.frame.open(name)


class FocalPlaneAverage(HSIActionMixin, SelectAction):
    """Average all focal planes down to a single focal plane.
    
    """
    name = "Average Focal Planes"
    default_menu = ("Tools", -100)
    
    testcube = 1
    
    def getTempName(self):
        name = "focal_plane_average%d" % self.__class__.testcube
        self.__class__.testcube += 1
        return self.getDatasetPath(name)
    
    def action(self, index=-1, multiplier=1):
        cube = self.mode.cube
        name = self.getTempName()
        fh = vfs.make_file(name)
        avg = createCubeLike(cube, lines=1, interleave='bip')
        data = avg.getNumpyArray()
        #dprint("%d,%d,%d: %s" %(avg.lines, avg.samples, avg.bands, data.shape))
        if cube.isFasterFocalPlane():
            self.mode.status_info.startProgress("Averaging...", cube.lines, delay=1.0)
            temp = numpy.zeros((avg.bands, avg.samples), dtype=numpy.float32)
            line = 0
            for plane in cube.iterFocalPlanes():
                temp += plane
                line += 1
                self.mode.status_info.updateProgress(line)
            temp /= cube.lines
            data[0,:,:] = temp.T
            self.mode.status_info.stopProgress("Averaged %s" % cube.url)
        else:
            self.mode.status_info.startProgress("Averaging...", cube.bands, delay=1.0)
            band = 0
            for plane in cube.iterBands():
                a = numpy.average(plane, axis=0)
                #dprint("band=%d: plane=%s a=%s" % (band, str(plane.shape), str(a.shape)))
                data[0,:,band] = a
                band += 1
                self.mode.status_info.updateProgress(band)
            self.mode.status_info.stopProgress("Averaged %s" % cube.url)
            
        fh.setCube(avg)
        # must close file handle or it won't be registered with the DatasetFS
        # file system
        fh.close()
        options = {
            'view': 'focalplane',
            }
        self.frame.open(name, options=options)


class ScaledImageMixin(HSIActionMixin):
    minibuffer = IntMinibuffer
    minibuffer_label = "Scale Dimensions by Integer Factor:"

    last_scale = 2
    testcube = 1
    
    def isEnabled(self):
        return len(self.mode.cubeview.getCurrentPlanes()) > 0
    
    def getTempName(self):
        name = "scaled%d" % ScaledImageMixin.testcube
        ScaledImageMixin.testcube += 1
        return self.getDatasetPath(name)

    def setLastValue(self, value):
        self.__class__.last_scale = value
        
    def getInitialValueHook(self):
        return str(self.__class__.last_scale)


class ScaleImageDimensions(ScaledImageMixin, MinibufferAction):
    """Create a new image that is a larger scaled version of the current view
    
    Uses the current CubeView image to create a new image that is scaled in
    pixel dimensions.  Note that the CubeView image that is used is after all
    the filters are applied.
    """
    name = "Scale Dimensions by Integer"
    default_menu = ("Tools", -300)
    
    def processMinibuffer(self, minibuffer, mode, scale):
        self.setLastValue(scale)
        
        cube = self.mode.cube
        view = self.mode.cubeview
        planes = view.getCurrentPlanes()
        
        name = self.getTempName()
        fh = vfs.make_file(name)
        newcube = createCubeLike(cube, samples=planes[0].shape[1] * scale,
                                 lines=planes[0].shape[0] * scale,
                                 bands=len(planes), interleave='bsq')
        data = newcube.getNumpyArray()
        dprint("%d,%d,%d: %s" % (newcube.lines, newcube.samples, newcube.bands, data.shape))
        band = 0
        for plane in planes:
            data[band,:,:] = bandPixelize(plane, scale)
            band += 1
            
        fh.setCube(newcube)
        # must close file handle or it won't be registered with the DatasetFS
        # file system
        fh.close()
        self.frame.open(name)


class ReduceImageDimensions(ScaledImageMixin, MinibufferAction):
    """Create a new image by reducing the size of the current view by an
    integer scale factor.
    
    Uses the current CubeView image to create a new image that is scaled in
    pixel dimensions.  Note that the CubeView image that is used is after all
    the filters are applied.
    """
    name = "Reduce Dimensions by Integer"
    default_menu = ("Tools", 301)
    minibuffer_label = "Reduce Dimensions by Integer Factor:"

    def processMinibuffer(self, minibuffer, mode, scale):
        self.setLastValue(scale)
        
        cube = self.mode.cube
        view = self.mode.cubeview
        planes = view.getCurrentPlanes()
        
        name = self.getTempName()
        fh = vfs.make_file(name)
        newcube = createCubeLike(cube, samples=planes[0].shape[1] / scale,
                                 lines=planes[0].shape[0] / scale,
                                 bands=len(planes), interleave='bsq')
        data = newcube.getNumpyArray()
        dprint("%d,%d,%d: %s" % (newcube.lines, newcube.samples, newcube.bands, data.shape))
        band = 0
        for plane in planes:
            data[band,:,:] = bandReduceSampling(plane, scale)
            band += 1
            
        fh.setCube(newcube)
        # must close file handle or it won't be registered with the DatasetFS
        # file system
        fh.close()
        self.frame.open(name)


class ExportAsImage(SelectAction):
    """Export the current datacube in image format like PNG, JPEG, etc.
    """
    name = "as Image"
    default_menu = ("File/Export", -200)

    def action(self, index=-1, multiplier=1):
        filename = self.frame.showSaveAs("Save Image",
                                         wildcard="PNG (*.png)|*.png|JPEG (*.jpg)|*.jpg")
        if filename:
            try:
                status = self.mode.saveImage(filename)
                if status:
                    self.mode.setStatusText("Saved image as %s" % filename)
                else:
                    self.mode.setStatusText("Failed saving %s" % filename)
            except:
                self.frame.showErrorDialog("Unrecognized file format %s\n\nThe filename extension determines the\nimage format.  Use a filename extension of\n.png or .jpg" % ext)


class ExportAsENVI(SelectAction):
    """Export the current datacube in ENVI BIL format
    """
    name = "as ENVI"
    default_menu = ("File/Export", -100)

    def action(self, index=-1, multiplier=1):
        filename = self.frame.showSaveAs("Save Image as ENVI",
                                         wildcard="BIL (*.bil)|*.bil|BIP (*.bip)|*.bip|BSQ (*.bsq)|*.bsq")
        if filename:
            root, ext = os.path.splitext(filename)
            ext = ext.lower()
            if ext in ['.bil', '.bip', '.bsq']:
                handler = HyperspectralFileFormat.getHandlerByName("ENVI")
                if handler:
                    try:
                        self.mode.showBusy(True)
                        self.mode.status_info.startProgress("Exporting to %s" % filename)
                        wx.GetApp().cooperativeYield()
                        handler.export(filename, self.mode.cube, progress=self.updateProgress)
                        self.mode.status_info.stopProgress("Saved %s" % filename)
                        wx.GetApp().cooperativeYield()
                    finally:
                        self.mode.showBusy(False)
                else:
                    self.mode.setStatusText("Can't find ENVI handler")
            else:
                self.frame.showErrorDialog("Unrecognized file format %s\n\nThe filename extension determines the\ninterleave format.  Use a filename extension of\n.bip, .bil, or .bsq" % filename)

    def updateProgress(self, value):
        self.mode.status_info.updateProgress(value)
        wx.GetApp().cooperativeYield()
