# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
import os,re,urlparse
import urllib2

from cStringIO import StringIO

from lib.bufferedreader import *

from trac.core import *
from debug import *

__all__ = [ 'URLInfo', 'IURLHandler', 'URLHandler' ]


class URLInfo(debugmixin):
    def __init__(self, url, default="file", usewin=None):
        self.url = url
        self.bfh = None # Buffered file reader
        
        (self.protocol, self.netloc, self.path, self.parameters,
         self.query_string, self.fragment) = urlparse.urlparse(self.url, default)
        assert self.dprint(self)

        # special handling for windows filenames with drive letters.
        # For testing purposes, usewin can be specified as False
        if os.name in ['nt', 'ce', 'os2'] and usewin is None:
            usewin = True

        if usewin:
            # assert self.dprint(self)
            if len(self.protocol)==1:
                self.path = "%s:%s" % (self.protocol, self.path)
                self.protocol = "file"
            elif len(self.path)>3 and self.path[0] == '/' and self.path[2] == ':':
                self.path = "%s:%s" % (self.path[1], self.path[3:])

        # FIXME: this file specific stuff should be moved outta here
        if self.protocol == "file":
            # urlparse makes a distinction between file://name and
            # file:///name:
            # >>> urlparse("file://LICENSE")
            # ('file', 'LICENSE', '', '', '', '')
            # >>> urlparse("file:///LICENSE")
            # ('file', '', '/LICENSE', '', '', '')

            # but, I don't need that distinction, so just cat them.
            self.path = os.path.abspath(self.netloc + self.path)
            if usewin:
                self.url = "file:///" + self.path.replace('\\','/')
            elif usewin == False and os.name in ['nt', 'ce', 'os2']:
                self.path = self.path[2:] # remove drive letter
                self.url = "file://" + self.path.replace('\\','/')
            else:
                self.url = "file://" + self.path
            self.netloc = ''

    def __repr__(self):
        return "%s %s" % (self.url, (self.protocol,
                                                        self.netloc,
                                                        self.path,
                                                        self.parameters,
                                                        self.query_string,
                                                        self.fragment))

    def __str__(self):
        return self.url

    def exists(self):
        if self.protocol == 'file':
            return os.path.exists(self.path)
        else:
            try:
                fh = self.getReader()
                return True
            except urllib2.URLError:
                return False

    def readonly(self):
        if self.protocol == "file":
            return not os.access(self.path, os.W_OK)
        else:
            return True

    def getBasename(self):
        basename=os.path.basename(self.path)
        if not basename:
            # It's possible that the basename doesn't exist:
            # e.g. http://www.flipturn.org doesn't have a path
            # component to the url.  Even though it actually refers to
            # http://www.flipturn.org/index.html, nothing in the
            # returned data indicates the actual filename.

            # FIXME: So, what to do about it?
            if self.bfh:
                dprint("info: %s" % self.bfh.fh.info())
                dprint("geturl: %s" % self.bfh.fh.geturl())
        return basename

    def getReader(self, size=1024):
        if self.bfh is None:
            fh = self.getDirectReader()
            self.bfh = BufferedReader(fh, size)
        self.bfh.seek(0)
        return self.bfh

    def getDirectReader(self):
        comp_mgr = ComponentManager()
        handler = URLHandler(comp_mgr)
        fh = handler.urlreader(self)
        if self.protocol == 'file':
            fh.tell = fh.fp.tell
            fh.seek = fh.fp.seek
        return fh

    def getWriter(self):
        comp_mgr = ComponentManager()
        handler = URLHandler(comp_mgr)
        fh = handler.urlwriter(self)
        return fh



#### The URLHandler and IURLHandler define extensions to the
#### urllib2 module to load other types of URLs.

class IURLHandler(Interface):
    """Interface for IO plugins.  A plugin that implements this
    interface takes a URL in the form of protocol://path/to/some/file
    and implements two methods that return a file-like object that can
    be used to either read from or write to the datastore that is
    pointed to by the URL.  Some protocols, like http, will typically
    be read-only, which means the getWriter method may be omitted from
    the plugin."""

    def getURLHandlers():
        """Return a list of urllib2 handlers defining new protocol
        support."""


class URLHandler(Component, debugmixin):
    handlers = ExtensionPoint(IURLHandler)

    def __init__(self):
        # Only call this once, unless forced to by removing the
        # attribute 'opener' from the class namespace.
        if hasattr(URLHandler,'opener'):
            return self

        # urllib2 seems to want a complete set of handlers built at
        # once -- it doesn't work calling build_opener more than once,
        # because it forgets all the previous user defined handlers.
        urlhandlers = []
        for handler in self.handlers:
            urlhandlers.extend(handler.getURLHandlers())

        assert self.dprint(urlhandlers)
        URLHandler.opener = urllib2.build_opener(*urlhandlers)

    @classmethod
    def clearHandlers(cls):
        """Force handlers to be reloaded next time a handler is requested."""
        
        if hasattr(URLHandler,'opener'):
            delattr(URLHandler,'opener')

    def urlreader(self, info):
        """Get a file-like object for reading from this url."""
        fh = URLHandler.opener.open(info.url)
        fh.urlinfo = info
        return fh

    def urlwriter(self, info):
        """Get a file-like object for (binary) writing to this url.

        Currently, only file:// style urls are supported for writing.
        Theoretically, webdav can be used to write to an http scheme
        url, but I haven't figured that out yet.
        """
        assert self.dprint("trying to open %s" % info.url)
        if info.protocol == "file":
            assert self.dprint("saving to file %s" % info.path)
            fh = open(info.path, "wb")
            return fh
        raise IOError("protocol %s not supported for writing" % info.protocol)


if __name__ == "__main__":
    pass

