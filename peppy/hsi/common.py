from cube import *
from roi import *
from utils import *
from loader import *

class HSIActionMixin(object):
    @classmethod
    def worksWithMajorMode(cls, mode):
        return mode.keyword == "HSI"
    
    def getDatasetPath(self, name):
        """Convenience method to get a full pathname to the dataset filesystem
        that is based on the source pathname.
        
        This adds a prefix to the dataset pathname so that it corresponds to
        the same path used in the source image.  This allows any save commands
        to use the same path on the filesystem as the initial directory shown
        in the file save dialog.
        """
        cwd = self.mode.buffer.cwd()
        import peppy.vfs as vfs
        url = vfs.normalize(cwd)
        path = unicode(url.path)
        name = u"dataset:%s/%s" % (path, name)
        return name

_scipy_mod = "not loaded"
# Some features require scipy, so set this flag to allow the features
# that require scipi to be enabled at runtime
def scipy_module():
    global _scipy_mod
    if _scipy_mod == "not loaded":
        try:
            # Import this way to prevent py2exe from automatically including scipy
            _scipy_mod = __import__('scipy')
            __import__('scipy.signal')
        except:
            _scipy_mod = None
    return _scipy_mod


__all__ = ['HSIActionMixin', 'scipy_module',
           'Cube', 'MetadataMixin', 'newCube', 'createCube', 'createCubeLike',
           'LittleEndian', 'BigEndian',
           'HyperspectralFileFormat', 'HyperspectralSTC',
           'ROI', 'ROIFile',
           'HyperspectralROIFormat',
           'spectralAngle', 'resample', 'normalizeUnits',
           'bandPixelize', 'bandReduceSampling',
           ]
