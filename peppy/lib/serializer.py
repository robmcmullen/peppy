# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Utilities to serialize objects

"""

import os


class PickleSerializerMixin(object):
    """Utility class to serialize an object's interesting data
    
    This mixin class implements the framework to save and restore data
    to a file.  It requires at least three methods to be defined in
    the subclassing object:
    
    C{unpackVersion[version_identifier]}
    C{createVersion[version_identifier]}
    C{packVersion[version_identifier]}
    
    The version identifier must be an integer; for example a simple example
    would be C{unpackVersion1}, C{packVersion1}, and C{createVersion1}.
    
    If multiple versions of the saved data format are used, then conversion
    methods must also be specified.  Conversion methods are defined as:
    
    C{convertVersion[version_id1]ToVersion[version_id2]}
    
    Upon loading an old version the version number of the old version will be
    compared to the default version.  If the default version is higher, the
    conversion methods will be called to transform the data from the format
    of the old version to the format of the new version.  Conversions may
    be cascaded, so that moving to version 1 to version 3 would call, in
    succession: convertVersion1ToVersion2 and convertVersion2ToVersion3
    """
    def __init__(self, default_version=1):
        self._ps_default_version = default_version
        self._ps_restored = False
    
    def getSerializedFilename(self):
        """Construct and return the filename to be used to store the pickled
        data.
        
        @return: full path for pickle file
        """
        raise NotImplementedError
    
    def loadStateFromFile(self, filename=None):
        """Load pickle file and restore the instance attributes
        
        The main driver method to restore the class from serialized storage.
        This method calls L{getSerializedFilename} to get the filename
        that contains the pickled data, load the raw data, and calls the
        appropriate unpackVersion* method to restore the instance state.
        
        The createVersion* methods provide a hook for the subclass to define
        default values when the pickled data doesn't exist.  If C{filename}
        isn't found, the method L{createVersion[default_version]} is called,
        where the value used for C{default_version} is the default version
        passed to the constructor.
        
        @kwarg filename: alternate filename for pickled data
        
        @raises RuntimeError: if incorrect filename used or unknown packing
        version is discovered in pickled data
        
        @raises IOError: if problem reading the pickle file
        """
        import cPickle as pickle
        
        if filename is None:
            filename = self.getSerializedFilename()
        if filename is None:
            raise RuntimeError("Serialized filename must be specified")
        
        if os.path.exists(filename):
            fh = open(filename, "rb")
            bytes = fh.read()
            fh.close()
            if bytes:
                version, data = pickle.loads(bytes)
                unpack_method = "unpackVersion%s" % version
                if hasattr(self, unpack_method):
                    unpacker = getattr(self, unpack_method)
                    unpacker(data)
                else:
                    raise RuntimeError("Unknown version %s found when trying to restore from %s" % (version, filename))
                self._ps_restored = True
                
                while version < self._ps_default_version:
                    convert_method = "convertVersion%sToVersion%s" % (version, version+1)
                    if hasattr(self, convert_method):
                        convert = getattr(self, convert_method)
                        convert()
                        version += 1
                    else:
                        raise RuntimeError("Missing converter from version %s to version %s when trying to restore from %s" % (version, version+1, filename))
                        
        else:
            create_method = "createVersion%s" % self._ps_default_version
            create = getattr(self, create_method)
            create()
    
    def saveStateToFile(self, filename=None, version=None):
        """Save the instance attributes in a pickle file
        
        The main driver method to save the instance data to serialized storage.
        This method calls L{getSerializedFilename} to get the filename that
        will contain the pickled data, converts the instance state to a set of
        data through the appropriate packVersion* method, and pickles the data
        to the file.
        
        @kwarg filename: alternate filename for pickled data
        
        @kwarg version: alternate version to be used when creating the set
        of data
        
        @raises RuntimeError: if incorrect filename used or unknown packing
        version is discovered in pickled data
        
        @raises IOError: if problem writing the pickle file
        """
        import cPickle as pickle
        
        if filename is None:
            filename = self.getSerializedFilename()
        if filename is None:
            raise RuntimeError("Serialized filename must be specified")
        
        if version is None:
            version = self._ps_default_version
        if version is None:
            raise RuntimeError("Serializer version must be declared")
        pack_method = "packVersion%s" % version
        if hasattr(self, pack_method):
            packer = getattr(self, pack_method)
            data = packer()
        else:
            raise RuntimeError("Unknown version %s attempting to pack data in %s" % (version, filename))
        packable = (version, data)
        bytes = pickle.dumps(packable)
        fh = open(filename, "wb")
        try:
            fh.write(bytes)
        except IOError: # can fail on win32 on network drive when write is large
            fh.close()
            fh = open(filename, "wb")
            for start in range(0, len(bytes), 100000):
                end = min(start + 100000, len(bytes))
                fh.write(bytes[start:end])
        fh.close()
