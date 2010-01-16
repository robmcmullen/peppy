import os, sys
import copy as pycopy

from peppy.vfs.itools.vfs import *
from peppy.vfs.itools.vfs.registry import get_file_system, deregister_file_system, _file_systems
from peppy.vfs.itools.uri import *
from peppy.vfs.itools.vfs.base import BaseFS

from peppy.vfs.utils import *

import peppy.vfs.http
import peppy.vfs.webdav
import peppy.vfs.tar
import peppy.vfs.sftp


__all__ = [
    ##### From vfs:
    'BaseFS',
    'FileFS',
    # File modes
    'READ',
    'WRITE',
    'READ_WRITE',
    'APPEND',
    # Registry
    'register_file_system',
    'deregister_file_system',
    'get_file_system',
    'get_file_system_schemes',
    
    # Authentication
    'register_authentication_callback',
    'get_authentication_callback',
    'AuthenticationCancelled',
    
    # Functions
    'exists',
    'is_file',
    'is_folder',
    'can_read',
    'can_write',
    'get_permissions',
    'set_permissions',
    'get_ctime',
    'get_mtime',
    'get_atime',
    'get_mimetype',
    'get_size',
    'make_file',
    'make_folder',
    'remove',
    'open',
    'open_numpy_mmap',
    'open_write',
    'get_metadata',
    'copy',
    'move',
    'get_names',
    'traverse',

    ##### From uri:
    'get_reference',
    'normalize',
    'canonical_reference',
    'get_dirname',
    'get_filename',
    ]
