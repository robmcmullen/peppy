# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Match data to major modes that can edit that data

"""

import os

import peppy.vfs as vfs

from peppy.lib.textutil import *

from peppy.debug import *
from peppy.editra import *
from peppy.yapsy.plugins import *


class IgnoreMajorMode(RuntimeError):
    """Raise this exception within one of the MajorMode verify classmethods to
    skip further processing of the major mode in matching operations
    """ 
    pass

class MajorModeMatcherDriver(debugmixin):
    current_modes = []
    skipped_modes = set()
    
    # This list holds all major modes that aren't defined in a plugin
    global_major_modes = []
    
    @classmethod
    def addGlobalMajorMode(cls, mode):
        """Inform the major mode matcher about a MajorMode that isn't in
        a plugin
        
        Most major modes are defined in plugins; but certain special modes are
        defined globally.  They must be added using this method.
        """
        if mode not in cls.global_major_modes:
            cls.global_major_modes.append(mode)
    
    @classmethod
    def getMajorModesCompatibleWithMode(cls, mode):
        """Get a list of major mode classes that are compatible with the given
        major mode.
        
        Compatible means that they can successfully be viewed by that major
        mode.  Currently, this means that they share a common STC class,
        but this is not necessarily going to remain this way.  It might be
        possible in the future to change STCs when changing modes.
        """
        buffer = mode.buffer
        stc_class = buffer.stc.__class__
        assert cls.dprint("stc_class=%s" % stc_class)
        modes = cls.getMajorModesCompatibleWithSTCClass(stc_class)

        modes.sort(key=lambda s:s.keyword.lower())
        assert cls.dprint(modes)
        return modes
    
    @classmethod
    def getMajorModesCompatibleWithSTCClass(cls, stc_class):
        plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
        modes = [m for m in cls.global_major_modes if m.verifyCompatibleSTC(stc_class)]
        for plugin in plugins:
            # Only display those modes that use the same type of STC as the
            # current mode.
            modes.extend([m for m in plugin.getMajorModes() if m.verifyCompatibleSTC(stc_class)])
            compatible = plugin.getCompatibleMajorModes(stc_class)
            if compatible is not None:
                modes.extend(compatible)
        cls.dprint("%s: compatible modes = %s" % (stc_class, str(modes)))
        return modes

    @classmethod
    def findActiveModes(cls, plugins=None):
        """Returns the list of currently active major modes in most specific
        mode to most general mode order.
        
        Major modes have a hierarchy based on their subclass order.  For
        example, L{FundamentalMode} is more general than L{PythonMode}
        because PythonMode is subclassed from FundamentalMode.  It makes
        sense, then, to start the subclass searching from the more specific
        PythonMode because PythonMode should return a positive match before
        FundamentalMode.
        """
        if plugins is None:
            plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
            
        subclasses_of = {}
        for plugin in plugins:
            if cls.debuglevel > 1: cls.dprint("checking plugin %s" % str(plugin.__class__.__mro__))
            modes = plugin.getMajorModes()
            for mode in modes:
                mro = mode.getSubclassHierarchy()
                # The method resolution order returns the class as mro[0], so
                # we really want the parent class at mro[1].  This will always
                # work because MajorMode is guaranteed to be a subclass of
                # the mode, so there will always be at least two entries in
                # this list.
                first_parent_class = mro[1]
                if first_parent_class not in subclasses_of:
                    subclasses_of[first_parent_class] = [mode]
                else:
                    subclasses_of[first_parent_class].append(mode)
        
        subclass_order = subclasses_of.keys()
        # subclass_order might also have modes that are subclasses of other
        # modes, so we need to sort this so that the subclasses come before
        # their parents.  For example, FundamentalMode will appear as a key in
        # subclass_order.  If PythonMode had a subclass, say PythonExtraMode,
        # then PythonMode would also appear in subclass_order.  In this case,
        # we need to make sure that PythonMode's subclasses appear before
        # FundamentalMode's subclasses so that PythonExtraMode has a chance to
        # match before PythonMode.
        def sort_subclasses(a, b):
            if a == b:
                return 0
            elif issubclass(a, b):
                return -1
            return 1
        subclass_order.sort(cmp = sort_subclasses)
        
        active_modes = []
        found = {}
        for parent in subclass_order:
            for mode in subclasses_of[parent]:
                if mode not in found:
                    active_modes.append(mode)
                    found[mode] = True
            if parent not in found:
                active_modes.append(parent)
                found[parent] = True
        
        return active_modes
    
    @classmethod
    def findAndCacheActiveModes(cls, plugins):
        """Uses L{findActiveModes} to cache the list of currently active major
        modes
        """
        cls.current_modes = cls.findActiveModes(plugins)
        cls.dprint("Currently active major modes: %s" % str(cls.current_modes))
        cls.skipped_modes = set()
    
    @classmethod
    def iterActiveModes(cls):
        for mode in cls.current_modes:
            if mode not in cls.skipped_modes:
                yield mode
    
    @classmethod
    def ignoreMode(cls, mode):
        cls.dprint("Ignoring mode %s" % mode)
        cls.skipped_modes.add(mode)
    
    @classmethod
    def matchKeyword(cls, keyword, buffer, url=None):
        """Search the list of active major modes for the mode named by the
        specified keyword.
        
        @param keyword: text string matched against the 'keyword' class
        attribute of the major mode
        
        @return: class of the matched major mode, or None if not found
        """
        app = wx.GetApp()
        plugins = app.plugin_manager.getActivePluginObjects()
        cls.findAndCacheActiveModes(plugins)
        for mode in cls.iterActiveModes():
            if mode.verifyKeyword(keyword):
                return mode
        
        if not url:
            url = buffer.raw_url
        # As a last resort to open a specific mode, attempt to open it
        # with any third-party openers that have been registered
        mode = cls.attemptOpen(plugins, buffer, url)
        cls.dprint("attemptOpen matches %s" % mode)
        if mode and mode.verifyKeyword(keyword):
            return mode
        return None

    @classmethod
    def match(cls, buffer, magic_size=None, url=None, header=None):
        if url is None:
            url = buffer.raw_url

        if vfs.is_folder(url):
            mode = cls.matchFolder(buffer, url)
        else:
            mode = cls.matchFile(buffer, magic_size, url, header)
        
        return mode
    
    @classmethod
    def matchFolder(cls, buffer, url=None):
        app = wx.GetApp()
        plugins = app.plugin_manager.getActivePluginObjects()
        cls.findAndCacheActiveModes(plugins)
        
        # Try to match a specific protocol
        modes = cls.scanProtocol(url)
        cls.dprint("scanProtocol matches %s" % modes)
        if modes:
            return modes[0]
        
        # ok, it's not a specific protocol.  Try to match a url pattern and
        # generate a list of possible modes
        metadata = cls.getFailsafeMetadata(url)
        modes, generic_modes = cls.scanFolderURL(url, metadata)
        cls.dprint("scanFolderURL matches %s (generic: %s) using metadata %s" % (modes, generic_modes, metadata))
        if modes:
            return modes[0]
        
        # Try the special case where a mode could be opened using a rewritten
        # URL
        mode, rewritten = cls.scanOpenWithRewrittenURL(url)
        if mode:
            buffer.raw_url = rewritten
            return mode
        
        # As a last resort to open a specific mode, attempt to open it
        # with any third-party openers that have been registered
        mode = cls.attemptOpen(plugins, buffer, url)
        cls.dprint("attemptOpen matches %s" % mode)
        if mode:
            return mode
        
        if generic_modes:
            return generic_modes[0]
        
        raise RuntimeError("No mode matches mimetype inode/directory!  Directory viewing will not be possible!")

    @classmethod
    def matchFile(cls, buffer, magic_size=None, url=None, header=None):
        app = wx.GetApp()
        if magic_size is None:
            magic_size = app.classprefs.magic_size
        
        plugins = app.plugin_manager.getActivePluginObjects()
        cls.findAndCacheActiveModes(plugins)
        
        # Try to match a specific protocol
        modes = cls.scanProtocol(url)
        cls.dprint("scanProtocol matches %s" % modes)
        if modes:
            return modes[0]

        # ok, it's not a specific protocol.  Try to match a url pattern and
        # generate a list of possible modes
        metadata = cls.getFailsafeMetadata(url)
        modes, text_modes, binary_modes = cls.scanFileURL(url, metadata)
        cls.dprint("scanFileURL matches %s (text: %s) (binary: %s) using metadata %s" % (modes, text_modes, binary_modes, metadata))

        if header is None:
            # get a buffered file handle to examine some bytes in the file
            fh = buffer.getBufferedReader(magic_size)
            if not fh:
                # ok, the file doesn't exist, meaning that we're creating a new
                # file.  Return the best guess we have based on filename only.
                if modes:
                    return modes[0]
                else:
                    return cls.findModeByMimetype("text/plain")
            header = fh.read(magic_size)

        url_match = None
        if modes:
            # OK, there is a match with the filenames.  Determine the
            # capability of the mode to edit the file by attempting to match
            # the language keywords in the file
            likely = cls.scanLanguage(header, modes)
            if likely:
                return likely[0]

            # If language keywords are inconclusive, try identification by
            # magic bytes in the file
            capable = [m.verifyMagic(header) for m in modes]
            cm = zip(capable, modes)

            # If there's an exact match, make a note of it
            for c, m in cm:
                if c is not None and c:
                    url_match = m
                    break

            if url_match is None:
                # if there's an acceptable one, make a note of it
                for c, m in cm:
                    if c is None:
                        url_match = m
                        break

        # Regardless if there's a match on the URL, try to match an
        # emacs mode specifier since a match here means that we should
        # override the match based on filename
        emacs_match = cls.scanEmacs(header)
        cls.dprint("scanEmacs matches %s" % emacs_match)
        if emacs_match:
            return emacs_match

        # Like the emacs match, a match on a shell bangpath should
        # override anything determined out of the filename
        bang_match = cls.scanShell(header)
        cls.dprint("scanShell matches %s" % bang_match)
        if bang_match:
            return bang_match

        # Try to match some magic bytes that identify the file
        modes = cls.scanMagic(header)
        cls.dprint("scanMagic matches %s" % modes)
        if modes:
            # It is unlikely that multiple modes will match the same magic
            # values, so just load the first one that we find
            return modes[0]

        # Now we get to the filename match above: if there had been a
        # match on a filename but nothing more specific, we can return
        # it because we've exhausted the other checks
        if url_match:
            cls.dprint("url matches %s" % url_match)
            return url_match

        # Try the special case where a mode could be opened using a rewritten
        # URL
        mode, rewritten = cls.scanOpenWithRewrittenURL(url)
        if mode:
            buffer.raw_url = rewritten
            return mode

        # As a last resort to open a specific mode, attempt to open it
        # with any third-party openers that have been registered
        mode = cls.attemptOpen(plugins, buffer, url)
        cls.dprint("attemptOpen matches %s" % mode)
        if mode:
            return mode

        # If we fail all the tests, use a generic mode
        if guessBinary(header, app.classprefs.binary_percentage):
            if binary_modes:
                # FIXME: needs to be a better way to select which mode to use
                # if there are multiple application/octet-stream viewers
                return binary_modes[0]
        
        if text_modes:
            return text_modes[0]
        
        raise RuntimeError("No mode matches mimetype text/plain!  This is bad, because the editor is not functional if it can't edit text!")
    
    @classmethod
    def getFailsafeMetadata(cls, url):
        try:
            metadata = vfs.get_metadata(url)
        except Exception, e:
            import traceback
            error = traceback.format_exc()
            dprint(error)
            metadata = {'mimetype': None,
                        'mtime': None,
                        'size': 0,
                        'description': None,
                        }
        cls.dprint("%s: metadata=%s" % (unicode(url), unicode(metadata)))
        return metadata

    @classmethod
    def findModeByMimetype(cls, mimetype):
        for mode in cls.iterActiveModes():
            cls.dprint("searching %s" % mode.keyword)
            if mode.verifyMimetype(mimetype):
                return mode
        return None

    @classmethod
    def scanProtocol(cls, url):
        """Scan for url protocol match.
        
        Determine if the protocol is enough to specify the major mode.
        This generally happens only when the major mode is a client of
        a specific server and not a generic editor.  (E.g. MPDMode)

        @param url: vfs.Reference object to scan
        
        @returns: list of matching L{MajorMode} subclasses
        """
        
        modes = []
        for mode in cls.iterActiveModes():
            try:
                if mode.verifyProtocol(url):
                    modes.append(mode)
            except IgnoreMajorMode:
                cls.ignoreMode(mode)
        return modes

    @classmethod
    def scanOpenWithRewrittenURL(cls, url):
        """Scan for a major mode that can open the url by rewriting it
        
        These are for very rare matches where a file could also be opened
        another way if the url scheme was changed.  This can be used, for
        instance, if a file could also be a virtual directory as a zip or
        tar file.

        @param url: vfs.Reference object to scan
        
        @returns: 2-tuple containing the major mode and the rewritten URL.  If
        no modes match, returns (None, None)
        """
        for mode in cls.iterActiveModes():
            try:
                rewritten = mode.verifyOpenWithRewrittenURL(url)
                if rewritten:
                    return mode, rewritten
            except IgnoreMajorMode:
                pass
        return None, None

    @classmethod
    def scanFolderURL(cls, url, metadata):
        """Scan for url folder match.
        
        Determine if the pathname matches some pattern that can
        identify the corresponding major mode.

        @param url: vfs.Reference object to scan
        
        @returns: 2-tuple containing a list of major modes that are designed
        to edit the data pointed to by the URL, and a list of modes compatible
        with inode/directory or x-directory/normal that can edit it.
        """
        modes = []
        generics = []
        
        mimetype = metadata['mimetype']
        for mode in cls.iterActiveModes():
            try:
                if mode.verifyMimetype(mimetype):
                    if mimetype == 'inode/directory' or mimetype == 'x-directory/normal':
                        generics.append(mode)
                    else:
                        modes.append(mode)
                elif mode.verifyMetadata(metadata):
                    modes.append(mode)
                elif mode.verifyMimetype("inode/directory") or mode.verifyMimetype("x-directory/normal"):
                    generics.append(mode)
            except IgnoreMajorMode:
                cls.ignoreMode(mode)
        return modes, generics

    @classmethod
    def scanFileURL(cls, url, metadata):
        """Scan for url filename match.
        
        Determine if the pathname matches some pattern that can
        identify the corresponding major mode.

        @param url: vfs.Reference object to scan
        
        @returns: 3-tuple containing a list of major modes that are designed
        to edit the data pointed to by the URL, a list of modes compatible
        with text/plain that can edit it, and a list of modes compatibly with
        application/octet-stream that can edit it.
        """
        
        modes = []
        generics = []
        
        # Anything that matches application/octet-stream is a generic mode, so
        # save it for last.
        binary = []
        binary_generics = []
        
        mimetype = metadata['mimetype']
        for mode in cls.iterActiveModes():
            try:
                if mode.verifyMimetype(mimetype):
                    if mimetype == 'application/octet-stream':
                        binary.append(mode)
                    else:
                        modes.append(mode)
                elif mode.verifyMetadata(metadata):
                    modes.append(mode)
                elif mode.verifyFilename(url.path.get_name()):
                    modes.append(mode)
                elif mode.verifyMimetype("application/octet-stream"):
                    binary_generics.append(mode)
                elif mode.verifyMimetype("text/plain"):
                    generics.append(mode)
            except IgnoreMajorMode:
                cls.ignoreMode(mode)
        binary.extend(binary_generics)
        return modes, generics, binary

    @classmethod
    def scanMagic(cls, header):
        """Scan for a pattern match in the first bytes of the file.
        
        Determine if there is a 'magic' pattern in the first n bytes
        of the file that can associate it with a major mode.

        @param header: first n bytes of the file
        
        @returns: list of matching L{MajorMode} subclasses
        """
        
        modes = []
        for mode in cls.iterActiveModes():
            try:
                if mode.verifyMagic(header):
                    modes.append(mode)
            except IgnoreMajorMode:
                cls.ignoreMode(mode)
        return modes

    @classmethod
    def scanLanguage(cls, header, modes):
        """Scan for a pattern match in the first bytes of the file.
        
        Determine if there is a 'magic' pattern in the first n bytes
        of the file that can associate it with a major mode.

        @param header: first n bytes of the file
        
        @returns: list of matching L{MajorMode} subclasses
        """
        
        likely = []
        encoding, bom = detectEncoding(header)
        if encoding:
            dprint(encoding)
            header = encodedBytesToUnicode(header, encoding, bom)
        for mode in modes:
            if hasattr(mode, 'verifyLanguage'):
                how_likely = mode.verifyLanguage(header)
                cls.dprint("%s: %d" % (mode, how_likely))
                if how_likely > 0:
                    likely.append((how_likely, mode))
        if likely:
            cls.dprint("Found multiple likely modes: %s" % str(likely))
            likely.sort()
            likely.reverse()
            likely = [entry[1] for entry in likely]
        cls.dprint("modes: %s" % str(likely))
        return likely

    @classmethod
    def scanEmacs(cls, header):
        """Scan the first two lines of a file for an emacs mode
        specifier.
        
        Determine if an emacs mode specifier in the file can be
        associated with a major mode.

        @param header: first n bytes of the file
        
        @returns: matching L{MajorMode} subclass or None
        """
        
        modename, settings = parseEmacs(header)
        cls.dprint("modename = %s, settings = %s" % (modename, settings))
        for mode in cls.iterActiveModes():
            if mode.verifyKeyword(modename):
                return mode
        return None
        
    @classmethod
    def scanShell(cls, header):
        """Scan the first lines of a file for a shell 'bangpath'
        specifier.
        
        Determine if a shell bangpath in the file can be associated
        with a major mode.

        @param header: first n bytes of the file
        
        @returns: matching L{MajorMode} subclass or None
        """
        
        if header.startswith("#!"):
            lines = header.splitlines()
            bangpath = lines[0].lower()
            for mode in cls.iterActiveModes():
                keyword = mode.keyword.lower()

                # only match words that are bounded by some sort
                # of non-word delimiter.  For instance, if the
                # mode is "test", it will match "/usr/bin/test" or
                # "/usr/bin/test.exe" or "/usr/bin/env test", but
                # not /usr/bin/testing or /usr/bin/attested
                regex = r'[\W]%s([\W]|$)' % re.escape(keyword)
                match=re.search(regex, bangpath)
                if match:
                    return mode
        return None
    
    @classmethod
    def attemptOpen(cls, plugins, buffer, url):
        """Use the mode's attemptOpen method to see if it recognizes the url.
        
        @param buffer: Buffer object to scan
        
        @returns: matching L{MajorMode} subclass or None
        """
        modes = []
        for plugin in plugins:
            try:
                exact, generics = plugin.attemptOpen(buffer, url)
                if exact:
                    return exact
                modes.extend(generics)
            except ImportError:
                # plugin tried to load a module that didn't exist
                pass
            except:
                # some other error
                import traceback
                error = traceback.format_exc()
                dprint("Some non-import related error attempting to open from plugin %s\n:%s" % (str(plugin), error))
        if modes:
            return modes[0]
        return None
