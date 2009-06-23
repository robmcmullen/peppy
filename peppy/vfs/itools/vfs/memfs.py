# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Rob McMullen <robm@users.sourceforge.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Import from the Standard Library
from datetime import datetime
from StringIO import StringIO

# Import from itools
from peppy.vfs.itools.uri import Path, Reference
from vfs import READ, WRITE, READ_WRITE, APPEND, copy
from base import BaseFS
from registry import register_file_system
from permissions import Permissions


class MemDir(dict):
    """Base class used for representing directories.

    Nested dictionaries are used to represent directories, and this subclass
    of dict provides a few additional methods over simply using a dict.
    """
    is_file = False
    
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.mtime = datetime.now()

    def get_size(self):
        return 0
    
    def get_mtime(self):
        return self.mtime

    def ls(self, indent=""):
        """Debugging function to do a recursive list of the filesystem"""
        s = StringIO()
        for key in self.keys():
            if self[key].is_file:
                s.write("%s%s\n" % (indent, key))
            else:
                s.write("%s%s:\n" % (indent, key))
                contents = self[key].ls(indent + "  ")
                s.write(contents)
        return s.getvalue()


class MemFile(object):
    """Base class to represent files.

    Stored files are represented as objects in the memory filesystem.  To
    minimize the memory footprint, the data itself is stored as a string
    (rather than as a StringIO instance, for example).
    """
    is_file = True

    def __init__(self, data, name=""):
        self.data = data
        self.name = name
        self.mtime = datetime.now()

    def get_mtime(self):
        return self.mtime

    def get_size(self):
        return len(self.data)


class TempFile(StringIO):
    """Temporary file-like object that stores itself in the filesystem
    when closed or deleted.

    Since files are stored as a string, some file-like object must be used when
    the user is reading or writing, and this is it.  It's a wrapper around the
    data when reading/writing to an existing file, and automatically updates
    the data storage when it is closed.
    """
    file_class = MemFile
    
    def __init__(self, folder, file_name, initial="", read_only=False):
        StringIO.__init__(self, initial)
        self.folder = folder
        self.file_name = file_name
        self._is_closed = False
        self._read_only = read_only
    
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        pass

    def close(self):
        self._close()
        self._is_closed = True
        StringIO.close(self)

    def _close(self):
        if not self._read_only:
            data = self.getvalue()
            if isinstance(data, unicode):
                data = data.encode('utf8')
            self.folder[self.file_name] = self.file_class(data, self.file_name)

    def __del__(self):
        if not self._is_closed:
            self._close()


class MemFS(BaseFS):
    """Memory filesystem based on nested dictionaries.

    The mem: virtual filesystem represents a hierarchical filesystem
    entirely in memory using nested dictionaries as the storage
    mechanism.
    """

    # The rood of the filesystem.  Only one of these per application.
    root = MemDir()
    
    temp_file_class = TempFile

    @classmethod
    def _normalize_path(cls, path):
        """Normalize the path to conform to the nested dict structure."""
        # FIXME: no interface in itools to set current working
        # directory?  Set '.' to '/'
        if path.startswith('.'):
            path = path[1:]

        # strip off leading '/'; root of / is implicit
        path = path.lstrip('/')

        while path.endswith('/'):
            path = path[:-1]
        return path

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
        parent = None
        fs = cls.root

        path = cls._normalize_path(path)
        if not path:
            return parent, fs, path
        components = path.split('/')

        # Skip over the root level since it is implicit in the storage
        for comp in components:
            if fs.is_file:
                # if we've found a file but we've still got path
                # components left, return error
                return None, None, None
            if comp in fs:
                parent = fs
                fs = fs[comp]
            else:
                return parent, None, comp
        return parent, fs, comp

    @classmethod
    def _makedirs(cls, path):
        """Create nested dicts representing path.

        Create the hierarchy of nested dicts such that the entire path
        is represented in the filesystem.

        path: string representing the pathname
        """
        path = cls._normalize_path(path)
        if not path:
            return
        fs = cls.root
        components = path.split('/')
        for comp in components:
            if fs.is_file:
                raise OSError("[Errno 20] Not a directory: '%s'" % path)
            if comp in fs:
                fs = fs[comp]
            else:
                fs[comp] = MemDir()
                fs = fs[comp]
        if fs.is_file:
            raise OSError("[Errno 20] Not a directory: '%s'" % path)

    @classmethod
    def exists(cls, reference):
        path = str(reference.path)
        parent, item, name = cls._find(path)
        return item is not None

    @classmethod
    def is_file(cls, reference):
        path = str(reference.path)
        parent, item, name = cls._find(path)
        if item is not None:
            return item.is_file
        return False

    @classmethod
    def is_folder(cls, reference):
        path = str(reference.path)
        parent, item, name = cls._find(path)
        if item is not None:
            return not item.is_file
        return False

    @classmethod
    def can_read(cls, reference):
        return cls.is_file(reference)

    @classmethod
    def can_write(cls, reference):
        return cls.is_file(reference)

    @classmethod
    def get_permissions(cls, reference):
        perm = Permissions(0)
        perm.set_mode('u', 'r', True)
        perm.set_mode('u', 'w', True)
        perm.set_mode('g', 'r', True)
        perm.set_mode('o', 'r', True)
        return perm

    @classmethod
    def set_permissions(cls, reference, permissions):
        pass

    @classmethod
    def get_size(cls, reference):
        path = str(reference.path)
        parent, item, name = cls._find(path)
        if item:
            return item.get_size()
        raise OSError("[Errno 2] No such file or directory: '%s'" % reference)

    @classmethod
    def get_mtime(cls, reference):
        path = str(reference.path)
        parent, item, name = cls._find(path)
        if item:
            return item.get_mtime()
        raise OSError("[Errno 2] No such file or directory: '%s'" % reference)


    @classmethod
    def make_file(cls, reference):
        folder_path = str(reference.path[:-1])
        file_path = str(reference.path)

        parent, item, dummy = cls._find(file_path)
        if parent is not None:
            if parent.is_file:
                raise OSError("[Errno 20] Not a directory: '%s'" % folder_path)
            if item is not None:
                raise OSError("[Errno 17] File exists: '%s'" % reference)
        else:
            cls._makedirs(folder_path)

        file_name = reference.path.get_name()
        parent, folder, folder_name = cls._find(folder_path)
        if parent and parent.is_file:
            raise OSError("[Errno 20] Not a directory: '%s'" % folder_path)
        fh = cls.temp_file_class(folder, file_name)
        return fh

    @classmethod
    def make_folder(cls, reference):
        path = str(reference.path)
        cls._makedirs(path)

    @classmethod
    def remove(cls, reference):
        path = str(reference.path)

        parent, item, name = cls._find(path)
        if item is None:
            raise OSError("[Errno 2] No such file or directory: '%s'" % reference)
        if item.is_file:
            del parent[name]
        else:
            # we need to go up a level and remove the entire dict.
            folder_path = str(reference.path[:-1])
            grandparent, parent, grandparent_name = cls._find(folder_path)
            del parent[name]

    @classmethod
    def open(cls, reference, mode=None):
        path = str(reference.path)
        parent, item, name = cls._find(path)
        if not parent:
            raise IOError("[Errno 20] Not a directory: '%s'" % reference)
        if not item:
            raise IOError("[Errno 2] No such file or directory: '%s'" % reference)

        file_name = reference.path[-1]

        if mode == WRITE:
            # write truncates
            fh = cls.temp_file_class(parent, file_name, "")
        elif mode == APPEND:
            fh = cls.temp_file_class(parent, file_name, item.data)
            fh.seek(item.get_size())
        elif mode == READ_WRITE:
            # Open for read/write but don't position at end of file, i.e. "r+b"
            fh = cls.temp_file_class(parent, file_name, item.data)
        else:
            fh = cls.temp_file_class(parent, file_name, item.data, True)
        return fh

    @classmethod
    def move(cls, source, target):
        # Fail if target exists and is a file
        tgtpath = str(target.path)
        parent, item, tgtname = cls._find(tgtpath)
        if item:
            if item.is_file:
                raise OSError("[Errno 20] Not a directory: '%s'" % target)
            dest = item
        else:
            # the target doesn't exist, so it must be the pathname of
            # the new item.
            tgtname = target.path[-1]
            folder_path = str(target.path[:-1])
            cls._makedirs(folder_path)
            parent, dest, dummy = cls._find(folder_path)

        srcpath = str(source.path)
        srcdir, src, origname = cls._find(srcpath)
        if src:
            dest[tgtname] = src
            del srcdir[origname]
        else:
            raise OSError("[Errno 2] No such file or directory: '%s'" % source)

    ######################################################################
    # Folders only
    @classmethod
    def get_names(cls, reference):
        path = str(reference.path)
        parent, item, name = cls._find(path)
        if item.is_file:
            raise OSError("[Errno 20] Not a directory '%s'" % reference)
        return item.keys()


register_file_system('mem', MemFS)

# python's urlparse.urlsplit doesn't know anything about mem urls, so we have
# to force it to parse query strings and fragments by adding the mem scheme
# to urlparse's internal arrays
import urlparse
urlparse.uses_fragment.append('mem')
urlparse.uses_query.append('mem')
