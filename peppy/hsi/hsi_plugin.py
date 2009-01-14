# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info

import peppy.vfs as vfs
from peppy.yapsy.plugins import *

from peppy.debug import *

from peppy.hsi.loader import *

from peppy.about import AddCopyright
AddCopyright("Matplotlib", "http://matplotlib.sourceforge.org/", "John D. Hunter", "2003-2008", "Colormaps from")

class HSIPlugin(IPeppyPlugin):
    """HSI viewer plugin to register modes and user interface.
    """
    def getHSIModeClass(self):
        """Attempt to import the HSI mode and initialize any needed resources
        """
        try:
            import peppy.hsi.hsi_major_mode
            mode = peppy.hsi.hsi_major_mode.HSIMode
        except Exception, e:
            dprint("FAILED Loading hsi_major_mode")
            import traceback
            error = traceback.format_exc()
            dprint(error)
            raise
        import peppy.hsi.common
        peppy.hsi.common.scipy_module()
        
        return mode
    
    def attemptOpen(self, buffer, url):
        assert self.dprint("Trying to open url: %s" % repr(unicode(url)))
        mode = self.getHSIModeClass()
        format = HyperspectralFileFormat.identify(url)
        if format:
            assert self.dprint("found %s" % repr(format))
            return (None, [peppy.hsi.hsi_major_mode.HSIMode])
        return (None, [])
    
    def getCompatibleMajorModes(self, stc_class):
        if stc_class == HyperspectralSTC:
            try:
                return [self.getHSIModeClass()]
            except:
                dprint("FAILED Loading hsi_major_mode")
                import traceback
                error = traceback.format_exc()
                dprint(error)
                pass
        return []

    def getCompatibleMinorModes(self, cls):
        if cls.keyword == "HSI":
            try:
                import peppy.hsi.plotters
                for mode in [peppy.hsi.plotters.HSIXProfileMinorMode,
                             peppy.hsi.plotters.HSIYProfileMinorMode,
                             peppy.hsi.plotters.HSISpectrumMinorMode]:
                    yield mode
            except:
                pass
        raise StopIteration
    
    def getCompatibleActions(self, mode):
        assert self.dprint("Checking for HSI mode %s" % mode)
        if mode.keyword == "HSI":
            try:
                import peppy.hsi.hsi_menu
                import peppy.hsi.filter_menu
                return [peppy.hsi.hsi_menu.PrevBand,
                        peppy.hsi.hsi_menu.NextBand,
                        peppy.hsi.hsi_menu.SelectBand,
                        peppy.hsi.hsi_menu.GotoBand,
                        peppy.hsi.hsi_menu.BandSlider,
                        peppy.hsi.hsi_menu.BandSliderUpdates,
                        peppy.hsi.filter_menu.ColormapAction,
                        peppy.hsi.filter_menu.ContrastFilterAction,
                        peppy.hsi.filter_menu.MedianFilterAction,
                        peppy.hsi.filter_menu.GaussianFilterAction,
                        peppy.hsi.filter_menu.ClippingFilterAction,
                        peppy.hsi.filter_menu.SubtractBandAction,
                        peppy.hsi.hsi_menu.SwapEndianAction,
                        peppy.hsi.hsi_menu.CubeViewAction,
                        peppy.hsi.hsi_menu.ShowPixelValues,
                        
                        peppy.hsi.hsi_menu.TestSubset,
                        peppy.hsi.hsi_menu.SpatialSubset,
                        peppy.hsi.hsi_menu.FocalPlaneAverage,
                        peppy.hsi.hsi_menu.ScaleImageDimensions,
                        peppy.hsi.hsi_menu.ReduceImageDimensions,
                        
                        peppy.hsi.hsi_menu.ExportAsENVI,
                        peppy.hsi.hsi_menu.ExportAsImage,
                        ]
            except Exception, e:
                dprint(e)
                pass
        return []
