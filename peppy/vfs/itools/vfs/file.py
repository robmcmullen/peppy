# -*- coding: UTF-8 -*-
# Copyright (C) 2006-2007 Juan David Ibáñez Palomar <jdavid@itaapy.com>
# Copyright (C) 2007 Rob McMullen <rob.mcmullen@gmail.com>
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
from os import (listdir, makedirs, mkdir, remove, rename, rmdir, stat, walk,
                access, R_OK, W_OK)
from os.path import (exists, getatime, getctime, getmtime, getsize, isfile,
    isdir, join)
from subprocess import call

# Import from itools
from peppy.vfs.itools.uri import Path, Reference
from vfs import READ, WRITE, READ_WRITE, APPEND, copy
from base import BaseFS
from registry import register_file_system


class FileFS(BaseFS):

    @classmethod
    def unicode_wrapper(cls, reference, func):
        path = unicode(reference.path)
        try:
            return func(path)
        except UnicodeEncodeError:
            return func(path.encode('utf-8'))


    @classmethod
    def exists(cls, reference):
        return cls.unicode_wrapper(reference, exists)


    @classmethod
    def is_file(cls, reference):
        return cls.unicode_wrapper(reference, isfile)


    @classmethod
    def is_folder(cls, reference):
        return cls.unicode_wrapper(reference, isdir)


    @classmethod
    def can_read(cls, reference):
        path = unicode(reference.path)
        try:
            return access(path, R_OK)
        except UnicodeEncodeError:
            return access(path.encode('utf-8'), R_OK)


    @classmethod
    def can_write(cls, reference):
        path = unicode(reference.path)
        try:
            return access(path, W_OK)
        except UnicodeEncodeError:
            return access(path.encode('utf-8'), W_OK)


    @classmethod
    def get_ctime(cls, reference):
        return datetime.fromtimestamp(cls.unicode_wrapper(reference, getctime))


    @classmethod
    def get_mtime(cls, reference):
        return datetime.fromtimestamp(cls.unicode_wrapper(reference, getmtime))


    @classmethod
    def get_atime(cls, reference):
        return datetime.fromtimestamp(cls.unicode_wrapper(reference, getatime))


    @classmethod
    def get_size(cls, reference):
        return cls.unicode_wrapper(reference, getsize)


    @classmethod
    def make_file(cls, reference):
        folder_path = unicode(reference.path[:-1])
        file_path = unicode(reference.path)

        try:
            dest_exists = exists(folder_path)
        except UnicodeEncodeError:
            folder_path = folder_path.encode('utf-8')
            dest_exists = exists(folder_path)
        if dest_exists:
            try:
                dest_exists = exists(file_path)
            except UnicodeEncodeError:
                file_path = file_path.encode('utf-8')
                dest_exists = exists(file_path)
            if dest_exists:
                raise OSError, "File exists: '%s'" % reference
        else:
            makedirs(folder_path)
        try:
            fh = file(file_path, 'wb')
        except UnicodeEncodeError:
            fh = file(file_path.encode('utf-8'), 'wb')
        return fh


    @classmethod
    def make_folder(cls, reference):
        cls.unicode_wrapper(reference, mkdir)


    @classmethod
    def remove(cls, path):
        if isinstance(path, Reference):
            path = unicode(path.path)
        elif isinstance(path, Path):
            path = unicode(path)

        try:
            existence = exists(path)
        except UnicodeEncodeError:
            path = path.encode('utf-8')
            existence = exists(path)
        if not existence:
            raise OSError, "File does not exist '%s'" % path

        if isdir(path):
            # Remove folder contents
            for root, folders, files in walk(path, topdown=False):
                for name in files:
                    remove(join(root, name))
                for name in folders:
                    rmdir(join(root, name))
            # Remove the folder itself
            rmdir(path)
        else:
            remove(path)


    @classmethod
    def open(cls, reference, mode=None):
        path = unicode(reference.path)
        try:
            existence = exists(path)
        except UnicodeEncodeError:
            path = path.encode('utf-8')
            existence = exists(path)
        if not existence:
            raise OSError, "File does not exist '%s'" % reference

        # Open for write
        if mode == WRITE:
            return file(path, 'wb')
        # Open for read/write
        if mode == READ_WRITE:
            return file(path, 'r+b')
        # Open for append
        if mode == APPEND:
            return file(path, 'ab')
        # Open for read (default)
        return file(path, 'rb')


    @classmethod
    def move(cls, source, target):
        # Fail if target exists and is a file
        dst = unicode(target.path)
        src = unicode(source.path)
        try:
            target_file = isfile(dst)
        except UnicodeEncodeError:
            dst = dst.encode('utf-8')
            src = src.encode('utf-8')
            target_file = isfile(dst)
        if target_file:
            raise OSError, '[Errno 20] Not a directory'

        # If target is a folder, move inside it
        if isdir(dst):
            dst = target.path.resolve2(source.path[-1])
            dst = unicode(dst)

        try:
            rename(src, dst)
        except OSError:
            copy(src, dst)
            cls.remove(src)


    ######################################################################
    # Folders only
    @classmethod
    def get_names(cls, reference):
        path = unicode(reference.path)
        try:
            names = listdir(path)
            to_unicode = True
        except UnicodeEncodeError:
            names = listdir(path.encode('utf-8'))
            to_unicode = False
        if to_unicode:
            if names and isinstance(names[0], str):
                names = [n.decode('utf-8') for n in names]
        return names
        



register_file_system('file', FileFS)
