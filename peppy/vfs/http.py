# -*- coding: UTF-8 -*-
# Copyright (C) 2006-2007 Juan David Ibáñez Palomar <jdavid@itaapy.com>
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
from httplib import HTTPConnection
from urllib import urlopen
from StringIO import StringIO

# Import from itools
from itools.vfs import BaseFS, register_file_system
from itools.datatypes import HTTPDate
from itools.vfs.vfs import READ, WRITE, READ_WRITE, APPEND, copy



class HTTPReadOnlyFS(BaseFS):
    @classmethod
    def _head(cls, reference):
        conn = HTTPConnection(str(reference.authority))
        # XXX Add the query
        conn.request('HEAD', str(reference.path))
        return conn.getresponse()

    @classmethod
    def exists(cls, reference):
        response = cls._head(reference)
        status = int(response.status)
        return status < 400 or status >= 500

    @classmethod
    def can_read(cls, reference):
        return cls.exists(reference)

    @classmethod
    def can_write(cls, reference):
        return False

    @classmethod
    def is_file(cls, reference):
        return cls.exists(reference)

    @classmethod
    def is_folder(cls, reference):
        return False

    @classmethod
    def get_mtime(cls, reference):
        response = cls._head(reference)
        mtime = response.getheader('last-modified')
        if mtime is None:
            return None
        return HTTPDate.decode(mtime)

    @classmethod
    def get_mimetype(cls, reference):
        response = cls._head(reference)
        ctype = response.getheader('content-type')
        return ctype.split(';')[0]

    @classmethod
    def get_size(cls, reference):
        response = cls._head(reference)
        size = response.getheader('content-length')
        return int(size)

    @classmethod
    def open(cls, reference, mode=None):
        reference = str(reference)
        return urlopen(reference)

register_file_system('http', HTTPReadOnlyFS)
