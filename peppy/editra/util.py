# Misc utility files from Editra that don't have any other dependencies
import os, sys
import wx
from peppy.debug import *

def GetFileReader(filename):
    try:
        fh = open(filename, 'rb')
        return fh
    except:
        return -1

def GetResourceDir(resource):
    base_dir = os.path.dirname(__file__)
    #dprint(base_dir)
    #dprint(sys.executable)
    if base_dir.find("library.zip") != -1:
        # in a py2exe frozen executable!  Remove the library.zip and use
        # the rest of the path
        base_dir = os.path.normpath(base_dir.replace("library.zip",""))
    rec_dir = os.path.join(base_dir, resource)
    #dprint(rec_dir)
    return rec_dir

def GetResourceFiles(resource, trim=True, get_all=False, title=True):
    """Gets a list of resource files from a directory and trims the
    file extentions from the names if trim is set to True (default).
    If the get_all parameter is set to True the function will return
    a set of unique items by looking up both the user and system level
    files and combining them, the default behavior returns the user
    level files if they exist or the system level files if the
    user ones do not exist.
    @param resource: name of config directory
    @keyword trim: trim file extensions or not
    @keyword get_all: get a set of both system/user files or just user level
    

    """
    rec_dir = GetResourceDir(resource)
    rec_list = list()
    if not os.path.exists(rec_dir):
        return -1
    else:
        recs = os.listdir(rec_dir)
        #dprint(recs)
        for rec in recs:
            if os.path.isfile(os.path.join(rec_dir, rec)):
                if trim:
                    rec = rec.split(u".")[0]
                if title:
                    rec = rec.title()
                rec_list.append(rec)
        rec_list.sort()
        return list(set(rec_list))
    
def GetExtension(file_str):
    """Gets last atom at end of string as extension if 
    no extension whole string is returned
    @param file_str: path or file name to get extension from

    """
    pieces = file_str.split('.')
    extension = pieces[-1]
    return extension

def GetPathName(path):
    """Gets the path minus filename
    @param path: full path to get base of

    """
    pieces = os.path.split(path)
    return pieces[0]

def GetFileName(path):
    """Gets last atom on end of string as filename
    @param path: full path to get filename from

    """
    pieces = os.path.split(path)
    filename = pieces[-1]
    return filename

def HexToRGB(hex_str):
    """Returns a list of red/green/blue values from a
    hex string.
    @param hex_str: hex string to convert to rgb
    
    """
    hexval = hex_str
    if hexval[0] == u"#":
        hexval = hexval[1:]
    ldiff = 6 - len(hexval)
    hexval += ldiff * u"0"
    # Convert hex values to integer
    red = int(hexval[0:2], 16)
    green = int(hexval[2:4], 16)
    blue = int(hexval[4:], 16)
    return [red, green, blue]

