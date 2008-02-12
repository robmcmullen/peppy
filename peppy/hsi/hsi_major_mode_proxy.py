# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info

import peppy.vfs as vfs
from peppy.yapsy.plugins import *

from peppy.debug import *

from peppy.hsi.loader import *

class HSIPlugin(IPeppyPlugin):
    """HSI viewer plugin to register modes and user interface.
    """

    def attemptOpen(self, buffer):
        url = buffer.url
        assert self.dprint("Trying to open url: %s" % repr(unicode(url)))
        hsi_major_mode = self.importModule("hsi_major_mode")
        if hsi_major_mode:
            format = HyperspectralFileFormat.identify(url)
            if format:
                assert dprint("found %s" % format)
                return hsi_major_mode.HSIMode
            else:
                fh = vfs.open(url)
                assert self.dprint("checking for cube handler: %s" % dir(fh))
                if fh and hasattr(fh, 'metadata') and hasattr(fh.metadata, 'getCube'):
                    return hsi_major_mode.HSIMode
        return None
    
    def getCompatibleMajorModes(self, stc_class):
        if stc_class == HyperspectralSTC:
            hsi_major_mode = self.importModule("hsi_major_mode")
            if hsi_major_mode:
                return [hsi_major_mode.HSIMode]
        return []

    def getCompatibleMinorModes(self, cls):
        if cls.keyword == "HSI":
            hsi_major_mode = self.importModule("hsi_major_mode")
            if hsi_major_mode:
                for mode in [hsi_major_mode.HSIXProfileMinorMode,
                             hsi_major_mode.HSIYProfileMinorMode,
                             hsi_major_mode.HSISpectrumMinorMode]:
                    yield mode
        raise StopIteration
    
    def getCompatibleActions(self, mode):
        assert self.dprint("Checking for HSI mode %s" % mode)
        if mode.keyword == "HSI":
            hsi_major_mode = self.importModule("hsi_major_mode")
            if hsi_major_mode:
                return [#hsi_major_mode.PrevCube,
                        #hsi_major_mode.NextCube,
                        #hsi_major_mode.SelectCube,
                        hsi_major_mode.PrevBand,
                        hsi_major_mode.NextBand,
                        hsi_major_mode.GotoBand,
                        hsi_major_mode.ContrastFilterAction,
                        hsi_major_mode.MedianFilterAction,
                        hsi_major_mode.CubeViewAction,
                        hsi_major_mode.ShowPixelValues,
                        ]
        return []
