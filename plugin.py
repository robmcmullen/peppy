"""
Central repository for the main set of plugins for peppy.
"""

import os,re

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
    
    def getReader(self):
        return NotImplementedError
    
    def getWriter(self):
        return NotImplementedError
    
    def getSTC(self,parent):
        return MySTC(parent)


class MajorModeMatch(object):
    """
    Return type of a L{IMajorModeMatcher} when a successful match is
    made.  In addition of the View class, any name/value pairs
    specific to this file can be passed back to the caller, as well as
    an indicator if the match is exact or generic.

    """
    
    def __init__(self,view,generic=False,exact=True,editable=True):
        self.view=view
        self.vars={}
        if generic:
            self.exact=False
        else:
            self.exact=True
        self.editable=True


class IMajorModeMatcher(Interface):
    """
    Interface that
    L{MajorModeMatcherDriver<views.MajorModeMatcherDriver>} uses to
    determine if a View represented by this plugin is capable of
    viewing the data in the buffer.  (Note that one IMajorModeMatcher
    may represent more than one View.)  Several methods are used in an
    attempt to pick the best match for the data in the buffer.

    First, if the first non-blank line in the buffer (or second line
    if the first contains the shell string C{#!}) contains the emacs
    mode, the L{scanEmacs} method will be called to see if your plugin
    recognizes the emacs major mode string within the C{-*-} delimiters.

    Secondly, if the first line starts with C{#!}, the rest of the line
    is passed to L{scanShell} method to see if it looks like an shell
    command.

    If neither of these methods return a View, then the user hasn't
    explicitly named the view, so we need to determine which View to
    use based on either the filename or by scanning the contents.

    The first of the subsequent search methods is also the simplest:
    L{scanFilename}.  If a pattern (typically the filename extension)
    is recognized, that view is used.

    Next in order, L{scanMagic} is called to see if some pattern in
    the text can be used to identify the file type.
    """

    def scanEmacs(emacsmode,vars):
        """
        This method is called if the first non-blank line in the
        buffer (or second line if the first contains the shell string
        C{#!}) contains an emacs major mode specifier.  Emacs
        recognizes a string in the form of::

          -*-C++-*-
          -*- mode: Python; -*-
          -*- mode: Ksh; var1:value1; var3:value9; -*-
      
        The text within the delimiters is parsed by the
        L{MajorModeMatcherDriver<views.MajorModeMatcherDriver>}, and
        two parameters are passed to this method.  The emacs mode
        string is passed in as C{emacsmode}, and any name/value pairs
        are passed in the C{vars} dict (which could be empty).  It is
        not required that your plugin understand and process the
        variables.

        If your plugin recognizes the emacs major mode string, return
        a L{MajorModeMatch} object that contains the View class.
        Otherwise, return None and the
        L{MajorModeMatcherDriver<views.MajorModeMatcherDriver>} will
        continue processing.

        @param emacsmode: text string of the Emacs major mode
        @type emacsmode: string
        @param vars: name:value pairs, can be the empty list
        @type vars: list
        """

    def scanShell(bangpath):
        """
        Called if the first line starts with the system shell string
        C{#!}.  The remaining characters from the first line are
        passed in as C{bangpath}.

        If your plugin recognizes something in the shell string,
        return a L{MajorModeMatch} object that contains the View class and
        the L{MajorModeMatcherDriver<views.MajorModeMatcherDriver>}
        will stop looking and use than View.  If not, return None and
        the L{MajorModeMatcherDriver<views.MajorModeMatcherDriver>}
        will continue processing.

        @param bangpath: characters after the C{#!}
        @type bangpath: string
        """

    def scanFilename(filename):
        """
        Called to see if a pattern in the filename can be identified
        that determines the file type and therefore the
        L{View<views.View>} that should be used.

        If your plugin recognizes something, return a L{MajorModeMatch}
        object with the optional indicators filled in.  If not, return
        None and the
        L{MajorModeMatcherDriver<views.MajorModeMatcherDriver>} will
        continue processing.

        @param filename: filename, can be in URL form
        @type filename: string
        """
    
    def scanMagic(buffer):
        """
        Called to see if a pattern in the text can be identified that
        determines the file type and therefore the L{View<views.View>}
        that should be used.

        If your plugin recognizes something, return a L{MajorModeMatch}
        object with the optional indicators filled in.  If not, return
        None and the
        L{MajorModeMatcherDriver<views.MajorModeMatcherDriver>} will
        continue processing.

        @param buffer: buffer of already loaded file
        @type buffer: L{Buffer<buffers.Buffer>}
        """

class MajorModeMatcherBase(Component):
    """
    Simple do-nothing base class for L{IMajorModeMatcher}
    implementations so that you don't have to provide null methods for
    scans you don't want to implement.

    @see: L{IMajorModeMatcher} for the interface description

    @see: L{FundamentalPlugin<fundamental.FundamentalPlugin>} or
    L{PythonPlugin} for examples.
    """
    def scanEmacs(self,emacsmode,vars):
        return None

    def scanShell(self,bangpath):
        return None

    def scanFilename(self,filename):
        return None
    
    def scanMagic(self,buffer):
        return None
    


if __name__ == "__main__":
    pass

