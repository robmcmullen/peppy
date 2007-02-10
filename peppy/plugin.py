# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Central repository for the main set of plugins for peppy.
"""

import os,re

from configprefs import *
from stcinterface import MySTC
from trac.core import *

class ProtocolPlugin(Interface):
    """Interface for IO plugins.  A plugin that implements this
    interface takes a URL in the form of protocol://path/to/some/file
    and implements two methods that return a file-like object that can
    be used to either read from or write to the datastore that is
    pointed to by the URL.  Some protocols, like http, will typically
    be read-only, which means the getWriter method may be omitted from
    the plugin."""

    def supportedProtocols():
        """Return a list of protocols that this interface supports,
        i.e. a http protocol class would return ['http'] or
        potentially ['http','https'] if it also http over SSL."""
        
    def getReader(filename):
        """Returns a file-like object that can be used to read the
        data using the given protocol."""

    def getWriter(filename):
        """Returns a file-like object that can be used to write the
        data using the given protocol."""

    def getSTC(parent):
        """
        Get an STC instance that supports this protocol.
        """

class ProtocolPluginBase(Component):
    def supportedProtocels(self):
        return NotImplementedError
    
    def getReader(self,filename):
        return NotImplementedError
    
    def getWriter(self,filename):
        return NotImplementedError
    
    def getSTC(self,parent):
        return MySTC(parent)



class IConfigurationExtender(Interface):
    """
    Used to add new configuration ophiotn to the application.
    """

    def loadConf(app):
        """
        Load some configuration settings, possibly from an external
        source like a file.  This is called after the application has
        loaded all the plugins and the main configuration file.
        """

    def saveConf(app):
        """
        Save configuration settings, possibly to an external file.
        This is called before the main configuration file is written,
        so additions to it are possible.
        """

class ConfigurationExtender(Component):
    extensions=ExtensionPoint(IConfigurationExtender)

    def load(self,app):
        for ext in self.extensions:
            ext.loadConf(app)

    def save(self,app):
        for ext in self.extensions:
            ext.saveConf(app)


class IBufferOpenPostHook(Interface):
    """
    Used to add new hook after a buffer has been successfully opened
    and the data read in..
    """

    def openPostHook(buffer):
        """
        Method to manipulate the buffer after the buffer has been
        loaded.
        """


class IFramePluginProvider(Interface):
    """
    Add a frame plugin to a new frame.
    """

    def getFramePlugins():
        """
        Return iterator containing list of frame plugins.
        """

class FramePlugin(ClassSettingsMixin):
    """
    Base class for all frame plugins.  A frame plugin is generally
    used to create a new UI window in a frame that is outside the
    purview of the major mode.  It is a constant regardless of which
    major mode is selected.
    """
    keyword=None

    def __init__(self, frame):
        ClassSettingsMixin.__init__(self)
        self.frame=frame
        if self.keyword is None:
            raise ValueError("keyword class attribute must be defined.")

        self.setup()

        self.createWindows(self.frame)
        
    def setup(self):
        pass

    def createWindows(self,parent):
        pass




if __name__ == "__main__":
    pass

