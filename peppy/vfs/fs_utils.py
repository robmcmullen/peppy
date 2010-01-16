# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
from StringIO import StringIO


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
            #debug: dprint(repr(data))
            if isinstance(data, unicode):
                data = data.encode('utf8')
            self.callback(self.ref, data)

    def __del__(self):
        if not self._is_closed:
            self._close()
            self._is_closed = True
