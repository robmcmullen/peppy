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
        try:
            import peppy.hsi.hsi_major_mode
            format = HyperspectralFileFormat.identify(url)
            if format:
                assert dprint("found %s" % format)
                return peppy.hsi.hsi_major_mode.HSIMode
            else:
                fh = vfs.open(url)
                assert self.dprint("checking for cube handler: %s" % dir(fh))
                if fh and hasattr(fh, 'metadata') and hasattr(fh.metadata, 'getCube'):
                    return peppy.hsi.hsi_major_mode.HSIMode
        except:
                dprint("FAILED Loading hsi_major_mode")
                raise
        return None
    
    def getCompatibleMajorModes(self, stc_class):
        if stc_class == HyperspectralSTC:
            try:
                import peppy.hsi.hsi_major_mode
                return [peppy.hsi.hsi_major_mode.HSIMode]
            except:
                dprint("FAILED Loading hsi_major_mode")
                pass
        return []

    def getCompatibleMinorModes(self, cls):
        if cls.keyword == "HSI":
            try:
                import peppy.hsi.hsi_major_mode
                for mode in [peppy.hsi.hsi_major_mode.HSIXProfileMinorMode,
                             peppy.hsi.hsi_major_mode.HSIYProfileMinorMode,
                             peppy.hsi.hsi_major_mode.HSISpectrumMinorMode]:
                    yield mode
            except:
                pass
        raise StopIteration
    
    def getCompatibleActions(self, mode):
        assert self.dprint("Checking for HSI mode %s" % mode)
        if mode.keyword == "HSI":
            try:
                import peppy.hsi.hsi_major_mode
                return [peppy.hsi.hsi_major_mode.PrevBand,
                        peppy.hsi.hsi_major_mode.NextBand,
                        peppy.hsi.hsi_major_mode.GotoBand,
                        peppy.hsi.hsi_major_mode.ContrastFilterAction,
                        peppy.hsi.hsi_major_mode.MedianFilterAction,
                        peppy.hsi.hsi_major_mode.CubeViewAction,
                        peppy.hsi.hsi_major_mode.ShowPixelValues,
                        ]
            except:
                pass
        return []
