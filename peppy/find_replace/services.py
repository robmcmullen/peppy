# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Find services for the find and replace plugin

This module includes the various default find services that can be used by
the find and replace actions.  The L{FindService}s define how the find and
replace actions interact with the major mode.  Each find service can provide
its own matching scheme; for example the basic L{FindService} searches for
exact matches in character strings, while the L{FindRegexService} includes a
complete regular expression find and replace capability.
"""
import os, glob, re

import wx
import wx.stc

from peppy.debug import *

class ReplacementError(Exception):
    pass


class FindSettings(debugmixin):
    def __init__(self, match_case=False, smart_case=True, whole_word=False):
        self.match_case = match_case
        self.smart_case = smart_case
        self.whole_word = whole_word
        self.find = ''
        self.find_user = ''
        self.replace = ''
        self.replace_user = ''
        self.first_found = -1
        self.wrapped = False
    
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
    backward = "Find backward"
    
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
        self.flags = 0
        
        text = self.settings.find       
        if text != text.lower():
            match_case = True
        else:
            match_case = self.settings.match_case
        
        if match_case:
            self.flags |= wx.stc.STC_FIND_MATCHCASE
        
        if self.settings.whole_word:
            self.flags |= wx.stc.STC_FIND_WHOLEWORD
    
    def getFlags(self, user_flags=0):
        needs_reset = False
        if self.settings.match_case != self.stc.locals.case_sensitive_search:
            self.settings.match_case = self.stc.locals.case_sensitive_search
            needs_reset = True
        if self.settings.whole_word != self.stc.locals.whole_word_search:
            self.settings.whole_word = self.stc.locals.whole_word_search
            needs_reset = True
        if needs_reset:
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
    
    def resetFirstFound(self):
        self.settings.first_found = -1
        self.settings.wrapped = False
    
    def setWrapped(self, state=True):
        self.settings.wrapped = state
        
    def isWrapped(self):
        return self.settings.wrapped
        
    def getFirstFound(self):
        return self.settings.first_found
    
    def isEntireDocumentChecked(self, pos, direction=1):
        #dprint("first=%d, current=%d, wrapped=%s" % (self.settings.first_found, pos, self.settings.wrapped))
        return self.settings.wrapped and pos == self.settings.first_found
        
    def getReplacement(self, replacing):
        """Return the string that will be substituted in the text
        
        @param replacing: the original string from the document
        @return: the string after the substitutions have been made
        """
        findTxt = self.settings.find
        replaceTxt = self.settings.replace
        
        # in order to use smart casing, both the find and replace strings
        # must be lower case and the target string needs to have at least one
        # alphabetic character.  If the target converted to upper case is the
        # same as the target converted to lower case, we know that it doesn't
        # have any alphabetic chars in it so we punt and use the replace
        # string as is.
        if self.settings.smart_case and findTxt.lower() == findTxt and replaceTxt.lower() == replaceTxt and replacing.upper() != replacing.lower():
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
        
        if pos >=0 and self.settings.first_found == -1:
            self.settings.first_found = pos
            
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
        
        if pos >=0 and self.settings.first_found == -1:
            self.settings.first_found = pos
        
        return pos, start

    def hasMatch(self):
        """Return True if the service currently has a match.
        
        This is used by the GUI to find if replacement is allowed in the text.
        """
        return self.stc.GetSelectionStart() != self.stc.GetSelectionEnd()

    def doReplace(self):
        """Replace the selection
        
        Replace the current selection in the stc with the replacement text
        """
        sel = self.stc.GetSelection()
        replacing = self.stc.GetTextRange(sel[0], sel[1])
        start = min(sel)
        end = max(sel)

        replacement = self.getReplacement(replacing)
        
        self.stc.ReplaceSelection(replacement)
        self.updateSelection(start, end, start, start + len(replacement.encode('utf-8')))
    
    def updateSelection(self, orig_start, orig_end, start, end):
        """Update the selection after replacement and adjust the starting
        point for the initial search
        
        @param orig_start: originally matched text starting position
        @param orig_end: originally matched text ending position
        @param start: replacement text starting position
        @param end: replacement text ending position
        """
        self.stc.SetSelection(start, end)
        if start < self.settings.first_found:
            self.settings.first_found += (end - start) - (orig_end - orig_start)
        


class FindBasicRegexService(FindService):
    forward = "Find Scintilla regex"
    
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
        start = min(sel)
        end = max(sel)
        self.stc.SetTargetStart(start)
        self.stc.SetTargetEnd(end)
        self.stc.SetSearchFlags(self.flags)
        #dprint("target = %d - %d" % (sel[0], sel[1]))
        count = self.stc.ReplaceTargetRE(self.settings.replace)

        self.updateSelection(start, end, start, start + count)


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
    forward = "Find wildcard"
    
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
    forward = "Find regex"

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
            self.flags |= re.IGNORECASE
        
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
            self.shadow_length = len(self.shadow)
            self.shadow_equiv_pos = 0
            self.stc_equiv_start = start
            self.stc_equiv_pos = start
            self.stc_next_offset = 0

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
        
        # Start of this round of searching occurs at the stc_equiv_pos, i.e.
        # the end of the last search
        start = self.stc_equiv_pos
        
        if self.stc_next_offset > 0:
            self.shadow_equiv_pos += 1
            self.stc_equiv_pos += self.stc_next_offset
        
        # Added check here to make sure that stc_next_offset doesn't push us
        # past the end of the search text.
        if self.shadow_equiv_pos > self.shadow_length:
            return -1, start

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
            
            if count == 0:
                # We've found a match, but it translates into zero characters.
                # We need to advance the pointer so the next search starts
                # from the next character but the matched text itself still
                # must show zero characters.  But, we can't change the
                # equiv_start and equiv_pos because any replacement depends on
                # their position.
                if match.start(0) == self.shadow_length:
                    # off the end! force the next attempt at matching to return
                    # the end of search indicator
                    self.stc_next_offset = 1
                else:
                    self.stc_next_offset = len(self.shadow[match.start(0)].encode('utf-8'))
            else:
                self.stc_next_offset = 0
            self.shadow_equiv_pos = match.end(0)
            
            #dprint("match=%s shadow: (%d-%d) equiv=%d, stc: (%d-%d) equiv=%d" % (match.group(0), match.start(0), match.end(0), self.shadow_equiv_pos, pos, pos+count, self.stc_equiv_pos))
            self.stc.SetSelection(self.stc_equiv_start, self.stc_equiv_pos)
        
        else:
            pos = -1
        
        if pos >=0 and self.settings.first_found == -1:
            self.settings.first_found = pos            
        
        return pos, start

    def hasMatch(self):
        """Return True if the service currently has a match.
        
        This is used by the GUI to find if replacement is allowed in the text.
        """
        return (self.stc_next_offset and (self.shadow_equiv_pos <= self.shadow_length)) or (self.stc.GetSelectionStart() != self.stc.GetSelectionEnd())
    
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
                        if value:
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
        orig_start, orig_end = self.stc_equiv_start, self.stc_equiv_pos
        
        # The stc equivalent position must be adjusted for the difference in
        # numbers of bytes, not numbers of characters.
        self.stc_equiv_pos += len(replacement.encode('utf-8')) - len(replacing.encode('utf-8'))
        self.stc.ReplaceTarget(replacement)
        self.updateSelection(orig_start, orig_end, self.stc_equiv_start, self.stc_equiv_pos)

