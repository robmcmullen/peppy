import os

from peppy.vfs.itools.datatypes import FileName
from peppy.vfs.itools.vfs import *
from peppy.vfs.itools.vfs.registry import get_file_system, deregister_file_system
from peppy.vfs.itools.uri import *

import peppy.vfs.mem
import peppy.vfs.http
import peppy.vfs.tar

def normalize(ref, base=None):
    """Normalize a url string into a reference and fix windows shenanigans"""
    if not isinstance(ref, Reference):
        ref = get_reference(ref)
    # Check the reference is absolute
    if ref.scheme:
        return ref
    # Default to the current working directory
    if base is None:
        base = os.getcwd()
    
    # URLs always use /
    if os.path.sep == '\\':
        base = base.replace(os.path.sep, '/')
    # Check windows drive letters
    if base[1] == ':':
        base = "%s:%s" (base[0].lower(), base[2:])
    baseref = get_reference('file://%s/' % base)
    return baseref.resolve(ref)

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
    'deregister_file_system',
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
    'normalize',
    ]
