from cube import *
from roi import *
from utils import *
from loader import *

class HSIActionMixin(object):
    @classmethod
    def worksWithMajorMode(cls, mode):
        return mode.keyword == "HSI"

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
           ]
