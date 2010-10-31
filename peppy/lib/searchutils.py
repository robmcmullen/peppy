# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Utilities and classes used to search for matches in files
"""

import os, time, fnmatch, heapq, re

import peppy.vfs as vfs
from peppy.debug import *

class AbstractSearchMethod(object):
    def __init__(self, mode):
        self.mode = mode
        self.ui = None
    
    def isValid(self):
        return False
    
    def getErrorString(self):
        raise NotImplementedError
    
    def getPrefix(self):
        return ""
    
    def iterFilesInDir(self, dirname, ignorer):
        # Nice algorithm from http://pinard.progiciels-bpi.ca/notes/Away_from_os.path.walk.html
        stack = [dirname]
        while stack:
            directory = heapq.heappop(stack)
            for base in os.listdir(directory):
                if not ignorer(base):
                    name = os.path.join(directory, base)
                    if os.path.isdir(name):
                        if not os.path.islink(name):
                            heapq.heappush(stack, name)
                    else:
                        yield name
    
    def iterFiles(self, ignorer):
        raise NotImplementedError

    def getMatchGenerator(self, url, matcher):
        if isinstance(url, vfs.Reference):
            if url.scheme != "file":
                dprint("vfs not threadsafe; skipping %s" % unicode(url).encode("utf-8"))
                return
            url = unicode(url.path).encode("utf-8")
        try:
            fh = open(url, "rb")
            return matcher.iterMatches(url, fh)
        except:
            dprint("Failed opening %s" % url)
        return iter([])
    
    def getUI(self, parent):
        raise NotImplementedError
    
    def setUIDefaults(self):
        raise NotImplementedError
    

class AbstractStringMatcher(object):
    """Base class for string matching.
    
    The L{match} method must be defined in subclasses to return True if
    the line matches the criteria offered by the subclass.
    """
    def __init__(self, string):
        self.string = string
    
    def iterMatches(self, url, fh):
        """Iterator for lines in a file, calling L{match} on each line and
        yielding a L{SearchResult} if match is found.
        
        """
        try:
            index = 0
            for line in fh:
                line = line.rstrip("\r\n")
                for start, end, chunk in self.iterLine(line):
                    result = SearchResult(url, index + 1, line)
                    yield result
                    # FIXME: until the UI can display multiple matches per
                    # line, only the first hit on the line is returned
                    break
                index += 1
        except UnicodeDecodeError:
            pass
        finally:
            fh.close()
    
    def iterLine(self, line):
        if self.match(line):
            yield 0, len(line), line
    
    def isValid(self):
        return bool(self.string)
    
    def getErrorString(self):
        if len(self.string) == 0:
            return "Search error: search string is blank"
        return "Search error: invalid search string"

class ExactStringMatcher(AbstractStringMatcher):
    def match(self, line):
        return self.string in line

class IgnoreCaseStringMatcher(ExactStringMatcher):
    def __init__(self, string):
        self.string = string.lower()
    
    def match(self, line):
        return self.string in line.lower()

class RegexStringMatcher(AbstractStringMatcher):
    def __init__(self, string, match_case):
        self.string = string
        try:
            if not match_case:
                flags = re.IGNORECASE
            else:
                flags = 0
            self.cre = re.compile(string, flags)
            self.error = ""
        except re.error, errmsg:
            self.cre = None
            self.error = errmsg
        self.last_match = None
    
    def match(self, line):
        self.last_match = self.cre.search(line)
        return self.last_match is not None
    
    def isValid(self):
        return bool(self.string) and bool(self.cre)
    
    def getErrorString(self):
        if len(self.string) == 0:
            return "Search error: search string is blank"
        return "Regular expression error: %s" % self.error


class AbstractSearchType(object):
    def __init__(self, mode):
        self.mode = mode
        self.ui = None
    
    def getName(self):
        raise NotImplementedError
    
    def getUI(self, parent):
        raise NotImplementedError
    
    def setUIDefaults(self):
        pass

    def getStringMatcher(self, search_text):
        raise NotImplementedError


class WildcardListIgnorer(object):
    def __init__(self, string):
        self.patterns = string.split(";")
    
    def __call__(self, filename):
        for pat in self.patterns:
            if fnmatch.fnmatchcase(filename, pat):
                return True
        return False


class SearchResult(object):
    def __init__(self, url, line, text):
        self.short = unicode(url)
        self.url = url
        self.line = line
        try:
            self.text = unicode(text)
        except UnicodeDecodeError:
            try:
                self.text = unicode(text.decode("utf-8"))
            except:
                self.text = repr(text)
    
    def checkPrefix(self, prefix):
        if self.url.startswith(prefix):
            self.short = unicode(self.url[len(prefix):])
