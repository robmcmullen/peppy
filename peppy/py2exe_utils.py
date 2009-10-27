# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""py2exe utilities

Common functions used for py2exe support
"""

import os, sys, imp

def main_is_frozen():
    return (hasattr(sys, "frozen") or # new py2exe
           hasattr(sys, "importers") # old py2exe
           or imp.is_frozen("__main__")) # tools/freeze

def get_package_data_dir(relative_path, relative_to=None):
    """Gets the package data directory.
    
    @param relative_path: the path starting from the root data directory,
    not from within the peppy directory.  For example, the path should be
    "peppy/help" rather than just "help".
    """
    if main_is_frozen():
        top = os.path.dirname(sys.argv[0])
    else:
        if relative_to is None:
            relative_to = __file__
        top = os.path.dirname(os.path.dirname(relative_to))
    #eprint(top)
    path = os.path.join(top, relative_path)
    #eprint(path)
    return path

