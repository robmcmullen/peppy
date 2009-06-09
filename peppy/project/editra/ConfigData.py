#!/usr/bin/env python

"""
Configuration Dialog for the Projects Plugin

"""

__author__ = "Kevin D. Smith <Kevin.Smith@sixquickrun.com>"
__revision__ = "$Revision: 595 $"
__scid__ = "$Id: ConfigDialog.py 595 2008-09-01 03:21:13Z CodyPrecord $"

#-----------------------------------------------------------------------------#
# Imports
import wx, sys, os, crypto
import SVN, CVS, GIT, BZR, HG

class ConfigData(dict):
    """ Configuration data storage class """
    _instance = None
    _created = False

    def __init__(self, data=dict()):
        """ Create the config data object """
        if not ConfigData._created:
            dict.__init__(self)

            self['source-control'] = {}
            self['general'] = {}
            self['projects'] = {}

            self.setFilters(sorted(['CVS', 'dntnd', '.DS_Store', '.dpp', '.newpp',
                                    '*~', '*.a', '*.o', '.poem', '.dll', '._*',
                                    '.localized', '.svn', '*.pyc', '*.bak', '#*',
                                    '*.pyo','*%*', '.git', '*.previous', '*.swp',
                                    '.#*', '.bzr', '.hg']))
            self.setBuiltinDiff(True)
            if wx.Platform == '__WXMAC__':
                self.setDiffProgram('opendiff')
            else:
                self.setDiffProgram('')
            self.setSyncWithNotebook(True)
            
            self.addSCSystem(CVS.CVS())
            self.addSCSystem(SVN.SVN())
            self.addSCSystem(GIT.GIT())
            self.addSCSystem(BZR.BZR())
            self.addSCSystem(HG.HG())
            
            self.load()
            ConfigData._created = True
        else:
            pass

    def __new__(cls, *args, **kargs):
        """Singleton instance
        @return: instance of this class

        """
        if cls._instance is None:
            cls._instance = dict.__new__(cls, *args, **kargs)
        return cls._instance

    @property
    def salt(self):
        return '"\x17\x9f/D\xcf'
        
    def addProject(self, path, options=dict()):
        """ Add a project and its options to the data """
        self['projects'][path] = options
        
    def removeProject(self, path):
        """ Remove a project from the configuration """
        try:
            del self['projects'][path]
        except KeyError:
            pass
        
    def clearProjects(self):
        """ Clear all project data """
        self['projects'].clear()
    
    def getProjects(self):
        """ Get all project data """
        return self['projects']
        
    def getProject(self, path):
        """ Get data for a specified project """
        return self['projects'][path]
        
    def setFilters(self, filters):
        """ Set the filters to use in filtering tree display """
        self['general']['filters'] = filters
        self.updateSCSystems()
        
    def getFilters(self):
        """ Get all filters """
        return self['general']['filters']
        
    def setBuiltinDiff(self, use_builtin=True):
        """ Set whether to use builtin diff or not
        @param use_builtin: bool

        """
        self['general']['built-in-diff'] = use_builtin
        
    def getBuiltinDiff(self):
        """ Use Projects builtin diff program """
        return self['general']['built-in-diff']
        
    def setDiffProgram(self, command):
        """ Set the diff program to use for comparing revisions """
        self['general']['diff-program'] = command
        
    def getDiffProgram(self):
        """ Get path/name of diff program to use """
        return self['general']['diff-program']
        
    def setSyncWithNotebook(self, do_sync=True):
        """ Set whether to syncronize tree with notebook or not
        @param do_sync: bool

        """
        self['general']['sync-with-notebook'] = do_sync
    
    def getSyncWithNotebook(self):
        """ Is the tree syncronized with the notebook """
        return self['general']['sync-with-notebook']
    
    def addSCSystem(self, instance, repositories=None):
        """ Add a source control system to the configuration """
        self['source-control'][instance.name] = self.newSCSystem(instance, repositories)
        self.updateSCSystems()
        return self['source-control'][instance.name]
    
    def updateSCSystems(self):
        """ Update all source control systems settings with the current 
        configuration data.
        
        """
        for key, value in self.getSCSystems().items():
            try:
                value['instance'].filters = self.getFilters()
                value['instance'].repositories = self.getSCRepositories(key)
                value['instance'].command = self.getSCCommand(key)
            except:
                pass
    
    def getSCSystems(self):
        """ Get all source control systems """
        return self['source-control']

    def getSCSystem(self, name):
        """ Get a specified source control system """
        return self['source-control'][name]

    def removeSCSystem(self, name):
        """ Remove a specified source control system from the config """
        try:
            del self['source-control'][name]
        except:
            pass

    def newSCSystem(self, instance, repositories=None):
        """ Create config object for a new source control system """
        system = {'command'  : instance.command,
                  'instance' : instance, 
                  'repositories': {'Default' : self.newSCRepository()}}
        if repositories is not None:
            system['repositories'].update(repositories)

        return system

    @staticmethod
    def newSCRepository():
        """ New empty config for a source control repository """
        return {'username':'', 'password':'', 'env':{}}
    
    def getSCRepositories(self, sc):
        """ Return all repositories for a given control system """
        return self.getSCSystem(sc)['repositories']
        
    def getSCRepository(self, sc, rep):
        """ Get the repository of a given source control system """
        return self.getSCRepositories(sc)[rep]
        
    def addSCRepository(self, sc, name):
        """ Add a new repository to a given systems data """
        self.getSCRepositories(sc)[name] = self.newSCRepository()
        
    def removeSCRepository(self, sc, name):
        """ Remove a repositories data from the given source control system """
        try:
            del self.getSCRepositories(sc)[name]
        except KeyError:
            pass
        
    def setSCUsername(self, sc, rep, name):
        """ Set the username for the given system and repository """
        self.getSCRepository(sc, rep)['username'] = name
    
    def removeSCUsername(self, sc, rep):
        """ Remove a username from the data of a given systems repository """
        try:
            del self.getSCRepository(sc, rep)['username']
        except KeyError:
            pass
        
    def getSCUsername(self, sc, rep):
        """ Get the username from the given system and repository """
        return self.getSCRepository(sc, rep)['username']
        
    def setSCPassword(self, sc, rep, password):
        """ Set the password for a given system and repository """
        if password.strip():
            enc_passwd = crypto.Encrypt(password, self.salt)
            self.getSCRepository(sc, rep)['password'] = enc_passwd
        else:
            self.getSCRepository(sc, rep)['password'] = ''            

    def getSCPassword(self, sc, rep):
        """ Get the password of the given systems repository """
        return self.getSCRepository(sc, rep)['password']

    def removeSCPassword(self, sc, rep):
        """ Remove the password data from a given systems repo """
        try:
            del self.getSCRepository(sc, rep)['password']
        except KeyError:
            pass
        
    def setSCCommand(self, sc, command):
        """ Set the command used to run the given source control system """
        system = self.getSCSystem(sc)
        system['instance'].command = system['command'] = command
    
    def getSCCommand(self, sc):
        """ Get the command used with the given system """
        return self.getSCSystem(sc)['command']

    def addSCEnvVar(self, sc, rep, name, value):
        """ Add environmental variables to use with a given system """
        self.getSCEnvVars(sc, rep)[name] = value
        
    def removeSCEnvVar(self, sc, rep, name):
        """ Remove the named environmental variable from the source system """
        try:
            del self.getSCEnvVars(sc, rep)[name]
        except KeyError:
            pass
        
    def getSCEnvVars(self, sc, rep):
        """ Get all environmental variables for the given systems repository """
        return self.getSCRepository(sc, rep)['env']

    def getSCEnvVar(self, sc, rep, name):
        """ Get a named environmental variable from the given system/repo """
        return self.getSCEnvVars(sc, rep)[name]
        
    def load(self):
        """ Load the saved configuration data from on disk config file """
        data = {}
        try:
            import ed_glob, util, stat
            filename = ed_glob.CONFIG['CACHE_DIR'] + 'Projects.config'
            conf = util.GetFileReader(filename)
            if conf != -1:
                try: 
                    data = eval(conf.read())
                    conf.close()
                except:
                    conf.close()
                    os.remove(filename)
        except (ImportError, OSError):
            pass

        recursiveupdate(self, data)
        self.updateSCSystems()

    def save(self):
        """ Write the data out to disk """
        #print repr(self)
        try:
            import ed_glob, util, stat
            filename = ed_glob.CONFIG['CACHE_DIR'] + 'Projects.config'
            conf = util.GetFileWriter(filename)
            if conf != -1:
                conf.write(repr(self))
                conf.close()
            os.chmod(filename, stat.S_IRUSR|stat.S_IWUSR)
        except (ImportError, OSError):
            pass

#-----------------------------------------------------------------------------#

def recursiveupdate(dest, src):
    """ Recursively update dst from src """
    for key, value in src.items():
        if key in dest:
            if isinstance(value, dict):
                recursiveupdate(dest[key], value)
            else:
                dest[key] = value
        else:
            dest[key] = value
    return dest

#-----------------------------------------------------------------------------#

if __name__ == '__main__':
    APP = wx.PySimpleApp(False)
    FRAME = wx.Frame(None, title="Config Dialog Parent Frame", size=(480, 335))
    CFG = ConfigDialog(FRAME, wx.ID_ANY, ConfigData())
    #cfg = GeneralConfigTab(frame, -1, ConfigData())
    #cfg = SourceControlConfigTab(frame, -1, ConfigData())
    FRAME.Show()
    CFG.Show()
    APP.MainLoop()
