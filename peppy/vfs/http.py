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
import re
from httplib import HTTPConnection
from urllib import urlopen
from StringIO import StringIO

# Import from itools
from itools.vfs import BaseFS, register_file_system
from itools.datatypes import DataType
from itools.vfs.vfs import READ, WRITE, READ_WRITE, APPEND, copy
from itools.uri import get_reference, Reference
from itools.core.cache import LRUCache

from davclient import DAVClient

from peppy.debug import dprint
import pprint
pp = pprint.PrettyPrinter(indent=0)

import utils

# Register a password prompter that the vfs implementation can call if it
# gets an unauthorized user error.  This can be inside the vfs handler so the
# calling program doesn't need to check for unauthorized user errors




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


class TempFile(StringIO):
    """Temporary file-like object that stores itself in the filesystem
    when closed or deleted.

    Since files are stored as a string, some file-like object must be used when
    the user is reading or writing, and this is it.  It's a wrapper around the
    data when reading/writing to an existing file, and automatically updates
    the data storage when it is closed.
    """
    def __init__(self, ref, callback, initial=""):
        StringIO.__init__(self, initial)
        self.ref = ref
        self.callback = callback
        self._is_closed = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        pass

    def close(self):
        self._close()
        self._is_closed = True
        StringIO.close(self)

    def _close(self):
        if self.callback is not None and not self._is_closed:
            data = self.getvalue()
            dprint(repr(data))
            if isinstance(data, unicode):
                data = data.encode('utf8')
            self.callback(self.ref, data)

    def __del__(self):
        if not self._is_closed:
            self._close()
            self._is_closed = True


class WebDavFS(BaseFS):
    temp_file_class = TempFile
    
    re301 = re.compile("<a +href=\"(.+)\">")
    
    remap301 = LRUCache(200)
    
    @classmethod
    def _purge_cache(cls, *refs):
        for ref in refs:
            if ref in cls.remap301:
                del cls.remap301[ref]
    
    @classmethod
    def _get_client(cls, ref):
        if ref in cls.remap301:
            ref = cls.remap301[ref]
        client = DAVClient(ref)
        return ref, client
        
    @classmethod
    def _propfind(cls, ref):
        ref, client = cls._get_client(ref)
        path = str(ref.path)
        dprint("url=%s, path=%s" % (ref, path))
        responses = client.propfind(path, depth=1)
        if client.response.status == 301:
            dprint(client.response.status)
            dprint(pp.pformat(responses))
            dprint(client.response.body)
            match = cls.re301.search(client.response.body)
            if match:
                newpath = match.group(1)
                responses = client.propfind(newpath, depth=1)
                cls.remap301[ref] = get_reference(newpath)
        
        return ref, client.response.status, responses
    
    @classmethod
    def _copy_reference_without_username(cls, ref):
        newauth = ref.authority.host
        if ref.authority.port:
            newauth += ":" + ref.authority.port
        scheme = ref.scheme
        if scheme.startswith("webdav"):
            scheme = "http" + scheme [6:]
        newref = Reference(scheme, newauth, ref.path, ref.query, ref.fragment)
        return newref
    
    @classmethod
    def _get_metadata(cls, ref, metadata, key_error_return=None):
        """Get the metadata item corresponding to the reference
        
        """
        ref, status, responses = cls._propfind(ref)
        if not responses:
            raise OSError("[Errno 2] No such file or directory: '%s'" % ref)
        newref = str(cls._copy_reference_without_username(ref))
        dprint(newref)
        dprint(pp.pformat(responses))
        
        try:
            # Try the full reference
            if newref in responses:
                return responses[newref][metadata]
            
            # If it's a directory, try it without the trailing slash
            if newref.endswith("/"):
                newref = newref[:-1]
                if newref in responses:
                    return responses[newref][metadata]
            
            # Try the path without the hostname
            newref = str(ref.path)
            dprint(newref)
            if newref in responses:
                return responses[newref][metadata]
            
            # If it's a directory, try it without the trailing slash
            if newref.endswith("/"):
                newref = newref[:-1]
                if newref in responses:
                    return responses[newref][metadata]
        except KeyError:
            # Didn't match anything.  If there's a default value return it,
            # otherwise raise an error.
            if key_error_return:
                return key_error_return
        raise OSError("[Errno 2] No such file or directory: '%s'" % ref)

    @classmethod
    def exists(cls, ref):
        ref, status, responses = cls._propfind(ref)
        dprint(status)
        dprint(pp.pformat(responses))
        return status < 400 or status >= 500

    @classmethod
    def can_read(cls, ref):
        return cls.exists(ref)

    @classmethod
    def can_write(cls, ref):
        return False

    @classmethod
    def is_file(cls, ref):
        if cls.exists(ref):
            return not cls.is_folder(ref)
        return False

    @classmethod
    def is_folder(cls, ref):
        dprint(ref)
        if cls.exists(ref):
            dprint(ref)
            mime = cls._get_metadata(ref, 'getcontenttype')
            return mime == "httpd/unix-directory"
        return False

    @classmethod
    def get_mtime(cls, ref):
        mtime = cls._get_metadata(ref, 'getlastmodified')
        return HTTPDate.decode(mtime)

    @classmethod
    def get_mimetype(cls, ref):
        return cls._get_metadata(ref, 'getcontenttype', 'application/octet-stream')

    @classmethod
    def get_size(cls, ref):
        size = cls._get_metadata(ref, 'getcontentlength')
        return int(size)

    @classmethod
    def make_file(cls, ref):
        folder_path = utils.get_dirname(ref)
        dprint(folder_path)
        file_path = utils.get_filename(ref)
        dprint(file_path)

        dest_exists = cls.exists(folder_path)
        if dest_exists:
            dest_exists = cls.exists(ref)
            if dest_exists:
                raise OSError("[Errno 17] File exists: '%s'" % ref)
            elif not cls.is_folder(folder_path):
                raise OSError("[Errno 20] Not a directory: '%s'" % folder_path)
        else:
            cls.make_folder(folder_path)
        
        fh = cls.temp_file_class(ref, cls._save_file)
        return fh
    
    @classmethod
    def _save_file(cls, ref, data):
        ref, client = cls._get_client(ref)
        path = str(ref.path)
        dprint(path)
        try:
            responses = client.put(path, data)
        except:
            dprint(client.response)
            raise
        dprint(repr(data))
        print client.response.status

    @classmethod
    def make_folder(cls, ref):
        if cls.exists(ref):
            if cls.is_folder(ref):
                return
            raise OSError("[Errno 20] Not a directory: '%s'" % ref)
        parent = utils.get_dirname(ref)
        if not cls.is_folder(parent):
            raise OSError("[Errno 20] Not a directory: '%s'" % parent)
        ref, client = cls._get_client(ref)
        path = str(ref.path)
        dprint(path)
        responses = client.mkcol(path)
        print client.response.status

    @classmethod
    def remove(cls, ref):
        if not cls.exists(ref):
            raise OSError("[Errno 17] File exists: '%s'" % ref)

        newref, client = cls._get_client(ref)
        path = str(newref.path)
        dprint(path)
        responses = client.delete(path)
        print client.response.status
        cls._purge_cache(ref, newref)
    
    @classmethod
    def open(cls, ref, mode=None):
        ref, client = cls._get_client(ref)
        body = client.get(str(ref.path))
        
        if mode == WRITE:
            # write truncates
            fh = cls.temp_file_class(ref, cls._save_file, "")
        elif mode == APPEND:
            fh = cls.temp_file_class(ref, cls._save_file, body)
            fh.seek(len(body))
        elif mode == READ_WRITE:
            # Open for read/write but don't position at end of file, i.e. "r+b"
            fh = cls.temp_file_class(ref, cls._save_file, body)
        else:
            fh = cls.temp_file_class(ref, None, body)
        return fh

    @classmethod
    def move(cls, source, target):
        if cls.is_file(target):
            raise OSError("[Errno 20] Not a directory: '%s'" % target)

        ref, client = cls._get_client(source)
        responses = client.move(source, target)
        print client.response.status


register_file_system('http', HTTPReadOnlyFS)

import urlparse
urlparse.uses_relative.append('webdav')
urlparse.uses_netloc.append('webdav')
urlparse.uses_query.append('webdav')
urlparse.uses_params.append('webdav')
urlparse.uses_fragment.append('webdav')
register_file_system('webdav', WebDavFS)
