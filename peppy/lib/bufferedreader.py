#-----------------------------------------------------------------------------
# Name:        bufferedreader.py
# Purpose:     buffering a streamed file
#
# Author:      Rob McMullen
#
# Created:     2007
# RCS-ID:      $Id: $
# Copyright:   (c) 2007 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""Buffered reading utilities.

BufferedReader allows a streamed file to be accessed like a
random-access file by buffering the first n bytes in memory.
"""

class BufferedReplacementReader(object):
    """Buffered file-like object wrapper that replaces the first n
    bytes of the file with the specified buffer.  The remainder of the
    file is unchanged."""
    def __init__(self, fh, buffer):
        self.fh = fh
        self.buffer = buffer
        self.len = len(buffer)
        self.pos = 0
        self.debug = False

        # set real file position to end of replacement buffer
        try:
            self.fh.seek(self.len)
            self.seekable = True
        except:
            # It may not throw an IOError, so rather than guessing
            # what sort of error does show up, just assume that on any
            # error it's not seekable
            self.seekable = False

    def seek(self, pos, whence=0):
        if whence == 1:
            pos += self.pos
        elif whence == 2:
            if self.seekable:
                self.fh.seek(pos, 2)
                pos = self.fh.tell()
            else:
                raise IOError("File not seekable from the end")

        if pos != self.pos:
            if pos <= self.len:
                self.pos = pos
                if self.seekable:
                    # position real file at end of buffer in case next
                    # read crosses the buffer boundary
                    self.fh.seek(self.len)
            elif self.seekable:
                self.pos = pos
                self.fh.seek(pos)
            else:
                raise IOError("File not seekable after initial %d bytes" % self.len)

    def tell(self):
        return self.pos

    def read(self, size=None):
        if self.pos>=self.len:
            # the read request is safely outside the buffer,  so just
            # call the wrapped reader.
            if size is None:
                txt=self.fh.read()
            else:
                txt=self.fh.read(size)
        else:
            # potentially crosses the border
            if size is None:
                # definitely crosses the border
                txt=self.buffer[self.pos:self.len]+self.fh.read()
            else:
                end=self.pos+size
                if end>self.len:
                    txt=self.buffer[self.pos:self.len]+self.fh.read(end-self.len)
                else:
                    txt=self.buffer[self.pos:end]
        self.pos+=len(txt)
        if self.debug: print "read %s from %d (%s)" % (size, self.pos, repr(txt))
        return txt

    def close(self):
        self.fh.close()
        self.fh = None


class BufferedReader(BufferedReplacementReader):
    """Buffered file-like object wrapper that reads the first n bytes
    of the file so that it can be re-read using the standard seek/tell
    idioms.  The remainder of the file is unchanged."""
    def __init__(self,  fh,  num_bytes):
        buffer = fh.read(num_bytes)
        BufferedReplacementReader.__init__(self, fh, buffer)


class WindowReader(object):
    """File-like object wrapper that restricts file read operations to a window
    region within the file.
    
    The window subset is specified by an offset and a length within the
    containing file.
    """
    def __init__(self, fh, offset, length):
        self.fh = fh
        self.offset = offset
        self.len = length
        self.pos = 0
        self.debug = False

        # set real file position to start of the window region
        try:
            self.fh.seek(self.offset)
            self.seekable = True
        except:
            # It may not throw an IOError, so rather than guessing
            # what sort of error does show up, just assume that on any
            # error it's not seekable
            self.fh.read(self.offset)
            self.seekable = False

    def seek(self, pos, whence=0):
        if whence == 1:
            pos += self.pos
        elif whence == 2:
            if self.seekable:
                self.fh.seek(pos, 2)
                pos = self.fh.tell() - self.offset
            else:
                raise IOError("File not seekable from the end")

        if pos != self.pos:
            if pos > self.len:
                pos = self.len
            if self.seekable:
                self.pos = pos
                self.fh.seek(self.offset + self.pos)
            else:
                raise IOError("File not seekable.")

    def tell(self):
        return self.pos

    def read(self, size=None):
        if size is None:
            size = self.len - self.pos
        if size + self.pos > self.len:
            size = self.len - self.pos
        txt=self.fh.read(size)
        self.pos+=len(txt)
        if self.debug: print "WindowReader: read %s from %d (%s)" % (size, self.pos, repr(txt))
        return txt

    def close(self):
        self.fh.close()
        self.fh = None
