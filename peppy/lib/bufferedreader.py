# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
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
        except IOError:
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


class BufferedReader(BufferedReplacementReader):
    """Buffered file-like object wrapper that reads the first n bytes
    of the file so that it can be re-read using the standard seek/tell
    idioms.  The remainder of the file is unchanged."""
    def __init__(self,  fh,  num_bytes):
        buffer = fh.read(num_bytes)
        BufferedReplacementReader.__init__(self, fh, buffer)
