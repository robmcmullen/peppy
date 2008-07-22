# peppy Copyright (c) 2006-2008 Rob McMullen
# This file is licenced under the same terms as Python itself
"""Utility functions for operating on text

These text utilities have no dependencies on any other part of peppy, and
therefore may be used independently of peppy.
"""
import re
import emacsutil

def piglatin(text):
    """Translate string to pig latin.
    
    Simple pig latin translator that properly capitalizes the resulting string,
    and skips over any leading or trailing non-alphabetic characters.
    """
    words = []
    for w in text.split():
        # Find non alphabetic chars at the start and skip them
        i=0
        while not w[i].isalpha():
            i += 1
        start = w[0:i]
        w = w[i:]
        
        if w[0] in 'aeiouAEIOU':
            prefix = w
            suffix = 'way'
        else:
            if w[0].isupper():
                prefix = w[1:].capitalize()
                suffix = w[0].lower() + 'ay'
            else:
                prefix = w[1:]
                suffix = w[0].lower() + 'ay'
        
        # Move any trailing non-alphabetic characters to the end
        i = len(prefix) - 1
        while i >= 0 and not prefix[i].isalpha():
            i -= 1
        end = prefix[i + 1:]
        prefix = prefix[0:i + 1]
        
        word = start + prefix + suffix + end
        #print "preprefix=%s, prefix=%s, suffix=%s, word=%s" % (preprefix, prefix, suffix, word)
        words.append(word)
    return u' '.join(words)

def getMagicComments(bytes, headersize=1024):
    """Given a byte string, get the first two lines.
    
    "Magic comments" appear in the first two lines of the file, and can
    indicate the encoding of the file or the major mode in which the file
    should be interpreted.
    """
    numbytes = len(bytes)
    if headersize > numbytes:
        headersize = numbytes
    header = bytes[0:headersize]
    lines = header.splitlines()
    return lines[0:2]

def detectEncoding(bytes):
    """Search for "magic comments" that specify the encoding
    """
    lines = getMagicComments(bytes)
    regex = re.compile("coding[:=]\s*([-\w.]+)")
    for txt in lines:
        match = regex.search(txt)
        if match:
            #print("Found encoding %s" % match.group(1))
            return match.group(1)
    return None

def parseEmacs(header):
    """Determine if the header specifies a major mode.
    
    Parse a potential emacs major mode specifier line into the
    mode and the optional variables.  The mode may appears as any
    of::

      -*-C++-*-
      -*- mode: Python; -*-
      -*- mode: Ksh; var1:value1; var3:value9; -*-

    @param header: first x bytes of the file to be loaded
    @return: two-tuple of the mode and a dict of the name/value pairs.
    @rtype: tuple
    """
    lines = getMagicComments(header)
    for line in lines:
        mode, vars = emacsutil.parseModeline(line)
        if mode:
            return mode, vars
    return None, None

def guessBinary(text, percentage):
    """Guess if this is a text or binary file.
    
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
    if detectEncoding(text):
        # The presence of an encoding by definition indicates a text file, so
        # therefore not binary!
        return False
    data = [ord(i) for i in text]
    binary=0
    for ch in data:
        if (ch<8) or (ch>13 and ch<32) or (ch>126):
            binary+=1
    if binary>(len(text)/percentage):
        return True
    return False


def guessSpacesPerIndent(text):
    """Guess the number of spaces per indent level
    
    Takes from the SciTE source file SciTEBase::DiscoverIndentSetting
    """
    tabsizes = [0]*9
    indent = 0 # current line indentation
    previndent = 0 # previous line indentation
    prevsize = -1 # previous line tab size
    newline = True
    for c in text:
        if c == '\n' or c == '\r':
            newline = True
            indent = 0
        elif newline:
            if c == ' ':
                indent += 1
            else:
                if indent:
                    if indent == previndent and prevsize >= 0:
                        tabsizes[prevsize] += 1
                    elif indent > previndent and previndent >= 0:
                        if indent - previndent <= 8:
                            prevsize = indent - previndent
                            tabsizes[prevsize] += 1
                        else:
                            prevsize = -1
                    previndent = indent
                elif c == '\t':
                    tabsizes[0] += 1
                newline = False
    
    # find maximum non-zero indent
    index = -1
    for i, size in enumerate(tabsizes):
        if size > 0 and (index == -1 or size > tabsizes[index]):
            index = i
    
    return index


if __name__ == "__main__":
    import sys
    
    for file in sys.argv[1:]:
        fh = open(file)
        text = fh.read()
        print "file=%s, tabsize=%d" % (file, guessSpacesPerIndent(text))
