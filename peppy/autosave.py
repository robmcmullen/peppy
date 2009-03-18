# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""

"""

import os

from peppy.lib.userparams import *
import peppy.vfs as vfs


class Autosave(ClassPrefs):
    preferences_tab = "General"
    icon = "icons/clock.png"
    default_classprefs = (
        BoolParam('use_autosave', True, 'Periodically save all files that have been changed to allow for recovery if there is a system crash'),
        IntParam('keystroke_interval', 10, 'Number of keystrokes before file is autosaved'),
    )
    
    def getKeystrokeInterval(self):
        return self.classprefs.keystroke_interval
    
    def isFilesystemSchemeAllowed(self, url):
        return url.scheme == 'file'
    
    def getFilename(self, original_url):
        if self.classprefs.use_autosave and self.isFilesystemSchemeAllowed(original_url):
            dirname = vfs.get_dirname(original_url)
            filename = vfs.get_filename(original_url)
            filename = "%%23%s%%23" % filename
            return dirname.resolve2(filename)


class BackupFiles(ClassPrefs):
    preferences_tab = "General"
    icon = "icons/disk_multiple.png"
    default_classprefs = (
        BoolParam('use_backups', True, 'Save backup copies of files before any modifications are made'),
    )
    
    def calculateFilename(self, url):
        dirname = vfs.get_dirname(url)
        filename = vfs.get_filename(url)
        filename = "%s~" % filename
        return dirname.resolve2(filename)
    
    def getFilename(self, original_url):
        if self.classprefs.use_backups:
            return self.calculateFilename(original_url)
