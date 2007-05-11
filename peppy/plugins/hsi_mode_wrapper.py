# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Wrapper for the hyperspectral image analysis mode.

"""

# hsi mode requires numpy, so if we don't have numpy, don't try to
# load the mode.
try:
    import numpy
    HAS_NUMPY = True
except:
    HAS_NUMPY = False

if HAS_NUMPY:
    import peppy.hsi.hsi_major_mode
