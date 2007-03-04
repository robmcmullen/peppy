# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
import os,re,urlparse
import urllib2

from cStringIO import StringIO

from trac.core import *
from debug import *

__all__ = [ 'URLInfo', 'GetReader', 'GetWriter', 'IURLHandler' ]


class URLInfo(debugmixin):
    def __init__(self, url, default="file", usewin=None):
        self.url = url
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
            self.readonly = not os.access(self.path, os.W_OK)
        else:
            self.readonly = True

    def __str__(self):
        return "%s %s" % (self.url, (self.protocol,
                                                        self.netloc,
                                                        self.path,
                                                        self.parameters,
                                                        self.query_string,
                                                        self.fragment))

class FileWrapper(object):
    def __init__(self, fh, info):
        self.fh = fh
        self.urlinfo = info

    def __getattr__(self, name):
        return getattr(self.fh, name)


#### The ProtocolHandler and IURLHandler define extensions to the
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


class ProtocolHandler(Component, debugmixin):
    handlers = ExtensionPoint(IURLHandler)

    def __init__(self):
        # Only call this once.
        if hasattr(ProtocolHandler,'opener'):
            return self

        urlhandlers = []
        for handler in self.handlers:
            urlhandlers.extend(handler.getURLHandlers())

        assert self.dprint(urlhandlers)
        ProtocolHandler.opener = urllib2.build_opener(*urlhandlers)
        
    def urlreader(self, url, data=None, usewin=False):
        info = URLInfo(url, "file")

        fh = ProtocolHandler.opener.open(info.url)
        fh.urlinfo = info
        return fh

    def urlwriter(self, url):
        info = URLInfo(url, "file")
        assert self.dprint("trying to open %s" % info.url)
        if info.protocol == "file":
            assert self.dprint("saving to file %s" % info.path)
            fh = FileWrapper(open(info.path, "wb"), info)
            return fh
        raise IOError("protocol %s not supported for writing" % info.protocol)


def GetReader(url, default="file", usewin=False):
    comp_mgr = ComponentManager()
    handler = ProtocolHandler(comp_mgr)
    return handler.urlreader(url)

def GetWriter(url, default="file", usewin=False):
    comp_mgr = ComponentManager()
    handler = ProtocolHandler(comp_mgr)
    return handler.urlwriter(url)


if __name__ == "__main__":
    pass

