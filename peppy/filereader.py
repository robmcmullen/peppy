# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, re, time, codecs

from cStringIO import StringIO

from wx.lib.pubsub import Publisher

import peppy.vfs as vfs

from peppy.debug import *
from peppy.lib.textutil import detectEncoding


class FileReader(debugmixin):
    """The base class used to read from files, including threaded support.
    
    """
    def __init__(self, fh, url, message=None, encoding=None):
        """Initialize the styled text control with peppy extensions.
        
        @param fh: filehandle to already open file
        
        @param url: URL of filehandle
        
        @keyword message: optional pubsub message to use for progress bar
        indicator
        
        @keyword encoding: optional encoding to use rather than scanning the
        text for a "magic comment" that indicates the encoding
        """
        self.fh = fh
        self.url = url
        
        # optional pubsub message
        self.message = message

        self.encoding = encoding
        
        self.tempstore = StringIO()
        self.bytes = None

        self.start()
    
    def start(self):
        length = vfs.get_size(self.url)
        assert self.dprint("Loading %d bytes" % length)
        chunk = 65536
        if length/chunk > 100:
            chunk *= 4
        self.readFrom(chunk=chunk, length=length)
    
    def readFrom(self, amount=None, chunk=65536, length=0):
        """Read a chunk of the file from the file-like object.
        
        Rather than reading the file in with a single call to fh.read(), it is
        broken up into segments.  It may take a significant amount of time to
        read a file, either if the file is really big or the file is loaded
        over a slow URI scheme.  The threaded load capability of peppy is used
        to display a progress bar that is updated after each segment is loaded,
        and also keeps the user interface responsive during a file load.
        """
        total = 0
        while amount is None or total<amount:
            txt = self.fh.read(chunk)
            assert self.dprint("reading %d bytes from %s" % (len(txt), self.fh))

            if len(txt) > 0:
                total += len(txt)
                if self.message:
                    # Negative value will switch the progress bar to
                    # pulse mode
                    Publisher().sendMessage(self.message, (total*100)/length)
                
                if isinstance(txt, unicode):
                    # This only seems to happen for unicode files written
                    # to the mem: filesystem, but if it does happen to be
                    # unicode, there's no need to convert the data
                    self.encoding = "utf-8"
                    self.tempstore.write(unicode.encode('utf-8'))
                else:
                    self.tempstore.write(txt)
            else:
                # stop when we reach the end.  An exception will be
                # handled outside this class
                break
    
    def isUnicode(self):
        bytes = self.getBytes()
        
        # Normalize the encoding name by running it through the codecs list
        if self.encoding:
            self.encoding = codecs.lookup(self.encoding).name
        
        # If an encoding is not specified, or it's not found in the codecs
        # list, try to scan the file for an encoding
        if not self.encoding:
            self.encoding = detectEncoding(self.bytes)

        return self.encoding is not None
    
    def getBytes(self):
        if self.bytes is None:
            self.bytes = self.tempstore.getvalue()
        return self.bytes
    
    def getUnicode(self):
        if self.isUnicode():
            try:
                bytes = self.getBytes()
                unicodestring = bytes.decode(self.encoding)
                assert self.dprint("unicodestring(%s) = %s bytes" % (type(unicodestring), len(unicodestring)))
                return unicodestring
            except UnicodeDecodeError, e:
                raise UnicodeDecodeError("bad encoding %s:" % self.encoding)
    
    def getBinaryBytesForStyledTextCtrl(self):
        bytes = self.getBytes()
        styledtxt = '\0'.join(bytes)+'\0'
        return styledtxt
