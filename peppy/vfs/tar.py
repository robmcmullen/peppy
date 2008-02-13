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
import os
from datetime import datetime
from StringIO import StringIO
import tarfile

# Import from itools
from itools.uri import Path, Reference
from itools.vfs import READ, WRITE, APPEND, copy
from itools.vfs.base import BaseFS
from itools.vfs.registry import register_file_system

class TarFS(BaseFS):
    """Virtual file system to navigate tar (and compressed tar) files.

    The tar: file system is based on the operation of KDE's tar kioslave, where
    only tar files that reside in the local file system are navigable.
    """

    @classmethod
    def _open(cls, path):
        """Find the archive and the path within the archive

        path: string representing the pathname in the local filesystem,
        including the tar file and the path within the tar file.
        
        returns: tuple of (path_to_archive, path_within_archive).  If the
        path to the archive is invalid, None will be returned, but the
        path_within_archive is not checked for validity in this method.
        """
        parent = None
        
        path = path.rstrip('/')
        #print("_open: path=%s" % path)
        components = path.split('/')
        components.reverse()
        
        # handle absolute and relative paths
        if path.startswith('/'):
            archive_path = u'/'
        elif len(path) > 1 and path[0].isalpha() and path[1]==':':
            archive_path = path[0:2]
            components.pop()
        else:
            archive_path = os.getcwd()
        archive_found = False
        member_path = ''
        archive = None
        
        # Find the first archive in the path
        while components:
            comp = components.pop()
            archive_path = u'/'.join([archive_path, comp])
            #print("archive_path=%s" % archive_path)
            try:
                path_exists = os.path.exists(archive_path)
            except UnicodeEncodeError:
                path_exists = os.path.exists(archive_path.encode('utf-8'))
            if path_exists:
                try:
                    archive = BaseFS.find_local_cached('tar', archive_path)
                    if not archive:
                        archive = tarfile.open(archive_path)
                        if archive:
                            BaseFS.store_local_cache('tar', archive_path, archive)
                    archive_found = True
                    break
                except Exception, e:
                    #import traceback
                    #traceback.print_exc()
                    #print("Exception: %s" % str(e))
                    pass
        if archive_found:
            #print archive.getmembers()
            if components:
                components.reverse()
            member_path = u"/".join(components)
            return archive, archive_path, member_path
        return None, None, None
    
    @classmethod
    def _get_info(cls, archive, name):
        if archive and name:
            name = name.rstrip('/')
            try:
                # Python 2.6 and later don't put slashes after directory names
                m = archive.getmember(name)
                return m
            except KeyError:
                # Python 2.4 puts a single slash after the directory name
                try:
                    m = archive.getmember(name + '/')
                    return m
                except KeyError:
                    # Python 2.5 puts a double slash after directory names
                    try:
                        m = archive.getmember(name + '//')
                        return m
                    except:
                        pass
        return None

    @classmethod
    def exists(cls, reference):
        path = unicode(reference.path)
        archive, path, name = cls._open(path)
        return archive is not None

    @classmethod
    def is_file(cls, reference):
        path = unicode(reference.path)
        archive, path, name = cls._open(path)
        m = cls._get_info(archive, name)
        if m:
            return m.isfile()
        return False

    @classmethod
    def is_folder(cls, reference):
        path = unicode(reference.path)
        archive, path, name = cls._open(path)
        if not name:
            # the root of the archive is a folder
            return True
        m = cls._get_info(archive, name)
        if m:
            return m.isdir()
        return False

    @classmethod
    def can_read(cls, reference):
        return cls.is_file(reference)

    @classmethod
    def can_write(cls, reference):
        return False

    @classmethod
    def get_size(cls, reference):
        path = unicode(reference.path)
        archive, path, name = cls._open(path)
        m = cls._get_info(archive, name)
        if m:
            return m.size
        raise OSError("[Errno 2] No such file or directory: '%s'" % reference)

    @classmethod
    def get_mtime(cls, reference):
        path = unicode(reference.path)
        archive, path, name = cls._open(path)
        m = cls._get_info(archive, name)
        if m:
            return datetime.fromtimestamp(m.mtime)
        raise OSError("[Errno 2] No such file or directory: '%s'" % reference)

    @classmethod
    def open(cls, reference, mode=None):
        path = unicode(reference.path)
        archive, path, name = cls._open(path)
        m = cls._get_info(archive, name)
        if not m:
            raise IOError("[Errno 2] No such file or directory: '%s'" % reference)

        if mode == WRITE or mode == APPEND:
            raise OSError("[Errno 30] Read-only file system")
        else:
            fh = archive.extractfile(m)
        return fh

    ######################################################################
    # Folders only
    @classmethod
    def get_names(cls, reference):
        path = unicode(reference.path)
        archive, path, name = cls._open(path)
        if not archive:
            raise OSError('[Errno 20] Not a directory')
        names = []
        if name and not name.endswith('/'):
            name = name + '/'
        cut = len(name)
        for possible in archive.getnames():
            if possible.startswith(name):
                # Only match stuff in this directory; not directories further
                # down.
                #print("possible match for %s: %s" % (name, possible))
                tmp = possible[cut:].replace('//', '/').rstrip('/') # for py 2.5
                comps = tmp.split('/')
                #print("tmp=%s comps=%s" % (tmp, comps))
                if tmp and len(comps)==1:
                    names.append(tmp)
        #print("matches: %s" % names)
        return names


register_file_system('tar', TarFS)
