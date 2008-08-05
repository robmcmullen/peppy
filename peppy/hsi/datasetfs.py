# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Dataset filesystem that manages HSI cubes
"""
from datetime import datetime

from peppy.debug import *

# Import from itools
from peppy.vfs.itools.uri import Path, Reference
from peppy.vfs.itools.vfs import READ, WRITE, READ_WRITE, APPEND, copy
from peppy.vfs.itools.vfs.base import BaseFS
from peppy.vfs.itools.vfs.registry import register_file_system


class TempFile(object):
    """Temporary file-like object that stores itself in the filesystem
    when closed or deleted.

    Since files are stored as a string, some file-like object must be used when
    the user is reading or writing, and this is it.  It's a wrapper around the
    data when reading/writing to an existing file, and automatically updates
    the data storage when it is closed.
    """
    def __init__(self, file_name, metadata=None):
        self.file_name = file_name
        self.metadata = metadata
        self._is_closed = False
    
    def setCube(self, cube):
        # Delay importing subcube until now so we don't import numpy until
        # it's absolutely necessary
        import peppy.hsi.subcube
        self.metadata = peppy.hsi.subcube.SubDataset(cube)
    
    def read(self, numbytes):
        return "-*- HSIMode -*-"
    
    def close(self):
        self._close()
        self._is_closed = True

    def _close(self):
        if self.metadata:
            DatasetFS.root[self.file_name] = self.metadata
        elif self.file_name in DatasetFS.root:
            del DatasetFS.root[self.file_name]

    def __del__(self):
        if not self._is_closed:
            self._close()

class DatasetFS(BaseFS):
    """Memory filesystem based on nested dictionaries.

    The mem: virtual filesystem represents a hierarchical filesystem
    entirely in memory using nested dictionaries as the storage
    mechanism.
    """

    # The rood of the filesystem.  Only one of these per application.
    root = {}

    @classmethod
    def _find(cls, path):
        """Find the item in the filesystem pointed to by the path

        path: string representing the pathname within the mem: filesystem

        returns: tuple of (parent_dict, item, name_in_parent).  If the
        path is valid, the returned item item can be a MemDir or a
        MemFile object.  If the path is invalid, item will be None.
        name_in_parent is the filename of the item stored in the
        parent_dict.
        """
        if path in cls.root:
            return cls.root[path]
        return None

    @classmethod
    def exists(cls, reference):
        path = str(reference.path)
        item = cls._find(path)
#        print("root = %s" % cls.root)
#        print("item = %s" % item)
        return item is not None

    @classmethod
    def is_file(cls, reference):
        path = str(reference.path)
        item = cls._find(path)
        return bool(item)
    
    @classmethod
    def is_folder(cls, reference):
        return False

    @classmethod
    def can_read(cls, reference):
        return cls.is_file(reference)

    @classmethod
    def can_write(cls, reference):
        return cls.is_file(reference)

    @classmethod
    def get_size(cls, reference):
        path = str(reference.path)
        item = cls._find(path)
        if item:
            return item.cube.data_bytes
        raise OSError("[Errno 2] No such file or directory: '%s'" % reference)

    @classmethod
    def get_mtime(cls, reference):
        path = str(reference.path)
        item = cls._find(path)
        if item:
            return item.cube.file_date
        raise OSError("[Errno 2] No such file or directory: '%s'" % reference)


    @classmethod
    def make_file(cls, reference):
        file_path = str(reference.path)

        item = cls._find(file_path)
        if item is not None:
            raise OSError("[Errno 17] File exists: '%s'" % reference)

        fh = TempFile(file_path)
        return fh

    @classmethod
    def remove(cls, reference):
        path = str(reference.path)

        item = cls._find(path)
        if item is None:
            raise OSError("[Errno 2] No such file or directory: '%s'" % reference)
        del cls.root[path]

    @classmethod
    def open(cls, reference, mode=None):
        path = str(reference.path)
        item = cls._find(path)
        if not item:
            raise IOError("[Errno 2] No such file or directory: '%s'" % reference)

        fh = TempFile(path, item)
        return fh

    ######################################################################
    # Folders only
    @classmethod
    def get_names(cls, reference):
        path = str(reference.path)
        dprint(path)
#        item = cls._find(path)
#        if item:
#            raise OSError("[Errno 20] Not a directory '%s'" % reference)
        return cls.root.keys()


register_file_system('dataset', DatasetFS)

# python's urlparse.urlsplit doesn't know anything about mem urls, so we have
# to force it to parse query strings and fragments by adding the mem scheme
# to urlparse's internal arrays
import urlparse
urlparse.uses_fragment.append('dataset')
urlparse.uses_query.append('dataset')
