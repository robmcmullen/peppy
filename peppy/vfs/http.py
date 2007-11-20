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

# Import from itools
from itools.vfs import BaseFS, register_file_system
from itools.datatypes import DataType

class HTTPDate(DataType):
    # XXX As specified by RFC 1945 (HTTP 1.0), should check HTTP 1.1
    # XXX The '%a', '%A' and '%b' format variables depend on the locale
    # (that's what the Python docs say), so what happens if the locale
    # in the server is not in English?

    @staticmethod
    def decode(data):
        formats = [
            # RFC-1123 (updates RFC-822, which uses two-digits years)
            '%a, %d %b %Y %H:%M:%S GMT',
            # RFC-850
            '%A, %d-%b-%y %H:%M:%S GMT',
            # ANSI C's asctime() format
            '%a %b  %d %H:%M:%S %Y',
            # Non-Standard formats, sent by some clients
            # Variation of RFC-1123, uses full day name (sent by Netscape 4)
            '%A, %d %b %Y %H:%M:%S GMT',
            # Variation of RFC-850, uses full month name and full year
            # (unkown sender)
            '%A, %d-%B-%Y %H:%M:%S GMT',
            ]
        for format in formats:
            try:
                tm = time.strptime(data, format)
            except ValueError:
                pass
            else:
                break
        else:
            raise ValueError, 'date "%s" is not an HTTP-Date' % data

        year, mon, mday, hour, min, sec, wday, yday, isdst = tm
        return datetime(year, mon, mday, hour, min, sec)


    @staticmethod
    def encode(value):
        return value.strftime('%a, %d %b %Y %H:%M:%S GMT')


class HTTPFS(BaseFS):

    @staticmethod
    def _head(reference):
        conn = HTTPConnection(str(reference.authority))
        # XXX Add the query
        conn.request('HEAD', str(reference.path))
        return conn.getresponse()


    @staticmethod
    def exists(reference):
        response = HTTPFS._head(reference)
        status = int(response.status)
        return status < 400 or status >= 500


    @staticmethod
    def can_read(reference):
        return HTTPFS.exists(reference)


    @staticmethod
    def can_write(reference):
        return False


    @staticmethod
    def is_file(reference):
        return HTTPFS.exists(reference)


    @staticmethod
    def is_folder(reference):
        return False


    @staticmethod
    def get_mtime(reference):
        response = HTTPFS._head(reference)
        mtime = response.getheader('last-modified')
        if mtime is None:
            return None
        return HTTPDate.decode(mtime)


    @classmethod
    def get_mimetype(cls, reference):
        response = HTTPFS._head(reference)
        ctype = response.getheader('content-type')
        return ctype.split(';')[0]


    @staticmethod
    def get_size(reference):
        response = HTTPFS._head(reference)
        size = response.getheader('content-length')
        return int(size)


    @staticmethod
    def open(reference, mode=None):
        reference = str(reference)
        return urlopen(reference)


register_file_system('http', HTTPFS)
