from peppy.vfs.itools.datatypes import FileName
from peppy.vfs.itools.vfs import *
from peppy.vfs.itools.vfs.registry import get_file_system
from peppy.vfs.itools.uri import *

import peppy.vfs.mem
import peppy.vfs.http
import peppy.vfs.tar

__all__ = [
    ##### From vfs:
    'BaseFS',
    'FileFS',
    # File modes
    'READ',
    'WRITE',
    'APPEND',
    # Registry
    'register_file_system',
    'get_file_system',
    # Functions
    'exists',
    'is_file',
    'is_folder',
    'can_read',
    'can_write',
    'get_ctime',
    'get_mtime',
    'get_atime',
    'get_mimetype',
    'get_size',
    'make_file',
    'make_folder',
    'remove',
    'open',
    'copy',
    'move',
    'get_names',
    'traverse',

    ##### From uri:
    'get_reference',
    ]
