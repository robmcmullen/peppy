# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, re, time

import wx
import wx.stc
from wx.lib.pubsub import Publisher

from cStringIO import StringIO

import peppy.vfs as vfs

from peppy.debug import *
from peppy.stcinterface import *
from peppy.lib.textutil import *


# Mimic the primary selection middle mouse paste on non-X11 platforms, but
# unfortunately the primary selection will only be application local
non_x11_primary_selection = None

def GetClipboardText(primary_selection=False):
    global non_x11_primary_selection

    success = False
    if primary_selection:
        if wx.Platform == "__WXGTK__":
            wx.TheClipboard.UsePrimarySelection(primary_selection)
        else:
            #dprint(non_x11_primary_selection)
            return non_x11_primary_selection
    do = wx.TextDataObject()
    if wx.TheClipboard.Open():
        success = wx.TheClipboard.GetData(do)
        wx.TheClipboard.Close()

    if success:
        return do.GetText()
    return None

def SetClipboardText(txt, primary_selection=False):
    global non_x11_primary_selection

    if primary_selection:
        if wx.Platform == "__WXGTK__":
            wx.TheClipboard.UsePrimarySelection(primary_selection)
        else:
            non_x11_primary_selection = txt
            #dprint(non_x11_primary_selection)
            return 1
    do = wx.TextDataObject()
    do.SetText(txt)
    if wx.TheClipboard.Open():
        wx.TheClipboard.SetData(do)
        wx.TheClipboard.Close()
        return 1
    else:
        eprint("Can't open clipboard!")
    return 0


class FoldNode:
    def __init__(self,level,start,end,text,parent=None,styles=[]):
        """Folding node as data for tree item."""
        self.parent     = parent
        self.level      = level
        self.start      = start
        self.end        = end
        self.text       = text
        self.styles     = styles #can be useful for icon detection
        self.children   = []

    def __str__(self):
        return "L%d s%d e%d %s" % (self.level, self.start, self.end, self.text.rstrip())


class PeppyBaseSTC(wx.stc.StyledTextCtrl, STCInterface, debugmixin):
    """The base class used as backend storage for files that fit in memory.
    
    Peppy uses the wx.stc.StyledTextCtrl (abbreviated STC in the peppy
    documentation) to store its files in memory.  Because the STC allows
    multiple views of the same file, we take advantage of this to prevent
    keeping multiple copies of the file for different views.  As described
    in L{MajorMode}, multiple STCs will keep themselves updated when the user
    makes change in another STC.
    
    Note that there is a difference in the STC stored in the L{Buffer} and any
    STCs that are used by the L{FundamentalMode} class.  There will always be
    at least two instances of STCs: one in the buffer that is the main backend
    storage, and the other in the major mode that provides the view.  They
    both point to the same data, but they are kept separate in order that
    major modes (i.e.  the views of the data) can change at will.
    
    This class performs the bookkeeping to keep the STC document pointers up to
    date when a new view is added.
    """
    eol2int = {'\r': wx.stc.STC_EOL_CR,
               '\r\n': wx.stc.STC_EOL_CRLF,
               '\n': wx.stc.STC_EOL_LF,
               }
    int2eol = {wx.stc.STC_EOL_CR: '\r',
               wx.stc.STC_EOL_CRLF: '\r\n',
               wx.stc.STC_EOL_LF: '\n',
               }
    
    def __init__(self, parent, refstc=None, copy=None, **kwargs):
        wx.stc.StyledTextCtrl.__init__(self, parent, -1, pos=(9000,9000), **kwargs)
        self.ClearAll()
        
        if refstc is not None:
            self.refstc = refstc
            self.docptr = self.refstc.docptr
            self.AddRefDocument(self.docptr)
            self.SetDocPointer(self.docptr)
            self.SetCodePage(65001) # set for unicode character display
            self.refstc.addSubordinate(self)
            assert self.dprint("referencing document %s" % self.docptr)
        else:
            self.refstc = self
            self.docptr = self.CreateDocument()
            self.SetDocPointer(self.docptr)
            self.SetCodePage(65001) # set for unicode character display
            self.encoding = None # we don't know the encoding yet
            assert self.dprint("creating new document %s" % self.docptr)
            self.subordinates = []

            # If views can share info among similar classes, that info can be
            # stored here.
            self.stc_classes = []
            self.stc_class_info = {}

            if copy is not None:
                txt = copy.GetStyledText(0,copy.GetTextLength())
                dprint("copying %s from old stc." % repr(txt))
                self.AddStyledText(txt)
        self.maybe_undo_eolmode = None

    def updateSubordinateClasses(self):
        """Update the list of classes viewing this buffer."""
        classes = {}
        for view in self.subordinates:
            classes[view.__class__] = True
        self.stc_classses = classes.keys()
    
    def getSharedClassInfo(self, cls):
        """Get the dict that can be used to store data common to viewers of
        the specified class.
        """
        if cls not in self.refstc.stc_class_info:
            self.refstc.stc_class_info[cls] = {}
        return self.refstc.stc_class_info[cls]

    def addSubordinate(self,otherstc):
        self.subordinates.append(otherstc)
        self.updateSubordinateClasses()

    def removeDocumentView(self):
        """Remove the reference of this view from its parent document"""
        if self.refstc != self:
            self.refstc.subordinates.remove(self)
            self.refstc.updateSubordinateClasses()

    def open(self, buffer, message=None):
        """Open the file from the buffer and read in its contents.
        
        The open method is provided here in the STC and not in the buffer so
        that specialized STCs can provide their own load methods.  So far,
        this is only used in the L{NonResidentSTC} for files that are too
        large to fit in memory.
        """
        fh = buffer.getBufferedReader()
        self.readThreaded(fh, buffer, message)
    
    def readThreaded(self, fh, buffer, message=None):
        self.refstc.tempstore = StringIO()
        if fh:
            # if the file exists, read the contents.
            length = vfs.get_size(buffer.url)
            assert self.dprint("Loading %d bytes" % length)
            chunk = 65536
            if length/chunk > 100:
                chunk *= 4
            self.readFrom(fh, chunk=chunk, length=length, message=message)
        else:
            # FIXME: if we're creating the file, we should allow for a
            # template.  The template will be major-mode dependent, so there
            # will have to be some callback to the major mode
            pass
    
    def openSuccess(self, buffer, headersize=1024, encoding=None):
        bytes = self.tempstore.getvalue()
        numbytes = len(bytes)
        if headersize > numbytes:
            headersize = numbytes
        header = bytes[0:headersize]
        self.detectLineEndings(header)
        
        if encoding:
            self.refstc.encoding = encoding
        if not self.refstc.encoding:
            self.refstc.encoding = detectEncoding(header)
        self.decodeText(bytes)
        assert self.dprint("found encoding = %s" % self.refstc.encoding)
        
        del self.tempstore
    
    def readFrom(self, fh, amount=None, chunk=65536, length=0, message=None):
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
            txt = fh.read(chunk)
            assert self.dprint("reading %d bytes from %s" % (len(txt), fh))

            if len(txt) > 0:
                total += len(txt)
                if message:
                    # Negative value will switch the progress bar to
                    # pulse mode
                    Publisher().sendMessage(message, (total*100)/length)
                
                if isinstance(txt, unicode):
                    # This only seems to happen for unicode files written
                    # to the mem: filesystem, but if it does happen to be
                    # unicode, there's no need to convert the data
                    self.refstc.encoding = "utf-8"
                    self.tempstore.write(unicode.encode('utf-8'))
                else:
                    self.tempstore.write(txt)
            else:
                # stop when we reach the end.  An exception will be
                # handled outside this class
                break
    
    def decodeText(self, bytes):
        """Check for the file encoding and convert in place.
        
        If the encoding is embedded in the file (through emacs "magic
        comments"), change the text from the binary representation into the
        specified encoding.
        """
        if self.refstc.encoding:
            try:
                unicodestring = bytes.decode(self.refstc.encoding)
                assert self.dprint("unicodestring(%s) = %s bytes" % (type(unicodestring), len(unicodestring)))
                self.SetText(unicodestring)
                return
            except UnicodeDecodeError, e:
                assert self.dprint("bad encoding %s:" % self.refstc.encoding)
                self.refstc.badencoding = self.refstc.encoding
                self.refstc.encoding = None
        
        # If there's no encoding or an error in the decoding, stuff the binary
        # bytes in the stc.  The only way to load binary data into scintilla
        # is to convert it to two bytes per character: first byte is the
        # content, 2nd byte is styling (which we set to zero)
        self.SetText('')
        styledtxt = '\0'.join(bytes)+'\0'
        self.AddStyledText(styledtxt)
    
    def prepareEncoding(self):
        """Prepare the file for encoding.
        
        This method provides a short-circuit of the writing process in case the
        encoding is bad.  This is a poor man's way of preventing a zero-length
        file due to a bad encoding, because should this method generate an
        exception, the file will never be opened for writing and therefore
        won't be truncated.
        """
        try:
            txt = self.GetText()
            encoding = detectEncoding(txt)
            if encoding:
                assert self.dprint("found encoding %s" % encoding)
                txt = txt.encode(encoding)
                if encoding != self.refstc.encoding:
                    # If the encoding has changed, update it here
                    self.refstc.encoding = encoding
                    self.decodeText(txt)
            else:
                # Have to use GetStyledText because GetText will truncate the
                # string at the first zero character.
                numchars = self.GetTextLength()
                txt = self.GetStyledText(0, numchars)[0:numchars*2:2]
            
            self.refstc.encoded = txt
        except:
            self.refstc.encoded = None
            raise

    def writeTo(self, fh):
        """Writes a copy of the document to the provided file-like object.
        
        Note that peppy is not currently thread-enabled during file writing.
        """
        txt = self.refstc.encoded
        if txt is None:
            raise IOError("Invalid encoded string -- this should never happen")
        
        #dprint("writing %d bytes to %s" % (len(txt), fh))

        try:
            fh.write(txt)
        finally:
            # clean up temporary encoded version of the text
            self.refstc.encoded = None

    ## Additional functionality
    def checkUndoEOL(self):
        """Check to see if the last change was converting all EOL characters.
        
        The wx.stc.StyledTextCtrl doesn't directly store if the last undo/redo
        was the change in all of the end of line characters, so we have to
        check ourselves.
        """
        # Check to see if the eol mode has changed.
        if self.maybe_undo_eolmode is not None:
            if self.maybe_undo_eolmode['likely']:
                self.detectLineEndings()
                Publisher().sendMessage('resetStatusBar')
            self.maybe_undo_eolmode = None
        
    def Undo(self):
        """Override of base Undo command to add our additional checks."""
        wx.stc.StyledTextCtrl.Undo(self)
        self.checkUndoEOL()
        
    def Redo(self):
        """Override of base Redo command to add our additional checks."""
        wx.stc.StyledTextCtrl.Redo(self)
        self.checkUndoEOL()
        
    def CanEdit(self):
        """PyPE compat"""
        return True

    ## STCInterface additions
    def CanCopy(self):
        return True

    def CanCut(self):
        return True
    
    def SelectAll(self):
        self.SetSelectionStart(0)
        self.SetSelectionEnd(self.GetLength())

    def GetBinaryData(self, start=0, end=-1):
        """Convenience function to get binary data out of the STC.
        
        The only way to get binary data out of the STC is to use the
        GetStyledText method and chop out every other byte.  Using the regular
        GetText method will stop at the first nul character.

        @param start: first text position
        @param end: last text position
        
        @returns: binary data between start and end-1, inclusive (just
        like standard python array slicing)
        """
        if end == -1:
            end = self.GetTextLength()
        return self.GetStyledText(start,end)[::2]

    def GuessBinary(self,amount,percentage):
        """
        Guess if the text in this file is binary or text by scanning
        through the first C{amount} characters in the file and
        checking if some C{percentage} is out of the printable ascii
        range.

        Obviously this is a poor check for unicode files, so this is
        just a bit of a hack.

        @param amount: number of characters to check at the beginning
        of the file

        @type amount: int
        
        @param percentage: percentage of characters that must be in
        the printable ASCII range

        @type percentage: number

        @rtype: boolean
        """
        endpos=self.GetLength()
        if endpos>amount: endpos=amount
        bin=self.GetBinaryData(0,endpos)
        data = [ord(i) for i in bin]
        binary=0
        for ch in data:
            if (ch<8) or (ch>13 and ch<32) or (ch>126):
                binary+=1
        if binary>(endpos/percentage):
            return True
        return False
    
    def GetSelection2(self):
        """Get the current region, but don't return an empty last line if the
        cursor is at column zero of the last line.
        
        The STC seems to make entire line selections by placing the cursor
        on the left margin of the next line, rather than the end of the
        last highlighted line.  This causes any use of GetLineEndPosition
        to use this line with only the cursor to mean a real part of the
        selection, which is never what I indend, at least.  So, this version of
        GetSelection handles this case.
        """
        start, end = self.GetSelection()
        if start == end:
            return start, end
        if self.GetColumn(end) == 0:
            line = self.LineFromPosition(end - 1)
            newend = self.GetLineEndPosition(line)
            # If the new end is still greater than the start, then we'll assume
            # that this is going to work; otherwise, it wouldn't be possible to
            # select only the newline
            if newend > start:
                return start, newend
        return start, end
        
    def GetLineRegion(self):
        """Get current region, extending to current line if no region
        selected.

        If there's a region selected, extend it if necessary to
        encompass full lines.  If no region is selected, create one
        from the current line.
        """
        start, end = self.GetSelection()
        if start == end:
            linestart = lineend = self.GetCurrentLine()
        else:
            linestart = self.LineFromPosition(start)
            lineend = self.LineFromPosition(end - 1)
        
        start -= self.GetColumn(start)
        end = self.GetLineEndPosition(lineend)
        self.SetSelection(start, end)
        return (linestart, lineend)

    def PasteAtColumn(self, paste=None):
        """Paste a rectangular selection at a particular column.
        
        This method inserts a previously cut or copied rectangular selection
        at a column.  If some lines in the STC are too short and end before
        the column, leading spaces are inserted so that the column is pasted
        correctly.
        """
        assert self.dprint("rectangle=%s" % self.SelectionIsRectangle())
        start, end = self.GetSelection()
        assert self.dprint("selection = %d,%d" % (start, end))

        line = self.LineFromPosition(start)
        col = self.GetColumn(start)
        assert self.dprint("line = %d, col=%d" % (line, col))

        if paste is None:
            paste = GetClipboardText()
        self.BeginUndoAction()
        try:
            for insert in paste.splitlines():
                if line >= self.GetLineCount():
                    self.InsertText(self.GetTextLength(), self.getLinesep())
                start = pos = self.PositionFromLine(line)
                last = self.GetLineEndPosition(line)
                
                # FIXME: doesn't work with tabs
                if (pos + col) > last:
                    # need to insert spaces before the rectangular area
                    num = pos + col - last
                    insert = ' '*num + insert
                    pos = last
                else:
                    pos += col
                assert self.dprint("before: (%d,%d) = '%s'" % (start,last,self.GetTextRange(start,last)))
                assert self.dprint("inserting: '%s' at %d" % (insert, pos))
                self.InsertText(pos, insert)
                assert self.dprint("after: (%d,%d) = '%s'" % (start,last+len(insert),self.GetTextRange(start,last+len(insert))))
                line += 1
        finally:
            self.EndUndoAction()

    def detectLineEndings(self, header):
        """Guess which type of line ending is used by the file."""
        def whichLinesep(text):
            # line ending counting function borrowed from PyPE
            crlf_ = text.count('\r\n')
            lf_ = text.count('\n')
            cr_ = text.count('\r')
            mx = max(lf_, cr_)
            if not mx:
                return os.linesep
            elif crlf_ >= mx/2:
                return '\r\n'
            elif lf_ is mx:
                return '\n'
            else:# cr_ is mx:
                return '\r'
        
        linesep = whichLinesep(header)
        mode = self.eol2int[linesep]
        self.SetEOLMode(mode)

    def ConvertEOLs(self, mode):
        wx.stc.StyledTextCtrl.ConvertEOLs(self, mode)
        self.SetEOLMode(mode)

    def getLinesep(self):
        """Get the current line separator character.

        """
        mode = self.GetEOLMode()
        return self.int2eol[mode]
    
    def convertStringEOL(self, text):
        """Convert a string to the target EOL format of this STC"""
        target = self.getLinesep()
        if target == '\r':
            text = text.replace('\r\n', '\r').replace('\n', '\r')
        elif target == '\n':
            text = text.replace('\r\n', '\n').replace('\r', '\n')
        else:
            text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
        return text

    # Styling stuff
    
    def isStyleString(self, style):
        """Is the style a string?
        
        Designed to be overridded by subclasses to map styling info to useful
        status checks.
        """
        return False
    
    def isStyleComment(self, style):
        """Is the style a comment?
        
        Designed to be overridded by subclasses to map styling info to useful
        status checks.
        """
        return False

    def showStyle(self, linenum=None):
        if linenum is None:
            linenum = self.GetCurrentLine()

        linestart = self.PositionFromLine(linenum)

        # actual indention of current line
        ind = self.GetLineIndentation(linenum) # columns
        pos = self.GetLineIndentPosition(linenum) # absolute character position
        
        # folding says this should be the current indention
        fold = self.GetFoldLevel(linenum)&wx.stc.STC_FOLDLEVELNUMBERMASK - wx.stc.STC_FOLDLEVELBASE
        
        # get line without indention
        line = self.GetLine(linenum)
        dprint("linenum=%d fold=%d cursor=%d line=%s" % (linenum, fold, self.GetCurrentPos(), repr(line)))
##        for i in range(len(line)):
##            dprint("  pos=%d char=%s style=%d" % (linestart+i, repr(line[i]), self.GetStyleAt(linestart+i) ))

    def showLine(self, line):
        # expand folding if any
        self.EnsureVisible(line)
        self.GotoLine(line)
        self.ScrollToLine(line + self.LinesOnScreen() - 3)
        self.GotoLine(line)
        self.ScrollToColumn(0)

    # --- line indentation stuff
    
    def GetFoldColumn(self, linenum):
        return self.GetFoldLevel(linenum)&wx.stc.STC_FOLDLEVELNUMBERMASK - wx.stc.STC_FOLDLEVELBASE

    def GetPrevLineIndentation(self, linenum):
        for i in xrange(linenum-1, -1, -1):
            indent = self.GetLineIndentPosition(i)
            last = self.GetLineEndPosition(i)
            if indent<last:
                col = self.GetLineIndentation(i)
                dprint("line=%d indent=%d (col=%d) last=%d" % (i, indent, col, last))
                return col, i
            dprint("all blanks: line=%d indent=%d last=%d" % (i, indent, last))
        return 0, -1

    def GetIndentString(self, ind):
        if self.GetUseTabs():
            return (ind*' ').replace(self.GetTabWidth()*' ', '\t')
        else:
            return ind*' '
            
    ##### Utility methods for modifying the contents of the STC
    def addLinePrefixAndSuffix(self, start, end, prefix='', suffix=''):
        """Add a prefix and/or suffix to the line specified by start and end.

        Method to add characters to the start and end of the line. This is
        typically called within a loop that adds comment characters to the
        line.  start and end are assumed to be the endpoints of the
        current line, so no further checking of the line is necessary.

        @param start: first character in line
        @param end: last character in line before line ending
        @param prefix: optional prefix for the line
        @param suffix: optional suffix for the line

        @returns: new position of last character before line ending
        """
        assert self.dprint("commenting %d - %d: '%s'" % (start, end, self.GetTextRange(start,end)))
        slen = len(prefix)
        self.InsertText(start, prefix)
        end += slen

        elen = len(suffix)
        if elen > 0:
            self.InsertText(end, suffix)
            end += elen
        return end + len(self.getLinesep())

    def removeLinePrefixAndSuffix(self, start, end, prefix='', suffix=''):
        """Remove the specified prefix and suffix of the line.

        Method to remove the specified prefix and suffix characters from the
        line specified by start and end.  If the prefix or suffix doesn't match
        the characters in the line, nothing is removed. This is typically
        called within a loop that adds comment characters to the line.  start
        and end are assumed to be the endpoints of the current line, so no
        further checking of the line is necessary.

        @param start: first character in line
        @param end: last character in line before line ending
        @param prefix: optional prefix for the line
        @param suffix: optional suffix for the line

        @returns: new position of last character before line ending
        """
        assert self.dprint("uncommenting %d - %d: '%s'" % (start, end, self.GetTextRange(start,end)))
        slen = len(prefix)
        if self.GetTextRange(start, start+slen) == prefix:
            self.SetSelection(start, start+slen)
            self.ReplaceSelection("")
            end -= slen

        elen = len(suffix)
        if elen > 0:
            if self.GetTextRange(end-elen, end) == suffix:
                self.SetSelection(end-elen, end)
                self.ReplaceSelection("")
                end -= elen
        return end + len(self.getLinesep())

    def setCommentDelimiters(self, start='', end=''):
        """Set instance-specific comment characters and comment regex
        
        If the instance uses different comment characters that the class
        attributes, set the instance attributes here which will override
        the class attributes.
        
        A regex is created that will match a line with the comment characters.
        The regex returns a 3-tuple of whitespace followed by the opening
        comment character, the body of the line, and then the closing comment
        including any trailing whitespace.  If the language doesn't have a
        closing comment character, the final tuple element will always be
        an empty string.
        
        This is typically called by the Editra stc mixin to set the
        comment characters encoded by the Editra style manager.
        """
        self.start_line_comment = start
        self.end_line_comment = end
        if start:
            if end:
                regex = r"^(\s*(?:%s)*)(.*?)((?:%s)*\s*$)" % ("\\" + "\\".join(start), "\\" + "\\".join(end))
                self.dprint(regex)
                self.comment_regex = re.compile(regex)
            else:
                regex = r"^(\s*(?:%s)*)(.*)($)" % ("\\" + "\\".join(start))
                self.dprint(regex)
                self.comment_regex = re.compile(regex)
        else:
            regex = r"^(\s*)(.*)($)"
            self.dprint(regex)
            self.comment_regex = re.compile(regex)
        
    def commentRegion(self, add=True):
        """Default implementation of block commenting and uncommenting
    
        This class provides the default implementation of block commenting.
        Blocks are commented by adding a comment string at the beginning of
        the line, and an optional comment string at the end of each line in
        the block.
    
        Typically the comment characters are known to the Editra styling system
        and are therefore automatically added to the FundamentalMode subclass
        by a call to L{setCommentDelimiters}.

        @param add: True to add comments, False to remove them
        """
        eol_len = len(self.getLinesep())
        if add:
            func = self.addLinePrefixAndSuffix
        else:
            func = self.removeLinePrefixAndSuffix
        
        self.BeginUndoAction()
        line, lineend = self.GetLineRegion()
        assert self.dprint("lines: %d - %d" % (line, lineend))
        try:
            selstart, selend = self.GetSelection()
            assert self.dprint("selection: %d - %d" % (selstart, selend))

            start = selstart
            end = self.GetLineEndPosition(line)
            while line <= lineend:
                start = func(start, end, self.start_line_comment, self.end_line_comment)
                line += 1
                end = self.GetLineEndPosition(line)
            self.SetSelection(selstart, start - eol_len)
        finally:
            self.EndUndoAction()
            
    def splitCommentLine(self, line):
        """Split the line into the whitespace leader and body of the line.
        
        Return a tuple containing the leading whitespace and comment
        character(s), the body of the line, and any trailing comment
        character(s)
        """
        match = self.comment_regex.match(line)
        if match is None:
            return ("", line, "")
        self.dprint(match.groups())
        return match.group(1, 2, 3)


class PeppySTC(PeppyBaseSTC):
    """Base class used by major modes that use the STC.
    
    This class contains all the GUI callbacks and mouse bindings on top of
    L{PeppyBaseSTC}
    """
    
    def __init__(self, parent, refstc=None, copy=None, **kwargs):
        PeppyBaseSTC.__init__(self, parent, refstc=refstc, copy=copy, **kwargs)

        self.Bind(wx.stc.EVT_STC_DO_DROP, self.OnDoDrop)
        self.Bind(wx.stc.EVT_STC_DRAG_OVER, self.OnDragOver)
        self.Bind(wx.stc.EVT_STC_START_DRAG, self.OnStartDrag)
        self.Bind(wx.stc.EVT_STC_MODIFIED, self.OnModified)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_MIDDLE_UP, self.OnMousePaste)
        self.Bind(wx.EVT_LEFT_UP, self.OnSelectionEnd)

        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

        self.debug_dnd=False

    def sendEvents(self,evt):
        """
        Send an event to all subordinate STCs
        """
        for otherstc in self.subordinates:
            assert self.dprint("sending event %s to %s" % (evt,otherstc))
            wx.PostEvent(otherstc,evt())

    def addUpdateUIEvent(self, callback):
        """Add the equivalent to STC_UPDATEUI event for UI changes.

        The STC supplies the EVT_STC_UPDATEUI event that fires for
        every change that could be used to update the user interface:
        a text change, a style change, or a selection change.  If the
        editing (viewing) window does not use the STC to display
        information, you should supply the equivalent event for the
        edit window.
        
        @param callback: event handler to execute on event
        """
        self.Bind(wx.stc.EVT_STC_UPDATEUI, callback)
        
    def OnDestroy(self, evt):
        """
        Event handler for EVT_WINDOW_DESTROY. Preserve the clipboard
        contents can be preserved after the window is destroyed so
        that other apps can still grab it.

        @param evt: event
        """
        wx.TheClipboard.Flush()
        evt.Skip()

    def OnMouseWheel(self, evt):
        """Handle mouse wheel scrolling.
        """
        mouse = wx.GetApp().mouse
        assert self.dprint("Wheel! delta=%s rotation=%s" % (evt.GetWheelDelta(), evt.GetWheelRotation()))
        if mouse.classprefs.mouse_wheel_scroll_style == 'lines':
            num = mouse.classprefs.mouse_wheel_scroll_lines
        else:
            num = self.LinesOnScreen()
            if mouse.classprefs.mouse_wheel_scroll_style == 'half':
                num /= 2
        if evt.GetWheelRotation() > 0:
            # positive means scrolling up, which is a negative number of lines
            # to scroll
            num = -num
        self.LineScroll(0, num)
        #evt.Skip()
    
    def OnMousePaste(self, evt):
        """Paste the primary selection (on unix) at the mouse cursor location
        
        This currently supports only the primary selection (not the normal
        cut/paste clipboard) from a unix implementation.
        """
        pos = self.PositionFromPoint(wx.Point(evt.GetX(), evt.GetY()))
        #print("x=%d y=%d pos=%d" % (evt.GetX(), evt.GetY(), pos))
        if pos != wx.stc.STC_INVALID_POSITION:
            text = GetClipboardText(True)
            if text:
                text = self.convertStringEOL(text)
                self.InsertText(pos, text)
                self.GotoPos(pos + len(text))

    def OnSelectionEnd(self, evt):
        """Copy the selected region into the primary selection
        
        This currently supports unix only, because it depends on the primary
        selection of the clipboard.
        """
        sel = self.GetSelection()
        #dprint(sel)
        if sel[0] != sel[1]:
            text = self.GetTextRange(sel[0], sel[1])
            SetClipboardText(text, True)
        evt.Skip()

    def OnStartDrag(self, evt):
        assert self.dprint("OnStartDrag: %d, %s\n"
                       % (evt.GetDragAllowMove(), evt.GetDragText()))

        if self.debug_dnd and evt.GetPosition() < 250:
            evt.SetDragAllowMove(False)     # you can prevent moving of text (only copy)
            evt.SetDragText("DRAGGED TEXT") # you can change what is dragged
            #evt.SetDragText("")             # or prevent the drag with empty text


    def OnDragOver(self, evt):
        assert self.dprint(
            "OnDragOver: x,y=(%d, %d)  pos: %d  DragResult: %d\n"
            % (evt.GetX(), evt.GetY(), evt.GetPosition(), evt.GetDragResult())
            )

        if self.debug_dnd and evt.GetPosition() < 250:
            evt.SetDragResult(wx.DragNone)   # prevent dropping at the beginning of the buffer


    def OnDoDrop(self, evt):
        assert self.dprint("OnDoDrop: x,y=(%d, %d)  pos: %d  DragResult: %d\n"
                       "\ttext: %s\n"
                       % (evt.GetX(), evt.GetY(), evt.GetPosition(), evt.GetDragResult(),
                          evt.GetDragText()))

        if self.debug_dnd and evt.GetPosition() < 500:
            evt.SetDragText("DROPPED TEXT")  # Can change text if needed
            #evt.SetDragResult(wx.DragNone)  # Can also change the drag operation, but it
                                             # is probably better to do it in OnDragOver so
                                             # there is visual feedback

            #evt.SetPosition(25)             # Can also change position, but I'm not sure why
                                             # you would want to...




    def OnModified(self, evt):
        # NOTE: on really big insertions, evt.GetText can cause a
        # MemoryError on MSW, so I've commented this dprint out.
        #assert self.dprint("(%s) at %d: text=%s" % (self.transModType(evt.GetModificationType()),evt.GetPosition(), repr(evt.GetText())))

        # Since the stc doesn't store the EOL state as an undoable
        # parameter, we have to check for it.
        mod = evt.GetModificationType()
        if mod & (wx.stc.STC_PERFORMED_UNDO | wx.stc.STC_PERFORMED_REDO) and mod & (wx.stc.STC_MOD_INSERTTEXT | wx.stc.STC_MOD_DELETETEXT):
            text = evt.GetText()
            if self.maybe_undo_eolmode is None:
                self.maybe_undo_eolmode = {'total': 0, 'linesep': 0, 'likely': False}
            stats = self.maybe_undo_eolmode
            stats['total'] += 1
            if text == '\n' or text == '\r':
                self.dprint("found eol char")
                stats['linesep'] += 1
            if mod & wx.stc.STC_LASTSTEPINUNDOREDO:
                self.dprint("eol summary: %s" % stats)
                if stats['linesep'] == stats['total'] and stats['linesep'] >= self.GetLineCount()-1:
                    self.dprint("likely that this is a eol change")
                    stats['likely'] = True
        elif mod & wx.stc.STC_MOD_CHANGEFOLD:
            self.OnFoldChanged(evt)
        evt.Skip()
    
    def OnFoldChanged(self, evt):
        pass

    def OnUpdateUI(self, evt):
        assert self.dprint("(%s) at %d: text=%s" % (self.transModType(evt.GetModificationType()),evt.GetPosition(), repr(evt.GetText())))
        evt.Skip()


    def transModType(self, modType):
        st = ""
        table = [(wx.stc.STC_MOD_INSERTTEXT, "InsertText"),
                 (wx.stc.STC_MOD_DELETETEXT, "DeleteText"),
                 (wx.stc.STC_MOD_CHANGESTYLE, "ChangeStyle"),
                 (wx.stc.STC_MOD_CHANGEFOLD, "ChangeFold"),
                 (wx.stc.STC_PERFORMED_USER, "UserFlag"),
                 (wx.stc.STC_PERFORMED_UNDO, "Undo"),
                 (wx.stc.STC_PERFORMED_REDO, "Redo"),
                 (wx.stc.STC_LASTSTEPINUNDOREDO, "Last-Undo/Redo"),
                 (wx.stc.STC_MOD_CHANGEMARKER, "ChangeMarker"),
                 (wx.stc.STC_MOD_BEFOREINSERT, "B4-Insert"),
                 (wx.stc.STC_MOD_BEFOREDELETE, "B4-Delete")
                 ]

        for flag,text in table:
            if flag & modType:
                st = st + text + " "

        if not st:
            st = 'UNKNOWN'

        return st
