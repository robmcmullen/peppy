# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Some simple text transformation actions.

This plugin is a collection of some simple text transformation actions that
should be applicable to more than one major mode.
"""

import os, glob, re

import wx
import wx.lib.stattext

from peppy.yapsy.plugins import *
from peppy.actions.minibuffer import *

from peppy.about import AddCredit
from peppy.fundamental import FundamentalMode
from peppy.actions import *
from peppy.actions.base import *
from peppy.debug import *

AddCredit("Jan Hudec", "for the shell-style wildcard to regex converter from bzrlib")


class ReplacementError(Exception):
    pass


class FindSettings(debugmixin):
    def __init__(self, match_case=False, smart_case=True):
        self.match_case = match_case
        self.smart_case = smart_case
        self.find = ''
        self.find_user = ''
        self.replace = ''
        self.replace_user = ''
    
    def serialize(self, storage):
        storage['last_search'] = self.find_user
        storage['last_replace'] = self.replace_user

    def unserialize(self, storage):
        if 'last_search' in storage:
            self.find_user = storage['last_search']
        else:
            self.find_user = ''
        if 'last_replace' in storage:
            self.replace_user = storage['last_replace']
        else:
            self.replace_user = ''


class FindService(debugmixin):
    forward = "Find"
    backward = "Find Backward"
    replace = "Replace"
    
    help = """The default find and replace uses literal strings.  No wildcard
    or regular expressions are used to match text."""
    
    def __init__(self, stc, settings=None):
        self.flags = 0
        self.stc = stc
        if settings is None:
            self.settings = FindSettings()
        else:
            self.settings = settings
        
        if self.settings.find_user:
            self.setFindString(self.settings.find_user)
        if self.settings.replace:
            self.setReplaceString(self.settings.replace_user)
    
    def serialize(self, storage):
        self.settings.serialize(storage)
    
    def unserialize(self, storage):
        self.settings.unserialize(storage)
        self.setFindString(self.settings.find_user)
        self.setReplaceString(self.settings.replace_user)
    
    def allowBackward(self):
        return True
    
    def setFlags(self):
        text = self.settings.find
        
        if text != text.lower():
            match_case = True
        else:
            match_case = self.settings.match_case
        
        if match_case:
            self.flags = wx.stc.STC_FIND_MATCHCASE
        else:
            self.flags = 0
    
    def getFlags(self, user_flags=0):
        if self.settings.match_case != self.stc.locals.case_sensitive_search:
            self.settings.match_case = self.stc.locals.case_sensitive_search
            self.setFlags()
        
        return self.flags | user_flags
        
    def expandSearchText(self, findTxt):
        """Convert the search string that the user enters into the string
        actually searched for by the service.
        
        This is designed to be overridden in subclasses, and has most use for
        regular expression searches where the string the user types has to be
        compiled into a form that the regular expression engine uses to search.
        """
        if not findTxt:
            findTxt = ""
            
        return findTxt
    
    def expandReplaceText(self, text):
        """Convert the replacement string that the user enters into the string
        actually searched for by the service.
        
        Like L{expandSearchText}, this is primarily designed to be overridden
        in subclasses.
        """
        return self.expandSearchText(text)
    
    def setFindString(self, text):
        self.settings.find_user = text
        self.settings.find = self.expandSearchText(text)
        self.setFlags()
    
    def setReplaceString(self, text):
        self.settings.replace_user = text
        self.settings.replace = self.expandReplaceText(text)

    def getReplacement(self, replacing):
        """Return the string that will be substituted in the text
        
        @param replacing: the original string from the document
        @return: the string after the substitutions have been made
        """
        replaceTxt = self.settings.replace
        
        if self.settings.smart_case:
            if replacing.upper() == replacing:
                ## print "all upper", replacing
                replaceTxt = replaceTxt.upper()
            elif replacing.lower() == replacing:
                ## print "all lower", replacing
                replaceTxt = replaceTxt.lower()
            elif len(replacing) == len(replaceTxt):
                ## print "smartcasing", replacing
                r = []
                for i,j in zip(replacing, replaceTxt):
                    if i.isupper():
                        r.append(j.upper())
                    elif i.islower():
                        r.append(j.lower())
                    else:
                        r.append(j)
                replaceTxt = ''.join(r)
            elif replacing and replaceTxt and replacing[:1].upper() == replacing[:1]:
                ## print "first upper", replacing
                replaceTxt = replaceTxt[:1].upper() + replaceTxt[1:]
            elif replacing and replaceTxt and replacing[:1].lower() == replacing[:1]:
                ## print "first lower", replacing
                replaceTxt = replaceTxt[:1].lower() + replaceTxt[1:]
        
        return replaceTxt

    def getRange(self, start, chars, dire=1):
        end = start
        if dire==1:
            fcn = self.stc.PositionAfter
        else:
            fcn = self.stc.PositionBefore
        for i in xrange(chars):
            z = fcn(end)
            y = self.stc.GetCharAt(end)
            x = abs(z-end)==2 and (((dire==1) and (y == 13)) or ((dire==0) and (y == 10)))
            ## print y, z-end
            end = z - x
        return start, end
    
    def highlightSelection(self, pos, count):
        sel_start, sel_end = self.getRange(pos, count)
        #dprint("selection = %d - %d" % (sel_start, sel_end))
        self.stc.SetSelection(sel_start, sel_end)
    
    def findMatchLength(self, pos):
        """Scintilla doesn't return the end of the match, so we have to compute
        it ourselves.
        
        This is designed to be overridden in subclasses, particularly by
        subclasses that use regular expressions to match.
        
        This can also be used as a verification method to reject a match.
        Should a subclass need this capability, return a -1 here and the
        L{doFindNext} method will move to the next possible match and try
        again.  This will repeat until a match is found or the end of the
        document is reached.
        
        @return: number of characters matched by the search string, or -1 to
        reject the match.
        """
        count = len(self.settings.find)
        return count
    
    def doFindNext(self, start=-1, incremental=False):
        """Find and highlight the next match in the document.
        
        @param start: starting position in text, or -1 to use current position
        
        @param incremental: True if an incremental search that will be added to
        the current search result
        
        @return: tuple containing the position of the match or -1 if no match
        is found, and the position of the original start of the search.  If
        the search string is invalid, a tuple of (None, None) is returned.
        """
        if not self.settings.find:
            return None, None
        flags = self.getFlags(wx.FR_DOWN)
        
        #handle finding next item, handling wrap-arounds as necessary
        if start < 0:
            sel = self.stc.GetSelection()
            if incremental:
                start = min(sel)
            else:
                start = max(sel)
        
        while True:
            pos = self.stc.FindText(start, self.stc.GetTextLength(), self.settings.find, flags)
            #dprint("start=%d find=%s flags=%d pos=%d" % (start, self.settings.find, flags, pos))
        
            if pos < 0:
                # no match; done.
                break
            
            count = self.findMatchLength(pos)
            if count >= 0:
                self.highlightSelection(pos, count)
                break
            
            start = pos + 1
        
        return pos, start

    def doFindPrev(self, start=-1, incremental=False):
        """Find and highlight the previous match in the document.
        
        @param start: starting position in text, or -1 to use current position
        
        @param incremental: True if an incremental search that will be added to
        the current search result
        
        @return: tuple containing the position of the match or -1 if no match
        is found, and the position of the original start of the search.  If
        the search string is invalid, a tuple of (None, None) is returned.
        """
        if not self.settings.find:
            return None, None
        flags = self.getFlags()
        
        if start < 0:
            sel = self.stc.GetSelection()
            if incremental:
                start = min(sel) + len(self.settings.find)
                #dprint("sel=%s min=%d len=%s" % (str(sel), min(sel), len(self.settings.find)))
            else:
                start = min(sel)
        pos = self.stc.FindText(start, 0, self.settings.find, flags)
        
        if pos >= 0:
            count = self.findMatchLength(pos)
            self.highlightSelection(pos, count)
        
        return pos, start

    def doReplace(self):
        """Replace the selection
        
        Replace the current selection in the stc with the replacement text
        """
        sel = self.stc.GetSelection()
        replacing = self.stc.GetTextRange(sel[0], sel[1])

        replacement = self.getReplacement(replacing)
        
        self.stc.ReplaceSelection(replacement)
        self.stc.SetSelection(min(sel), min(sel) + len(replacement.encode('utf-8')))


class FindBasicRegexService(FindService):
    forward = "Find Scintilla Regex"
    replace = "Replace Scintilla Regex"
    
    help = r"""
    Basic regular expressions are a limited form supported by the scintilla
    editor, not the full python regular expressions.  Scintilla regular
    expressions are limited to:

.	Matches any character
\( 	This marks the start of a region for tagging a match.
\) 	This marks the end of a tagged region.
\n 	Where n is 1 through 9 refers to the first through ninth tagged region when replacing. For example if the search string was Fred\([1-9]\)XXX and the replace string was Sam\1YYY applied to Fred2XXX this would generate Sam2YYY.
\< 	This matches the start of a word using Scintilla's definitions of words.
\> 	This matches the end of a word using Scintilla's definition of words.
\x 	This allows you to use a character x that would otherwise have a special meaning. For example, \[ would be interpreted as [ and not as the start of a character set.
[...] 	This indicates a set of characters, for example [abc] means any of the characters a, b or c. You can also use ranges, for example [a-z] for any lower case character.
[^...] 	The complement of the characters in the set. For example, [^A-Za-z] means any character except an alphabetic character.
^ 	This matches the start of a line (unless used inside a set, see above).
$ 	This matches the end of a line.
* 	This matches 0 or more times. For example Sa*m matches Sm, Sam, Saam, Saaam and so on.
+ 	This matches 1 or more times. For example Sa+m matches Sam, Saam, Saaam and so on."""
    
    def __init__(self, stc, settings=None):
        FindService.__init__(self, stc, settings)
    
    def allowBackward(self):
        return False
    
    def findMatchLength(self, pos):
        """Determine the length of the regular expression match
        """
        line = self.stc.LineFromPosition(pos)
        last = self.stc.GetLineEndPosition(line)
        self.stc.SetTargetStart(pos)
        self.stc.SetTargetEnd(last)
        self.stc.SetSearchFlags(self.flags)
        found = self.stc.SearchInTarget(self.settings.find)
        last = self.stc.GetTargetEnd()
        #dprint("Target: found=%d pos=%d last=%d" % (found, pos, last))
        if found >= 0:
            return last - pos
        return -1
    
    def setFlags(self):
        self.flags = self.getFlags(wx.stc.STC_FIND_REGEXP)
    
    def doReplace(self):
        """Replace the selection
        
        Replace the current selection in the stc with the replacement text
        """
        sel = self.stc.GetSelection()
        self.stc.SetTargetStart(sel[0])
        self.stc.SetTargetEnd(sel[1])
        self.stc.SetSearchFlags(self.flags)
        #dprint("target = %d - %d" % (sel[0], sel[1]))
        count = self.stc.ReplaceTargetRE(self.settings.replace)

        self.stc.SetSelection(min(sel), min(sel) + count)


class FindWildcardService(FindService):
    """Find and replace using shell style wildcards.
    
    Simpler than regular expressions, shell style wildcards allow simple
    search and replace on patterns.  Internally, they are converted to regular
    expressions, but to the user's perspective they are simple, less powerful
    pattern matching.
    
    Replacements can be made using the wildcard characters -- the same set of
    wildcard characters must be given in the replacement string, in the same
    order.  For instance, if the find string is:
    
    blah*blah???blah*
    
    the replacement string should have the wildcards in the same order: '*',
    '?', '?', '?', and '*'.  E.g.:
    
    stuff*stuff?stuff?stuff?stuff*stuff
    """
    forward = "Find Wildcard"
    replace = "Replace Wildcard"
    
    help = """
    Shell-style wildcards are simpler than full regular expressions, but you
    give up some power for the simplicity.  '*' and '?' are the wildcards,
    where '*' matches zero or more non-whitespace characters and '?' matches
    exactly one non-whitespace character.
    
    Wildcards are also allowed in replacement strings, where each wildcard in
    the replacement string will be replaced by the value found in the search
    result matched by the corresponding wildcard character.  For instance, if
    the find string is:
    
    a*b???c*
    
    and finds the match a222b345c678, given the replacement string:
    
    d*e?f?g?h*i
    
    the resulting replacement will be:
    
    d222e3f4g5h678i"""
    
    def findMatchLength(self, pos):
        """Have to convert a scintilla regex to a python one so we can find out
        how many characters the regex matched.
        """
        pyre = self.settings.find.replace(r"\(.*\)", r"([^ \t\n\r]*)").replace(r"\(.\)", r"([^ \t\n\r])")
        
        line = self.stc.LineFromPosition(pos)
        last = self.stc.GetLineEndPosition(line)
        text = self.stc.GetTextRange(pos, last)
        match = re.match(pyre, text, flags=re.IGNORECASE)
        if match:
            #dprint(match.group(0))
            return len(match.group(0))
        #dprint("Not matched!!! pat=%s text=%s pos=%d last=%d" % (pyre, text, pos, last))
        return -1
    
    def setFlags(self):
        self.flags = self.getFlags(wx.stc.STC_FIND_REGEXP)
    
    def expandSearchText(self, text):
        """Convert from shell style wildcards to regular expressions"""
        import peppy.lib.glob
        
        if not text:
            text = ""
        regex = peppy.lib.glob.translate(text)
        #dprint(regex)
        
        return regex

    def expandReplaceText(self, text):
        if not text:
            text = ""
        return text
    
#    def repgroup(self, m):
#        dprint("match=%s span=%s" % (m.group(), str(m.span())))
#        self._group_count += 1
#        return "\\%d" % self._group_count
#
#    def expandReplaceText(self, text):
#        """Convert from shell style wildcards to regular expressions"""
#        import peppy.lib.glob
#        
#        if not text:
#            text = ""
#        regex = peppy.lib.glob.translate(text)
#        dprint(regex)
#        
#        groups = r"([\\][(].+[\\][)])"
#        self._group_count = 0
#        regex = re.sub(groups, self.repgroup, regex)
#        dprint(regex)
#        
#        return regex
    
    def getReplacement(self, replacing):
        """Get the replacement text.
        
        Can't use the built-in scintilla regex replacement method, because
        it seems that scintilla regexs are greedy and ignore the target end
        specified by SetTargetEnd.  So, we have to convert to a python regex
        and replace that way.
        """
        pyre = self.settings.find.replace(r"\(.*\)", r"([^ \t\n\r]*)").replace(r"\(.\)", r"([^ \t\n\r])")
        #dprint("replacing %s: %s, %s" % (replacing, pyre, self.settings.replace))
        matches = re.match(pyre, replacing, flags=re.IGNORECASE)
        if matches and matches.groups():
            groups = matches.groups()
        else:
            groups = []
        #dprint("matches: %s" % str(groups))
        
        output = []
        index = 0
        # replace each wildcard with the corresponding match from the search
        # string
        for c in self.settings.replace:
            if c in '*?':
                if index < len(groups):
                    output.append(groups[index])
                else:
                    output.append("")
                index += 1
            else:
                output.append(c)
        text = "".join(output)
        return text


class FindRegexService(FindService):
    """Find and replace using python regular expressions.
    
    """
    forward = "Find Regex"
    replace = "Replace Regex"

    def __init__(self, *args, **kwargs):
        FindService.__init__(self, *args, **kwargs)
        self.regex = None
        self.shadow = None

    def setFlags(self):
        text = self.settings.find
        
        if text != text.lower():
            match_case = True
        else:
            match_case = self.settings.match_case
        
        self.flags = re.MULTILINE
        if not match_case:
            self.flags = re.IGNORECASE
        
        # Force the next search to start from a new shadow copy of the text
        self.shadow = None
    
    def getFlags(self, user_flags=0):
        if hasattr(self.stc, 'locals') and self.settings.match_case != self.stc.locals.case_sensitive_search:
            self.settings.match_case = self.stc.locals.case_sensitive_search
            self.setFlags()
        
        flags = self.flags | user_flags
        
        try:
            self.regex = re.compile(self.settings.find, flags)
        except re.error:
            self.regex = None
        return flags
    
    def verifyShadow(self, start=-1, incremental=False):
        if self.shadow is None or start >= 0:
            #handle finding next item, handling wrap-arounds as necessary
            if start < 0:
                sel = self.stc.GetSelection()
                if incremental:
                    start = min(sel)
                else:
                    start = max(sel)
            self.shadow = self.stc.GetTextRange(start, self.stc.GetTextLength())
            self.shadow_equiv_pos = 0
            self.stc_equiv_start = start
            self.stc_equiv_pos = start

    def doFindNext(self, start=-1, incremental=False):
        """Find and highlight the next match in the document.
        
        @param start: starting position in text, or -1 to use current position
        
        @param incremental: True if an incremental search that will be added to
        the current search result
        
        @return: tuple of two elements.  The first element is the position of
        the match, -1 if no match, a string indicating that an error occurred.
        The second element is the position of the original start of the
        search.  If the search string is invalid, a tuple of (None, None)
        is returned.
        """
        if not self.settings.find:
            return None, None
        self.getFlags()
        if self.regex is None:
            return _("Incomplete regex"), None
        
        self.verifyShadow(start, incremental)
        
        match = self.regex.search(self.shadow, self.shadow_equiv_pos)
        if match:
            # Because unicode characters are stored as utf-8 in the stc and the
            # positions in the stc correspond to the raw bytes, not the number
            # of unicode characters, we have to find out the offset to the
            # unicode chars in terms of raw bytes.
            pos = self.stc_equiv_pos + len(self.shadow[self.shadow_equiv_pos:match.start(0)].encode('utf-8'))
            count = len(self.shadow[match.start(0):match.end(0)].encode('utf-8'))
            self.stc_equiv_start = pos
            self.stc_equiv_pos = pos + count
            
            self.shadow_equiv_pos = match.end(0)
            
            #dprint("match=%s shadow: (%d-%d) equiv=%d, stc: (%d-%d) equiv=%d" % (match.group(0), match.start(0), match.end(0), self.shadow_equiv_pos, pos, pos+count, self.stc_equiv_pos))
            self.stc.SetSelection(self.stc_equiv_start, self.stc_equiv_pos)
        
        else:
            pos = -1
        
        return pos, start
    
    def getReplacement(self, replacing):
        """Extended regex replacement
        
        This handles extra regex replacement targets, like upper and lower
        casing of targets, that the standard python regular expression matcher
        doesn't include.
        """
        def firstLower(s):
            if len(s) > 1:
                return s[0].lower() + s[1:]
            return s.lower()
        
        def firstUpper(s):
            if len(s) > 1:
                return s[0].upper() + s[1:]
            return s.upper()
        
        def lower(s):
            return s.lower()
        
        def upper(s):
            return s.upper()
        
        match = self.regex.match(replacing)
        if not match:
            # Hmmm.  This should have worked because theoretically we should
            # have been matching a value returned by the same regex.
            return replacing
        self.dprint("matches: %s" % str(match.groups()))
         
        output = []
        next_once = None
        next_until = None
        parts = re.split("(\\\\(?:[0-9]{1,2}|g<[0-9]+>|l|L|u|U|E))", self.settings.replace)
        self.dprint(parts)
        for part in parts:
            if part.startswith("\\"):
                escape = part[1:]
                if escape == "l":
                    next_once = firstLower
                elif escape == "u":
                    next_once = firstUpper
                elif escape == "L":
                    next_until = lower
                elif escape == "U":
                    next_until = upper
                elif escape == "E":
                    next_until = None
                else:
                    try:
                        if escape.startswith("g"):
                            index = int(part[1:])
                            self.dprint("found %s: %d" % (escape, index))
                        else:
                            index = int(part[1:])
                            self.dprint("found index %d" % index)
                        value = match.group(index)
                        if next_once:
                            value = next_once(value)
                            self.dprint("next_once converted to %s" % value)
                            next_once = None
                        elif next_until:
                            value = next_until(value)
                            self.dprint("next_until converted to %s" % value)
                        output.append(value)
                    except ValueError:
                        # not an integer means we just insert the value
                        output.append(part)
                    except IndexError:
                        # no matching group with that index, so put no value in the
                        # output for this match
                        pass
                self.dprint("part=%s: once=%s until=%s" % (part, str(next_once), str(next_until)))
            elif part:
                if next_once:
                    part = next_once(part)
                    self.dprint("converted to %s" % part)
                    next_once = None
                elif next_until:
                    part = next_until(part)
                    self.dprint("converted to %s" % part)
                output.append(part)
        self.dprint("output = %s" % str(output))
        text = "".join(output)
        return text

    def doReplace(self):
        """Replace the selection
        
        Replace the current selection with the regex replacement
        """
        self.verifyShadow()
        
        # We assume that doFindNext has been called, setting up the equivalent
        # start and end positions
        replacing = self.stc.GetTextRange(self.stc_equiv_start, self.stc_equiv_pos)
        replacement = self.getReplacement(replacing)
        
        self.stc.SetTargetStart(self.stc_equiv_start)
        self.stc.SetTargetEnd(self.stc_equiv_pos)
        
        # The stc equivalent position must be adjusted for the difference in
        # numbers of bytes, not numbers of characters.
        self.stc_equiv_pos += len(replacement.encode('utf-8')) - len(replacing.encode('utf-8'))
        self.stc.ReplaceTarget(replacement)
        self.stc.SetSelection(self.stc_equiv_start, self.stc_equiv_pos)

class FindBar(wx.Panel, debugmixin):
    """Find panel customized from PyPE's findbar.py
    
    """
    debuglevel = 0
    
    def __init__(self, parent, frame, stc, storage=None, service=None, direction=1, **kwargs):
        wx.Panel.__init__(self, parent, style=wx.NO_BORDER|wx.TAB_TRAVERSAL)
        self.frame = frame
        self.stc = stc
        if isinstance(storage, dict):
            self.storage = storage
        else:
            self.storage = {}
        self.settings = FindSettings()
        if service:
            self.service = service(self.stc, self.settings)
        else:
            self.service = FindService(self.stc, self.settings)
        
        self.createCtrls()
        
        # PyPE compat
        self._lastcall = None
        self.setDirection(direction)
    
    def createCtrls(self):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.label = wx.StaticText(self, -1, _(self.service.forward) + u":")
        sizer.Add(self.label, 0, wx.CENTER)
        self.find = wx.TextCtrl(self, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER)
        sizer.Add(self.find, 1, wx.EXPAND)
        self.SetSizer(sizer)
        
        self.find.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)
        self.find.Bind(wx.EVT_TEXT, self.OnChar)
    
    def setDirection(self, dir=1):
        if dir > 0:
            self._lastcall = self.OnFindN
            text = self.service.forward
        else:
            self._lastcall = self.OnFindP
            text = self.service.backward
        self.label.SetLabel(_(text) + u":")
        self.Layout()

    def OnChar(self, evt):
        #handle updating the background color
        self.resetColor()

        self.service.setFindString(self.find.GetValue())
        
        #search in whatever direction we were before
        self._lastcall(evt, incremental=True)
        
        evt.Skip()

    def OnEnter(self, evt):
        return self._lastcall(evt)
    
    def OnNotFound(self, msg=None):
        self.find.SetBackgroundColour(wx.RED)
        if msg is None:
            msg = _("Search string was not found.")
        self.frame.SetStatusText(msg)
        self.Refresh()

    def resetColor(self):
        if self.find.GetBackgroundColour() != wx.WHITE:
            self.find.SetBackgroundColour(wx.WHITE)
            self.Refresh()

    def showLine(self, pos, msg):
        self.dprint()
        self.resetColor()
        self.dprint()
        self.frame.SetStatusText(msg)
        self.dprint()
        line = self.stc.LineFromPosition(pos)
        self.dprint()
        if not self.stc.GetLineVisible(line):
            self.stc.EnsureVisible(line)
        self.dprint()
        self.stc.EnsureCaretVisible()
        self.dprint()
    
    def cancel(self, pos_at_end=False):
        self.resetColor()
        self.frame.SetStatusText('')
        if pos_at_end:
            pos = self.stc.GetSelectionEnd()
        else:
            pos = self.stc.GetSelectionStart()
        self.stc.GotoPos(pos)
        self.stc.EnsureCaretVisible()
    
    def OnFindN(self, evt, allow_wrap=True, help='', interactive=True, incremental=False):
        self._lastcall = self.OnFindN
        
        posn, st = self.service.doFindNext(incremental=incremental)
        self.dprint("start=%s pos=%s" % (st, posn))
        if posn is None:
            self.cancel()
            return
        elif not isinstance(posn, int):
            return self.OnNotFound(posn)
        elif posn != -1:
            self.dprint("interactive=%s" % interactive)
            if interactive:
                self.showLine(posn, help)
            self.loop = 0
            return
        
        if allow_wrap and st != 0:
            posn, st = self.service.doFindNext(0)
            self.dprint("wrapped: start=%d pos=%d" % (st, posn))
        self.loop = 1
        
        if posn != -1:
            if interactive:
                self.showLine(posn, "Reached end of document, continued from start.")
            return
        
        self.dprint("not found: start=%d pos=%d" % (st, posn))
        self.OnNotFound()
    
    def OnFindP(self, evt, allow_wrap=True, help='', incremental=False):
        self._lastcall = self.OnFindP
        
        posn, st = self.service.doFindPrev(incremental=incremental)
        if posn != -1:
            self.showLine(posn, help)
            self.loop = 0
            return
        
        if allow_wrap and st != self.stc.GetTextLength():
            posn, st = self.service.doFindPrev(self.stc.GetTextLength())
        self.loop = 1
        
        if posn != -1:
            self.showLine(posn, "Reached start of document, continued from end.")
            return
        
        self.OnNotFound()
    
    def repeatLastUserInput(self):
        """Load the user interface with the last saved user input
        
        @return: True if user input was loaded from the storage space
        """
        if not self.settings.find_user:
            self.service.unserialize(self.storage)
            self.find.ChangeValue(self.settings.find_user)
            self.find.SetInsertionPointEnd()
            return True
        return False

    def repeat(self, direction, service=None):
        self.resetColor()
        if service is not None:
            self.service = service(self.stc, self.settings)
        
        if direction < 0:
            self.setDirection(-1)
        else:
            self.setDirection(1)
        
        if self.repeatLastUserInput():
            return
        
        # replace doesn't use an automatic search, so make sure that a method
        # has been specified before calling it
        if self._lastcall:
            self._lastcall(None)
    
    def saveState(self):
        self.service.serialize(self.storage)


class FindMinibuffer(Minibuffer):
    """
    Adapter for PyPE findbar.  Maps findbar callbacks to our stuff.
    """
    search_storage = {}
    
    def createWindow(self):
        self.win = FindBar(self.mode.wrapper, self.mode.frame, self.mode, self.search_storage, direction=self.action.find_direction, service=self.action.find_service)
    
    def getHelp(self):
        return self.win.service.help

    def repeat(self, action):
        self.win.SetFocus()
        self.win.repeat(action.find_direction, action.find_service)

    def focus(self):
        # When the focus is asked for by the minibuffer driver, set it
        # to the text ctrl or combo box of the pype findbar.
        self.win.find.SetFocus()
    
    def closePreHook(self):
        self.win.saveState()
        self.dprint(self.search_storage)


class FindText(MinibufferRepeatAction):
    name = "Find..."
    tooltip = "Search for a string in the text."
    default_menu = ("Edit", -400)
    icon = "icons/find.png"
    key_bindings = {'default': "C-F", 'emacs': 'C-S', }
    minibuffer = FindMinibuffer
    find_service = FindService
    find_direction = 1

class FindRegex(MinibufferRepeatAction):
    name = "Find Regex..."
    tooltip = "Search for a python regular expression."
    default_menu = ("Edit", 401)
    key_bindings = {'emacs': 'C-S-S', }
    minibuffer = FindMinibuffer
    find_service = FindRegexService
    find_direction = 1

class FindWildcard(MinibufferRepeatAction):
    name = "Find Wildcard..."
    tooltip = "Search using shell-style wildcards."
    default_menu = ("Edit", 402)
    key_bindings = {'emacs': 'C-M-S', }
    minibuffer = FindMinibuffer
    find_service = FindWildcardService
    find_direction = 1

class FindPrevText(MinibufferRepeatAction):
    name = "Find Previous..."
    tooltip = "Search backwards for a string in the text."
    default_menu = ("Edit", 402)
    key_bindings = {'default': "C-S-F", 'emacs': 'C-R', }
    minibuffer = FindMinibuffer
    find_service = FindService
    find_direction = -1




class FakeButton(wx.lib.stattext.GenStaticText):
    """Simple text label that accepts focus.
    
    Used as the key processor for replace.  This label accepts focus but
    doesn't display any indicator that focus has been taken, so it looks like
    an ordinary label.  However, events can be processed through this label
    and it is used to handle the keyboard commands for replacing.
    """
    def AcceptsFocus(self):
        return True

class ReplaceBar(FindBar):
    """Replace panel in the style of the Emacs replace function
    
    The control of the minibuffer is similar to emacs:
    
    Type the search string in 'Replace:' and hit enter.  Type the replacement
    string in 'with:' and hit enter.  Then, use the keyboard to control the
    replacements: 'y' or 'space' to replace one match, 'n' or 'delete' to skip
    to the next match, 'q' to quit, '.' to replace one match and quit, '!' to
    replace all remaining matches', 'p' or '^' to move to the previous match.
    """
    replace = "Replace"
    replace_regex = "Regex Replace"
    help_status = "y: replace, n: skip, q: exit, !:replace all"
    
    def __init__(self, *args, **kwargs):
        FindBar.__init__(self, *args, **kwargs)
        
        if 'on_exit' in kwargs:
            self.on_exit = kwargs['on_exit']
        else:
            self.on_exit = None
        
        # Count of number of replacements
        self.count = 0
        
        # Last cursor position, tracked during replace all
        self.last_cursor = 0
    
    def createCtrls(self):
        text = self.service.replace
        grid = wx.GridBagSizer(0, 0)
        self.label = wx.StaticText(self, -1, _(text) + u":")
        grid.Add(self.label, (0, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        self.find = wx.TextCtrl(self, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER)
        grid.Add(self.find, (0, 1), flag=wx.EXPAND)
        self.replace = wx.TextCtrl(self, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER)
        grid.Add(self.replace, (1, 1), flag=wx.EXPAND)
        
        # Windows doesn't process char events through a real button, so we use
        # this fake button as a label and process events through it.  It's
        # added here so that it will be last in the tab order.
        self.command = FakeButton(self, -1, _("with") + u":")
        grid.Add(self.command, (1, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        
        grid.AddGrowableCol(1)
        self.SetSizer(grid)
        
        self.find.Bind(wx.EVT_TEXT_ENTER, self.OnTabToReplace)
        self.find.Bind(wx.EVT_SET_FOCUS, self.OnFindSetFocus)
        self.replace.Bind(wx.EVT_TEXT_ENTER, self.OnTabToCommand)
        self.replace.Bind(wx.EVT_KILL_FOCUS, self.OnTabToCommand)
        self.replace.Bind(wx.EVT_SET_FOCUS, self.OnReplaceSetFocus)
        self.command.Bind(wx.EVT_BUTTON, self.OnReplace)
        self.command.Bind(wx.EVT_KEY_DOWN, self.OnCommandKeyDown)
        self.command.Bind(wx.EVT_CHAR, self.OnCommandChar)
        self.command.Bind(wx.EVT_SET_FOCUS, self.OnSearchStart)
        self.command.Bind(wx.EVT_KILL_FOCUS, self.OnSearchStop)
    
    def OnReplaceError(self, msg=None):
        self.replace.SetBackgroundColour(wx.RED)
        self.frame.SetStatusText(msg)
        self.Refresh()

    def resetColor(self):
        if self.replace.GetBackgroundColour() != wx.WHITE:
            self.replace.SetBackgroundColour(wx.WHITE)
            self.replace.Refresh()
        FindBar.resetColor(self)

    def setDirection(self, dir=1):
        self.label.SetLabel(_(self.service.replace) + u":")
        self.Layout()

    def OnFindSetFocus(self, evt):
        self.frame.SetStatusText("Enter search text and press Return")
    
    def OnReplaceSetFocus(self, evt):
        self.frame.SetStatusText("Enter replacement text and press Return")
    
    def OnTabToReplace(self, evt):
        self.replace.SetFocus()
    
    def OnTabToCommand(self, evt):
        # Using tab after changing color when a selection exists in
        # self.replace causes the text to appear white on a white background.
        # Force the selection to disappear when tabbing off of self.replace
        self.replace.SetInsertionPointEnd()
        self.command.SetFocus()
    
    def OnSearchStart(self, evt):
        self.service.setFindString(self.find.GetValue())
        self.service.setReplaceString(self.replace.GetValue())
        self.OnFindN(evt, help=self.help_status)
    
    def OnSearchStop(self, evt):
        self.cancel()
        
    def OnReplace(self, evt, find_next=True, interactive=True):
        """Replace the selection
        
        The bulk of this algorithm is from PyPE.
        """
        if self.stc.GetReadOnly():
            return False

        allow_wrap = not interactive
        sel = self.stc.GetSelection()
        if sel[0] == sel[1]:
            if find_next:
                self.OnFindN(None, allow_wrap=allow_wrap, help=self.help_status, interactive=interactive)
            return True
        
        try:
            self.service.doReplace()
            if find_next:
                self.OnFindN(None, allow_wrap=allow_wrap, help=self.help_status, interactive=interactive)
            self.count += 1
                
            return True
        except ReplacementError, e:
            self.OnReplaceError(str(e))
        return False
    
    def OnReplaceAll(self, evt):
        self.count = 0
        self.loop = 0
        self.last_cursor = 0
        
        # FIXME: this takes more time than it should, probably because there's
        # a lot of redundant stuff going on in OnReplace.  This should be
        # rewritten for speed at some point.
        if hasattr(self.stc, 'showBusy'):
            self.stc.showBusy(True)
            wx.Yield()
        self.stc.BeginUndoAction()
        valid = True
        try:
            while self.loop == 0 and valid:
                valid = self.OnReplace(None, interactive=False)
            self.stc.GotoPos(self.last_cursor)
        finally:
            self.stc.EndUndoAction()
        
        if hasattr(self.stc, 'showBusy'):
            self.stc.showBusy(False)
        if valid:
            if self.count == 1:
                occurrences = _("Replaced %d occurrence")
            else:
                occurrences = _("Replaced %d occurrences")
            self.OnExit(msg=_(occurrences) % self.count)
    
    def OnCommandKeyDown(self, evt):
        key = evt.GetKeyCode()
        mods = evt.GetModifiers()
        
        # FIXME: windows doesn't receive the return character, so this code is
        # never reached when the return key is pressed.
        
        #dprint("key=%s mods=%s" % (key, mods))
        if key == wx.WXK_TAB and not mods & (wx.MOD_CMD|wx.MOD_SHIFT|wx.MOD_ALT):
            self.find.SetFocus()
        elif key == wx.WXK_RETURN or key == wx.WXK_DELETE:
            self.OnFindN(None, help=self.help_status)
        else:
            evt.Skip()
    
    def OnCommandChar(self, evt):
        uchar = unichr(evt.GetKeyCode())
        #dprint("uchar = %s" % uchar)
        if uchar in u'nN':
            self.OnFindN(None, help=self.help_status)
        elif uchar in u'yY ':
            self.OnReplace(None)
        elif uchar in u'pP^':
            self.OnFindP(None, help=self.help_status)
        elif uchar in u'qQ':
            self.OnExit()
        elif uchar in u'.':
            self.OnReplace(None, find_next=False)
            self.OnExit()
        elif uchar in u'!':
            self.OnReplaceAll(None)
        else:
            evt.Skip()
    
    def OnExit(self, msg=''):
        self.cancel(pos_at_end=True)
        if msg:
            self.frame.SetStatusText(msg)
        if self.on_exit:
            self.on_exit()

    def repeatLastUserInput(self):
        """Load the user interface with the last saved user input
        
        @return: True if user input was loaded from the storage space
        """
        # disable the repeat search when using the replace buffer
        self._lastcall = None
        
        # Set the focus to the find string to prevent the focus from staying on
        # the command control.  Unless this is done, the focus tends to stay
        # on the command control which highlights the last successful search.
        self.find.SetFocus()
        
        if not self.settings.find_user:
            self.service.unserialize(self.storage)
            self.find.ChangeValue(self.settings.find_user)
            self.find.SetInsertionPointEnd()
            self.replace.ChangeValue(self.settings.replace_user)
            self.replace.SetInsertionPointEnd()
            return True
        return False


class ReplaceMinibuffer(FindMinibuffer):
    """
    Adapter for PyPE findbar.  Maps findbar callbacks to our stuff.
    """
    search_storage = {}
    
    def createWindow(self):
        self.win = ReplaceBar(self.mode.wrapper, self.mode.frame, self.mode,
                              self.search_storage, on_exit=self.removeFromParent,
                              direction=self.action.find_direction,
                              service=self.action.find_service)



class Replace(MinibufferRepeatAction):
    name = "Replace..."
    tooltip = "Replace a string in the text."
    default_menu = ("Edit", 410)
    icon = "icons/text_replace.png"
    key_bindings = {'win': 'C-H', 'emacs': 'F6', }
    minibuffer = ReplaceMinibuffer
    find_service = FindService
    find_direction = 1

class ReplaceRegex(MinibufferRepeatAction):
    name = "Replace Regex..."
    tooltip = "Replace using python regular expressions."
    default_menu = ("Edit", 411)
    key_bindings = {'emacs': 'S-F6', }
    minibuffer = ReplaceMinibuffer
    find_service = FindRegexService
    find_direction = 1

class ReplaceWildcard(MinibufferRepeatAction):
    name = "Replace Wildcard..."
    tooltip = "Replace using shell-style wildcards."
    default_menu = ("Edit", 411)
    key_bindings = {'emacs': 'M-F6', }
    minibuffer = ReplaceMinibuffer
    find_service = FindWildcardService
    find_direction = 1


class CaseSensitiveSearch(ToggleAction):
    """Should search string require match by case"""
    name = "Case Sensitive Search"
    default_menu = ("Edit", 499)
    
    def isChecked(self):
        return self.mode.locals.case_sensitive_search

    def action(self, index=-1, multiplier=1):
        self.mode.locals.case_sensitive_search = not self.mode.locals.case_sensitive_search


class FindReplacePlugin(IPeppyPlugin):
    """Plugin containing of a bunch of cursor movement (i.e. non-destructive)
    actions.
    """

    def getCompatibleActions(self, mode):
        if issubclass(mode.__class__, FundamentalMode):
            return [FindText, FindRegex, FindWildcard, FindPrevText,
                    Replace, ReplaceRegex, ReplaceWildcard,
                    
                    CaseSensitiveSearch,
                    ]
        return []

if __name__ == "__main__":
    import sys
    import __builtin__
    __builtin__._ = str
    
    class Frame(wx.Frame):
        def __init__(self, *args, **kwargs):
            super(self.__class__, self).__init__(*args, **kwargs)

            sizer = wx.BoxSizer(wx.VERTICAL)
            self.stc = wx.stc.StyledTextCtrl(self, -1)
            sizer.Add(self.stc, 1, wx.EXPAND)
            
            self.search = FindBar(self, self, self.stc)
            sizer.Add(self.search, 0, wx.EXPAND)
            
            self.search_back = FindBar(self, self, self.stc, direction=-1)
            sizer.Add(self.search_back, 0, wx.EXPAND)
            
            self.search_regex = FindBar(self, self, self.stc, service=FindBasicRegexService)
            sizer.Add(self.search_regex, 0, wx.EXPAND)
            
            self.replace = ReplaceBar(self, self, self.stc)
            sizer.Add(self.replace, 0, wx.EXPAND)
            
            self.SetSizer(sizer)

            self.CreateStatusBar()
            menubar = wx.MenuBar()
            self.SetMenuBar(menubar)  # Adding the MenuBar to the Frame content.
            menu = wx.Menu()
            menubar.Append(menu, "File")
            self.menuAdd(menu, "Quit", "Exit the pragram", self.OnQuit)
            menu = wx.Menu()
            menubar.Append(menu, "Edit")
            self.menuAdd(menu, "Find Next", "Remove spelling correction indicators", self.OnFind)
            self.doTests()

        def loadSample(self, paragraphs=2):
            lorem_ipsum = u"""\
self
Self
SELF
SeLF
seLF
SeLf

Lorem ipsum dolor sit amet, consectetuer adipiscing elit.  Vivamus mattis
commodo sem.  Phasellus scelerisque tellus id lorem.  Nulla facilisi.
Suspendisse potenti.  Fusce velit odio, scelerisque vel, consequat nec,
dapibus sit amet, tortor.  Vivamus eu turpis.  Nam eget dolor.  Integer
at elit.  Praesent mauris.  Nullam non nulla at nulla tincidunt malesuada.
Phasellus id ante.  Sed mauris.  Integer volutpat nisi non diam.  Etiam
elementum.  Pellentesque interdum justo eu risus.  Cum sociis natoque
penatibus et magnis dis parturient montes, nascetur ridiculus mus.  Nunc
semper.  In semper enim ut odio.  Nulla varius leo commodo elit.  Quisque
condimentum, nisl eget elementum laoreet, mauris turpis elementum felis, ut
accumsan nisl velit et mi.

And some Russian: \u041f\u0438\u0442\u043e\u043d - \u043b\u0443\u0447\u0448\u0438\u0439 \u044f\u0437\u044b\u043a \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f!

"""
            self.stc.ClearAll()
            for i in range(paragraphs):
                self.stc.AppendText(lorem_ipsum)

        def menuAdd(self, menu, name, desc, fcn, id=-1, kind=wx.ITEM_NORMAL):
            if id == -1:
                id = wx.NewId()
            a = wx.MenuItem(menu, id, name, desc, kind)
            menu.AppendItem(a)
            wx.EVT_MENU(self, id, fcn)
            menu.SetHelpString(id, desc)
        
        def OnQuit(self, evt):
            self.Close(True)
        
        def OnFind(self, evt):
            pass
        
        def doTests(self):
            service = FindRegexService(self)
            service.setFindString("(.+) (.+)")
            service.setReplaceString("\\u\\1 \\l\\2 upper=\\U\\1 upper \\2\\E lower=\\L\\1 LoWeR \\2\\E")
            service.getFlags()
            dprint(service.getReplacement("blah STUFF"))
        
    app = wx.App(False)
    frame = Frame(None, size=(-1, 600))
    frame.loadSample()
    frame.Show()
    app.MainLoop()
