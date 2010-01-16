# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import re, time, datetime, calendar, stat
from StringIO import StringIO

# Import from itools
from itools.vfs import BaseFS, register_file_system
from itools.datatypes import HTTPDate
from itools.vfs.vfs import READ, WRITE, READ_WRITE, APPEND, copy
from itools.uri import get_reference, Reference
from itools.uri.generic import Authority
from itools.core.cache import LRUCache

from peppy.lib.dictutils import TimeExpiringDict

from peppy.debug import dprint
import pprint
pp = pprint.PrettyPrinter(indent=0)

import utils
from fs_utils import TempFile




class SFTPFS(BaseFS):
    temp_file_class = TempFile
    
    credentials = {}
    connection_cache = TimeExpiringDict(10)
    
    debug = False

    @classmethod
    def _get_sftp(cls, ref):
        hostname = ref.authority.host
        if ref.authority.port:
            port = ref.authority.port
        else:
            port = 22
        if ref.authority.userinfo:
            if ":" in ref.authority.userinfo:
                username, passwd = ref.authority.userinfo.split(":")
            else:
                username = ref.authority.userinfo
                passwd = ""
        else:
            username = ""
            passwd = ""
        
        if hostname and str(ref.path).startswith("/"):
            # The only time the SFTP client should be created is when a complete
            # path exists.  Otherwise, the user may be in the middle of
            # entering the authority part of the URL and it doesn't make sense
            # to prompt for a username/passwd if the hostname isn't complete.
            transport_key = (hostname, port)
            while True:
                if cls.debug: dprint("username=%s, passwd=%s" % (username, passwd))
                if not passwd:
                    if transport_key in cls.credentials:
                        username, passwd = cls.credentials[transport_key]
                        if cls.debug: dprint("Found cached credentials for %s" % str(transport_key))
                    else:
                        callback = utils.get_authentication_callback()
                        username, passwd = callback(hostname, "sftp", None, username)
                        if cls.debug: dprint("User entered credentials: username=%s, passwd=%s" % (username, passwd))
                if username and passwd:
                    try:
                        t = paramiko.Transport(transport_key)
                        t.connect(username=username, password=passwd, hostkey=None)
                        if t.is_authenticated():
                            if cls.debug: dprint("Authenticated for user %s" % username)
                            cls.credentials[transport_key] = (username, passwd)
                            sftp = paramiko.SFTPClient.from_transport(t)
                            return sftp
                    except paramiko.AuthenticationException:
                        pass
                    if cls.debug: dprint("Failed password for user %s" % username)
                    if transport_key in cls.credentials:
                        del cls.credentials[transport_key]
                    passwd = ""
        
        raise OSError("[Errno 2] Incomplete URL: '%s'" % ref)
        
    @classmethod
    def _get_client(cls, ref):
        newref = cls._copy_root_reference_without_username(ref)
        if newref in cls.connection_cache:
            client = cls.connection_cache[newref]
            if cls.debug: dprint("Found cached sftp connection: %s" % client)
        else:
            client = cls._get_sftp(ref)
            if cls.debug: dprint("Creating sftp connection: %s" % client)
            cls.connection_cache[newref] = client
        return client
        
    @classmethod
    def _stat(cls, ref):
        client = cls._get_client(ref)
        attrs = client.stat(str(ref.path))
        if cls.debug: dprint("%s: %s" % (ref, repr(attrs)))
        return attrs
    
    @classmethod
    def _copy_root_reference_without_username(cls, ref):
        newauth = ref.authority.host
        if ref.authority.port:
            newauth += ":" + ref.authority.port
        newref = Reference(ref.scheme, Authority(newauth), "/", "", "")
        return newref
    
    @classmethod
    def exists(cls, ref):
        try:
            attrs = cls._stat(ref)
            return attrs is not None
        except IOError:
            return False

    @classmethod
    def can_read(cls, ref):
        try:
            attrs = cls._stat(ref)
            return attrs.st_mode & (stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH)
        except IOError:
            return False

    @classmethod
    def can_write(cls, ref):
        try:
            attrs = cls._stat(ref)
            return attrs.st_mode & (stat.S_IWUSR|stat.S_IWGRP|stat.S_IWOTH)
        except IOError:
            return False

    @classmethod
    def is_file(cls, ref):
        try:
            attrs = cls._stat(ref)
            return stat.S_ISREG(attrs.st_mode)
        except IOError:
            return False

    @classmethod
    def is_folder(cls, ref):
        try:
            attrs = cls._stat(ref)
            return stat.S_ISDIR(attrs.st_mode)
        except IOError:
            return False

    @classmethod
    def get_mtime(cls, ref):
        attrs = cls._stat(ref)
        return attrs.st_mtime

    @classmethod
    def get_mtime(cls, ref):
        attrs = cls._stat(ref)
        return attrs.st_mtime

    @classmethod
    def get_atime(cls, ref):
        attrs = cls._stat(ref)
        return attrs.st_atime

    @classmethod
    def get_size(cls, ref):
        attrs = cls._stat(ref)
        return attrs.st_size

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
            try:
                cls.make_folder(folder_path)
            except IOError, e:
                raise OSError(e)
        
        fh = cls.temp_file_class(ref, cls._save_file)
        return fh
    
    @classmethod
    def _save_file(cls, ref, data):
        client = cls._get_client(ref)
        path = str(ref.path)
        fh = client.open(path, mode='w')
        fh.write(data)
        fh.close()

    @classmethod
    def make_folder(cls, ref):
        if cls.exists(ref):
            if cls.is_folder(ref):
                return
            raise OSError("[Errno 20] Not a directory: '%s'" % ref)
        parent = utils.get_dirname(ref)
        if not cls.exists(parent):
            raise OSError("[Errno 2] No such file or directory: '%s'" % parent)
        if not cls.is_folder(parent):
            raise OSError("[Errno 20] Not a directory: '%s'" % parent)
        client = cls._get_client(ref)
        path = str(ref.path)
        if cls.debug: dprint(path)
        client.mkdir(path)

    @classmethod
    def remove(cls, ref):
        if not cls.exists(ref):
            raise OSError("[Errno 2] No such file or directory: '%s'" % ref)

        client = cls._get_client(ref)
        if cls.is_folder(ref):
            # Remove folder contents
            for root, folders, files in cls.walk(client, ref, topdown=False):
                path = str(root.path)
                for name in files:
                    client.remove(path + "/" + name)
                for name in folders:
                    client.rmdir(path + "/" + name)
            # Remove the folder itself
            client.rmdir(str(ref.path))
        else:
            client.remove(str(ref.path))
    
    @classmethod
    def walk(cls, client, top, topdown=True, onerror=None):
        # Taken from os.py
        try:
            names = cls.get_names(top)
        except IOError, err:
            if onerror is not None:
                onerror(err)
            return
        
        dirs, nondirs = [], []
        for name in names:
            ref = top.resolve2(name)
            if cls.is_folder(ref):
                dirs.append(name)
            else:
                nondirs.append(name)

        if topdown:
            yield top, dirs, nondirs
        for name in dirs:
            ref = top.resolve2(name)
            attrs = client.stat(str(ref.path))
            if not stat.S_ISLNK(attrs.st_mode):
                for x in cls.walk(client, ref, topdown, onerror):
                    yield x
        if not topdown:
            yield top, dirs, nondirs
    
    @classmethod
    def open(cls, ref, mode=None):
        if not cls.exists(ref):
            raise OSError("[Errno 2] No such file or directory: '%s'" % ref)
        if not cls.is_file(ref):
            raise OSError("[Errno 20] Not a file: '%s'" % ref)
        client = cls._get_client(ref)
        path = str(ref.path)
        if mode == WRITE:
            # write truncates
            fh = cls.temp_file_class(ref, cls._save_file, "")
        elif mode == APPEND:
            fh = client.open(path, mode='a')
        elif mode == READ_WRITE:
            # Open for read/write but don't position at end of file, i.e. "r+b"
            fh = client.open(path, mode='r+')
        else:
            fh = client.open(path, mode='r')
        return fh

    @classmethod
    def move(cls, source, target):
        if cls.is_file(target):
            raise OSError("[Errno 20] Not a directory: '%s'" % target)

        client = cls._get_client(source)
        client.rename(str(source.path), str(target.path))

    @classmethod
    def get_names(cls, ref):
        if not cls.exists(ref):
            raise OSError("[Errno 2] No such file or directory: '%s'" % ref)
        if not cls.is_folder(ref):
            raise OSError("[Errno 20] Not a directory: '%s'" % ref)
        client = cls._get_client(ref)
        filenames = client.listdir(str(ref.path))
        if cls.debug: dprint(filenames)
        return filenames

try:
    import paramiko
    
    import urlparse
    urlparse.uses_relative.append('sftp')
    urlparse.uses_netloc.append('sftp')
    urlparse.uses_query.append('sftp')
    urlparse.uses_params.append('sftp')
    urlparse.uses_fragment.append('sftp')
    register_file_system('sftp', SFTPFS)
except ImportError:
    pass
