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
import re, time, calendar
from httplib import HTTPConnection
from urllib import urlopen
from StringIO import StringIO

# Import from itools
from itools.vfs import BaseFS, register_file_system
from itools.datatypes import DataType
from itools.vfs.vfs import READ, WRITE, READ_WRITE, APPEND, copy
from itools.uri import get_reference, Reference
from itools.uri.generic import Authority
from itools.core.cache import LRUCache

from davclient import DAVClient
import BaseHTTPServer
BaseHTTPServer.BaseHTTPRequestHandler.responses[424] = ('Failed Dependency', 'Failed Dependency')

from peppy.lib.dictutils import TimeExpiringDict

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

        return calendar.timegm(tm)

    @staticmethod
    def encode(mtime):
        tm = time.gmtime(mtime)
        return time.strftime('%a, %d %b %Y %H:%M:%S GMT', tm)


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
    
    response_cache = TimeExpiringDict(10)
    
    @classmethod
    def _purge_cache(cls, *refs):
        folders = []
        for orig_ref in refs:
            ref = cls._copy_reference_without_username(orig_ref)
            dprint("Removing cache for %s" % ref)
            if ref in cls.remap301:
                del cls.remap301[ref]
            if ref in cls.response_cache:
                status, responses = cls.response_cache[ref]
                path_found, response = cls._get_response_from_ref(ref, responses)
                try:
                    if response['getcontenttype'] == "httpd/unix-directory":
                        dprint("Found folder %s" % ref)
                        folders.append(ref)
                except KeyError:
                    pass
                del cls.response_cache[ref]
        
        # Remove all the cached data for anything contained in any folders that
        # have been removed.
        for folder in folders:
            dprint("Checking folder %s" % folder)
            folder_url = unicode(folder)
            keys = cls.response_cache.keys()
            for ref in keys:
                dprint("Checking cache %s" % str(ref))
                ref_url = unicode(ref)
                if ref_url.startswith(folder_url):
                    dprint("Removing cache hit %s for deleted folder: %s" % (ref_url, folder_url))
                    del cls.response_cache[ref]
    
    @classmethod
    def _get_client(cls, ref):
        if ref in cls.remap301:
            ref = cls.remap301[ref]
        client = DAVClient(ref)
        newref = cls._copy_reference_without_username(ref)
        return newref, client
        
    @classmethod
    def _propfind(cls, ref):
        ref, client = cls._get_client(ref)
        if ref in cls.response_cache:
            status, responses = cls.response_cache[ref]
            dprint("response_cache hit: %s" % str(ref))
        else:
            dprint("response_cache miss: %s" % str(ref))
            path = str(ref.path)
            responses = client.propfind(path, depth=1)
            if client.response.status == 301:
                #dprint(client.response.status)
                #dprint(pp.pformat(responses))
                #dprint(client.response.body)
                match = cls.re301.search(client.response.body)
                if match:
                    newpath = match.group(1)
                    responses = client.propfind(newpath, depth=1)
                    cls.remap301[ref] = get_reference(newpath)
            status = client.response.status
            dprint("response_cache miss: storing status=%s, response=%s" % (status, responses))
        if responses is not None:
            dprint(ref)
            newref = cls._copy_reference_without_username(ref)
            cls.response_cache[newref] = (status, responses)
        
        return ref, status, responses
    
    @classmethod
    def _copy_reference_without_username(cls, ref):
        newauth = ref.authority.host
        if ref.authority.port:
            newauth += ":" + ref.authority.port
        scheme = ref.scheme
        if scheme.startswith("webdav"):
            scheme = "http" + scheme [6:]
        newref = Reference(scheme, Authority(newauth), ref.path, ref.query, ref.fragment)
        return newref
    
    @classmethod
    def _get_metadata(cls, ref, metadata, key_error_return=None):
        """Get the metadata item corresponding to the reference
        
        """
        ref, status, responses = cls._propfind(ref)
        if not responses:
            raise OSError("[Errno 2] No such file or directory: '%s'" % ref)
        try:
            path_found, response = cls._get_response_from_ref(ref, responses)
            
            if metadata in response:
                return response[metadata]
            return key_error_return
        except KeyError:
            raise OSError("[Errno 2] No such file or directory: '%s'" % ref)

    @classmethod
    def _get_response_from_ref(cls, ref, responses):
        """From the list of responses, return the response that matches the
        requested URL.
        
        @returns: tuple containing the key/value pair of the matching response.
        Note that the key will be the string version of the ref found in the
        responses, and obviously the value is the response corresponding to
        the key.
        
        @raises KeyError if response not found
        """
        newref = str(cls._copy_reference_without_username(ref))
        
        # Try the full reference
        if newref in responses:
            return newref, responses[newref]
        
        # Maybe it's a directory, so try it without or with the trailing slash
        if newref.endswith("/"):
            newref = newref[:-1]
            if newref in responses:
                return newref, responses[newref]
        else:
            dirref = newref + "/"
            if dirref in responses:
                return dirref, responses[dirref]
        
        # Try the path without the hostname
        newref = str(ref.path)
        if newref in responses:
            return newref, responses[newref]
        
        # Maybe it's a directory, so try it without or with the trailing slash
        if newref.endswith("/"):
            newref = newref[:-1]
            if newref in responses:
                return newref, responses[newref]
        else:
            dirref = newref + "/"
            if dirref in responses:
                return dirref, responses[dirref]

    @classmethod
    def exists(cls, ref):
        ref, status, responses = cls._propfind(ref)
        return status < 400 or status >= 500

    @classmethod
    def can_read(cls, ref):
        return cls.exists(ref)

    @classmethod
    def can_write(cls, ref):
        if cls.exists(ref):
            lock = cls._get_metadata(ref, 'lockdiscovery')
            return lock is not None
        return False

    @classmethod
    def is_file(cls, ref):
        if cls.exists(ref):
            return not cls.is_folder(ref)
        return False

    @classmethod
    def is_folder(cls, ref):
        if cls.exists(ref):
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
        file_path = utils.get_filename(ref)

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
        try:
            responses = client.put(path, data)
        except:
            raise
        cls._purge_cache(ref)

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
        # It's also possible (but not required) the parent could be cached, so
        # clean out its cache as well
        dprint(parent)
        cls._purge_cache(parent)

    @classmethod
    def remove(cls, ref):
        if not cls.exists(ref):
            raise OSError("[Errno 17] File exists: '%s'" % ref)

        newref, client = cls._get_client(ref)
        path = str(newref.path)
        responses = client.delete(path)
        dprint(client.response.status)
        cls._purge_cache(ref, newref)
    
    @classmethod
    def open(cls, ref, mode=None):
        ref, client = cls._get_client(ref)
        body = client.get(str(ref.path))
        if client.response.status == 200:
            dprint("%s: %s" % (str(ref), body))
            
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
        else:
            dprint("%s: %s" % (str(ref), client.response.status))
            raise OSError("[Errno %d] %s: '%s'" % (client.response.status, BaseHTTPServer.BaseHTTPRequestHandler.responses[client.response.status][0], ref))

    @classmethod
    def move(cls, source, target):
        if cls.is_file(target):
            raise OSError("[Errno 20] Not a directory: '%s'" % target)

        ref, client = cls._get_client(source)
        responses = client.move(source, target)
        dprint(client.response.status)
        cls._purge_cache(source, target)

    @classmethod
    def get_names(cls, ref):
        # Need to return immediately if there's an incomplete address, only
        # attempting pathname completions when there is a real path.  Otherwise,
        # it can block waiting for a response from a non-existent server.
        if not str(ref.path).startswith("/"):
            return []
        if not cls.is_folder(ref):
            raise OSError("[Errno 20] Not a directory: '%s'" % ref)

        ref, status, responses = cls._propfind(ref)
#        dprint(status)
#        dprint(pp.pformat(responses))
#        dprint(ref)
        prefix, response = cls._get_response_from_ref(ref, responses)
#        dprint(prefix)
#        dprint(response)
        prefix_count = len(prefix)
        filenames = []
        for path, response in responses.iteritems():
            if path.startswith(prefix): # Can this ever not happen?
                filename = path[prefix_count:]
                if filename.startswith("/"):
                    filename = filename[1:]
                if filename:
                    filenames.append(filename)
                    # FIXME: since we have the metadata, it makes sense to
                    # store it in the cache
#        dprint(filenames)
        return filenames

register_file_system('http', HTTPReadOnlyFS)

import urlparse
urlparse.uses_relative.append('webdav')
urlparse.uses_netloc.append('webdav')
urlparse.uses_query.append('webdav')
urlparse.uses_params.append('webdav')
urlparse.uses_fragment.append('webdav')
register_file_system('webdav', WebDavFS)
