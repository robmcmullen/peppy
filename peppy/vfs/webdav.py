# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import re, time, datetime, calendar
from StringIO import StringIO

# Import from itools
from itools.vfs import BaseFS, register_file_system
from itools.datatypes import HTTPDate
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
from fs_utils import TempFile


class WebDavFS(BaseFS):
    temp_file_class = TempFile
    
    re301 = re.compile("<a +href=\"(.+)\">")
    
    remap301 = LRUCache(200)
    
    response_cache = TimeExpiringDict(10)
    
    non_existent_time = datetime.datetime.utcfromtimestamp(0)
    
    debug = False

    @classmethod
    def _purge_cache(cls, *refs):
        folders = []
        for orig_ref in refs:
            ref = cls._copy_reference_without_username(orig_ref)
            if cls.debug: dprint("Removing cache for %s" % ref)
            if ref in cls.remap301:
                del cls.remap301[ref]
            if ref in cls.response_cache:
                status, responses = cls.response_cache[ref]
                path_found, response = cls._get_response_from_ref(ref, responses)
                try:
                    if response['getcontenttype'] == "httpd/unix-directory":
                        if cls.debug: dprint("Found folder %s" % ref)
                        folders.append(ref)
                except KeyError:
                    pass
                del cls.response_cache[ref]
        
        # Remove all the cached data for anything contained in any folders that
        # have been removed.
        for folder in folders:
            if cls.debug: dprint("Checking folder %s" % folder)
            folder_url = unicode(folder)
            keys = cls.response_cache.keys()
            for ref in keys:
                if cls.debug: dprint("Checking cache %s" % str(ref))
                ref_url = unicode(ref)
                if ref_url.startswith(folder_url):
                    if cls.debug: dprint("Removing cache hit %s for deleted folder: %s" % (ref_url, folder_url))
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
            if cls.debug: dprint("response_cache hit: %s" % str(ref))
        else:
            if cls.debug: dprint("response_cache miss: %s" % str(ref))
            path = str(ref.path)
            responses = client.propfind(path, depth=1)
            if client.response.status == 301:
                #if cls.debug: dprint(client.response.status)
                #if cls.debug: dprint(pp.pformat(responses))
                #if cls.debug: dprint(client.response.body)
                match = cls.re301.search(client.response.body)
                if match:
                    newpath = match.group(1)
                    responses = client.propfind(newpath, depth=1)
                    cls.remap301[ref] = get_reference(newpath)
            status = client.response.status
            if cls.debug: dprint("response_cache miss: storing status=%s, response=%s" % (status, responses))
        if responses is not None:
            if cls.debug: dprint(ref)
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
        if status == 403:
            return key_error_return
        elif not responses:
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
            return lock is None
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
        if mtime is not None:
            return HTTPDate.decode(mtime)
        return cls.non_existent_time

    @classmethod
    def get_mimetype(cls, ref):
        return cls._get_metadata(ref, 'getcontenttype', 'application/octet-stream')

    @classmethod
    def get_size(cls, ref):
        size = cls._get_metadata(ref, 'getcontentlength', 0)
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
        if cls.debug: dprint(path)
        responses = client.mkcol(path)
        # It's also possible (but not required) the parent could be cached, so
        # clean out its cache as well
        if cls.debug: dprint(parent)
        cls._purge_cache(parent)

    @classmethod
    def remove(cls, ref):
        if not cls.exists(ref):
            raise OSError("[Errno 17] File exists: '%s'" % ref)

        newref, client = cls._get_client(ref)
        path = str(newref.path)
        responses = client.delete(path)
        if cls.debug: dprint(client.response.status)
        cls._purge_cache(ref, newref)
    
    @classmethod
    def open(cls, ref, mode=None):
        ref, client = cls._get_client(ref)
        body = client.get(str(ref.path))
        if client.response.status == 200:
            if cls.debug: dprint("%s: %s" % (str(ref), body))
            
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
            if cls.debug: dprint("%s: %s" % (str(ref), client.response.status))
            raise OSError("[Errno %d] %s: '%s'" % (client.response.status, BaseHTTPServer.BaseHTTPRequestHandler.responses[client.response.status][0], ref))

    @classmethod
    def move(cls, source, target):
        if cls.is_file(target):
            raise OSError("[Errno 20] Not a directory: '%s'" % target)

        ref, client = cls._get_client(source)
        responses = client.move(source, target)
        if cls.debug: dprint(client.response.status)
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
#        if cls.debug: dprint(status)
#        if cls.debug: dprint(pp.pformat(responses))
#        if cls.debug: dprint(ref)
        prefix, response = cls._get_response_from_ref(ref, responses)
#        if cls.debug: dprint(prefix)
#        if cls.debug: dprint(response)
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
#        if cls.debug: dprint(filenames)
        return filenames

import urlparse
urlparse.uses_relative.append('webdav')
urlparse.uses_netloc.append('webdav')
urlparse.uses_query.append('webdav')
urlparse.uses_params.append('webdav')
urlparse.uses_fragment.append('webdav')
register_file_system('webdav', WebDavFS)
