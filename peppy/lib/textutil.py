# peppy Copyright (c) 2006-2008 Rob McMullen
# This file is licenced under the same terms as Python itself
"""Utility functions for operating on text

These text utilities have no dependencies on any other part of peppy, and
therefore may be used independently of peppy.
"""
import re

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
        match=re.search(r'-\*\-\s*(mode:\s*(.+?)|(.+?))(\s*;\s*(.+?))?\s*-\*-',line)
        if match:
            vars={}
            varstring=match.group(5)
            if varstring:
                try:
                    for nameval in varstring.split(';'):
                        s=nameval.strip()
                        if s:
                            name,val=s.split(':')
                            vars[name.strip()]=val.strip()
                except:
                    pass
            if match.group(2):
                return (match.group(2),vars)
            elif match.group(3):
                return (match.group(3),vars)
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
