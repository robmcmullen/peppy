# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Project support in peppy

This plugin provides support for projects, including individual templates for
projects, makefile and compilation support, and eventually even more good
stuff.

Templates can exist as global templates, or can exist within projects that
will override the global templates.  Global templates are stored in the peppy
configuration directory, while project templates are stored within the project
directory.

The project plugin adds the attribute 'project_info' to all major mode
instances when the plugin is activated.  Its value with be an instance of the
L{ProjectInfo} object if there is a project associated with the major mode,
otherwise it will be C{None}.  Therefore, you don't have to use hasattr(mode,
'project_info') before checking the value of project_info assuming that this
plugin is loaded.
"""
import os, re
import cPickle as pickle

from wx.lib.pubsub import Publisher
from peppy.third_party.pubsub import pub

import peppy.vfs as vfs

from peppy.about import AddCopyright
from peppy.yapsy.plugins import *
from peppy.lib.userparams import *
from peppy.lib.pluginmanager import *

from peppy.project.actions import *
from peppy.project.project import *
from peppy.project.project_sidebar import ProjectSidebar

AddCopyright("Editra Plugins", "http://code.google.com/p/editra-plugins/wiki/ProjectsPlugin", "Kevin D. Smith and Cody Precord", "2007-2008", "Source control utilities (git, svn, bzr, etc.) and project tree display from")


class ProjectPlugin(IPeppyPlugin):
    default_classprefs = (
        StrParam('project_directory', '.peppy-project', 'Directory used within projects to store peppy specific information', fullwidth=True),
        StrParam('project_file', 'project.cfg', 'File within project directory used to store per-project information', fullwidth=True),
        StrParam('template_directory', 'templates', 'Directory used to store template files for given major modes', fullwidth=True),
        StrParam('settings_directory', 'settings', 'Directory used to store files used to save project-specific settings for major modes', fullwidth=True),
        StrParam('default_settings_file_name', 'default-settings', 'File name used to store default view settings for all major modes in this project', fullwidth=True),
        StrParam('known_projects_file', 'known_projects.txt', 'File name in main peppy configuration directory used to store the list of known projects', fullwidth=True),
        PathParam('ctags_command', 'ctags', 'Path to ctags command', fullwidth=True),
        StrParam('ctags_tag_file_name', 'tags', 'name of the generated tags file', fullwidth=True),
        StrParam('ctags_args', '-R -n', 'extra arguments for the ctags command', fullwidth=True),
        )
    
    # mapping of projects we know about but haven't loaded ProjectInfo objects
    # for.  Maps URLs to KnownProject objects
    unloaded_but_known_projects = {}
    
    # mapping of known project URLs to their Project objects
    url_to_project_mapping = {}
    
    # mapping of buffer URLs to the project directory that is closest to it in
    # the hierarchy.
    buffer_url_to_project_dir = {}

    def initialActivation(self):
        if not wx.GetApp().config.exists(self.classprefs.template_directory):
            wx.GetApp().config.create(self.classprefs.template_directory)
        self.loadKnownProjectNames()
    
    def loadKnownProjectNames(self):
        pathname = wx.GetApp().getConfigFilePath(self.classprefs.known_projects_file)
        if not os.path.exists(pathname):
            return
        try:
            import pickle
            
            fh = open(pathname, 'rb')
            data = pickle.load(fh)
            self.dprint(data)
            if isinstance(data, dict):
                self.__class__.unloaded_but_known_projects = data
        except Exception, e:
            dprint("Failed loading known project list %s" % pathname)
            dprint(e)
            pass
    
    @classmethod
    def getKnownProjects(cls):
        """Get a list of known projects, either projects already loaded or
        those that we know about but haven't loaded ProjectInfo objects for.
        """
        projects = {}
        for project_info in cls.url_to_project_mapping.itervalues():
            url = project_info.getTopURL()
            if url in cls.unloaded_but_known_projects:
                del cls.unloaded_but_known_projects[url]
            projects[url] = project_info.getKnownProject()
        for url, project_info in cls.unloaded_but_known_projects.iteritems():
            projects[url] = project_info
        return projects
    
    @classmethod
    def isLoadedProject(cls, project_info):
        """Returns True if project info has been loaded.
        """
        project_info = project_info.getKnownProject()
        url = project_info.getTopURL()
        return url in cls.url_to_project_mapping
    
    @classmethod
    def removeKnownProject(cls, project_info):
        """Get a list of known projects, either projects already loaded or
        those that we know about but haven't loaded ProjectInfo objects for.
        """
        project_info = project_info.getKnownProject()
        url = project_info.getTopURL()
        if url in cls.unloaded_but_known_projects:
            del cls.unloaded_but_known_projects[url]

    def requestedShutdown(self):
        self.saveKnownProjectNames()

    @classmethod
    def saveKnownProjectNames(cls):
        pathname = wx.GetApp().getConfigFilePath(cls.classprefs.known_projects_file)
        try:
            import pickle
            
            fh = open(pathname, 'wb')
            known = cls.getKnownProjects()
            cls.dprint(known)
            pickle.dump(known, fh)
        except Exception, e:
            dprint("Failed saving known project list to %s because %s" % (pathname, e))
            pass

    def activateHook(self):
        Publisher().subscribe(self.projectInfo, 'mode.preinit')
        Publisher().subscribe(self.getFundamentalMenu, 'fundamental.context_menu')
        Publisher().subscribe(self.applyProjectSettings, 'fundamental.default_settings_applied')
        pub.subscribe(self.getTabMenu, 'tabs.context_menu')

    def deactivateHook(self):
        Publisher().unsubscribe(self.projectInfo)
        Publisher().unsubscribe(self.getFundamentalMenu)
        Publisher().unsubscribe(self.applyProjectSettings)
        pub.unsubscribe(self.getTabMenu, 'tabs.context_menu')
    
    @classmethod
    def getTemplateFilename(cls, template_name):
        """Convenience function to return the full path to a global template"""
        return wx.GetApp().config.fullpath("%s/%s" % (cls.classprefs.template_directory, template_name))
    
    @classmethod
    def getConfigFileHandle(cls, confdir, mode, url):
        """Get a file handle to data in the project's configuration directory.
        
        Files within the configuration directory should be based on the major
        mode name, and optionally for added specificity can append a filename
        extension.
        
        For instance, the template system used for projects uses the
        "$PROJROOT/.peppy- project/templates" directory by default, where
        $PROJROOT is the root directory of the project.  Within that templates
        directory, the file "Python" is the default for python files, but
        "Python.pyx" could be used as a default for pyrex files.
        
        @param confdir: pathname of configuration directory
        @param mode: major mode instance
        @param url: url of file that is being created
        
        @return: file-like object to read the data, or None if not found
        """
        filename = vfs.get_filename(url)
        names = []
        if '.' in filename:
            ext = filename.split('.')[-1]
            names.append(confdir.resolve2("%s.%s" % (mode.keyword, ext)))
        names.append(confdir.resolve2(mode.keyword))
        for configname in names:
            try:
                cls.dprint("Trying to load file %s" % configname)
                fh = vfs.open(configname)
                return fh
            except:
                pass
        return None

    @classmethod
    def findProjectConfigFileHandle(cls, mode, subdir):
        """Get a file handle to data in a sub-directory of the project's
        configuration directory.
        
        Uses L{getConfigFileHandle} to return a file-like object inside a
        subdirectory of the project's config directory.
        """
        cls.dprint(mode)
        if mode.project_info:
            url = mode.project_info.getSettingsRelativeURL(subdir)
            cls.dprint(unicode(url))
            if vfs.is_folder(url):
                fh = cls.getConfigFileHandle(url, mode, mode.buffer.url)
                return fh
        return None
    
    @classmethod
    def findProjectConfigFile(cls, mode, subdir):
        fh = cls.findProjectConfigFileHandle(mode, subdir)
        if fh:
            return fh.read()
        return None
    
    @classmethod
    def findProjectConfigObject(cls, mode, subdir):
        fh = cls.findProjectConfigFileHandle(mode, subdir)
        if fh:
            item = pickle.load(fh)
            return item
        return None
    
    @classmethod
    def findGlobalTemplate(cls, mode, url):
        """Find the global template that belongs to the particular major mode
        
        @param mode: major mode instance
        @param url: url of file that is being created
        """
        subdir = wx.GetApp().config.fullpath(cls.classprefs.template_directory)
        template_url = vfs.normalize(subdir)
        fh = cls.getConfigFileHandle(template_url, mode, url)
        if fh:
            return fh.read()

    @classmethod
    def findProjectConfigDir(cls, mode, subdir=""):
        cls.dprint(mode)
        if mode.project_info:
            url = mode.project_info.getSettingsRelativeURL(subdir)
            if subdir:
                url = url.resolve2(mode.keyword)
            cls.dprint(unicode(url))
            return url
        return None

    @classmethod
    def findProjectTemplateURL(cls, mode):
        return cls.findProjectConfigDir(mode, cls.classprefs.template_directory)

    @classmethod
    def findProjectSettingsURL(cls, mode):
        return cls.findProjectConfigDir(mode, cls.classprefs.settings_directory)

    @classmethod
    def findProjectTemplate(cls, mode):
        cls.dprint(mode)
        template = cls.findProjectConfigFile(mode, cls.classprefs.template_directory)
        if template is not None:
            return template
        return cls.findGlobalTemplate(mode, mode.buffer.url)
    
    @classmethod
    def findProjectURL(cls, url):
        # Check to see if we already know what the path is, and if we think we
        # do, make sure the project path still exists
        if url in cls.buffer_url_to_project_dir:
            path = cls.buffer_url_to_project_dir[url]
            if vfs.is_folder(path):
                return path
            del cls.buffer_url_to_project_dir[url]
        
        # Look for a new project path starting from the specified URL.
        if vfs.is_folder(url):
            last = vfs.normalize(url)
        else:
            last = vfs.normalize(vfs.get_dirname(url))
        cls.dprint(str(last.path))
        while not last.path.is_relative() and True:
            path = last.resolve2("%s" % (cls.classprefs.project_directory))
            cls.dprint(path.path)
            if vfs.is_folder(path):
                cls.buffer_url_to_project_dir[url] = path
                return path
            path = vfs.get_dirname(path.resolve2('..'))
            if path == last:
                cls.dprint("Done!")
                break
            last = path
        return None
    
    @classmethod
    def loadProjectByProjectConfigDir(cls, url):
        """Given the URL of a project config directory, load the ProjectInfo
        object if not already loaded.
        
        @return L{ProjectInfo} instance
        """
        if url not in cls.url_to_project_mapping:
            info = ProjectInfo(url)
            cls.url_to_project_mapping[url] = info
            cls.removeKnownProject(info)
        else:
            info = cls.url_to_project_mapping[url]
        cls.dprint("found project %s" % info)
        return info
    
    @classmethod
    def loadProjectInfoFromKnownProject(cls, known):
        """Given an KnownProject or a ProjectInfo, load the ProjectInfo
        object if necessary.
        
        It's possible that the info object points to a KnownProject instead
        of a ProjectInfo, so if it does, load the project and get the real
        ProjectInfo
        
        @return L{ProjectInfo} instance
        """
        dprint(known)
        url = known.getTopURL()
        url = url.resolve2("%s" % (cls.classprefs.project_directory))
        dprint(url)
        info = cls.loadProjectByProjectConfigDir(url)
        dprint(info)
        return info

    @classmethod
    def registerProject(cls, mode, url=None):
        """Associate a L{ProjectInfo} object with a major mode.
        
        A file is associated with a project by being inside a project
        directory.  If the URL of the file used in the buffer of the major
        mode is inside a project directory, the keyword 'project_info' will be
        added to the major mode's instance attributes.
        """
        if url is None:
            url = cls.findProjectURL(mode.buffer.url)
        if url:
            info = cls.loadProjectByProjectConfigDir(url)
        elif mode:
            cls.dprint(u"no project for %s" % mode.buffer.url)
            info = None
        
        if cls.debuglevel > 0:
            cls.dprint("Registered projects:")
            for url, project_info in cls.url_to_project_mapping.iteritems():
                cls.dprint(u"%s\t%s" % (project_info.getProjectName(), url))
        
        if mode:
            mode.project_info = info
        return info

    @classmethod
    def getProjectInfo(cls, mode):
        url = cls.findProjectURL(mode.buffer.url)
        if url and url in cls.url_to_project_mapping:
            return cls.url_to_project_mapping[url]
        return None
    
    @classmethod
    def createProject(cls, topdir):
        url = vfs.normalize(topdir)
        if url in cls.url_to_project_mapping:
            raise TypeError("Project already exists.")
        proj_dir = url.resolve2(cls.classprefs.project_directory)
        if not vfs.is_folder(proj_dir):
            if not vfs.exists(proj_dir):
                vfs.make_folder(proj_dir)
            else:
                raise TypeError("Can't create directory %s -- seems already exist as a file" % proj_dir)
        info = cls.registerProject(None, proj_dir)
        info.savePrefs()
        cls.dprint(info)
        buffers = BufferList.getBuffers()
        for buffer in buffers:
            if buffer.url.scheme != "file":
                continue
            cls.dprint(u"prefix=%s topdir=%s" % (buffer.url.path.get_prefix(url.path), url.path))
            if buffer.url.path.get_prefix(url.path) == url.path:
                cls.dprint(u"belongs in project! %s" % buffer.url.path)
                for mode in buffer.iterViewers():
                    mode.project_info = info
            else:
                cls.dprint(u"not in project: %s" % buffer.url.path)
        return info

    @classmethod
    def projectInfo(cls, msg):
        """Publish/subscribe callback called by major mode creation process.
        
        This is used to add the L{ProjectInfo} to a major mode when it's
        contained in a project.  If the file is found to belong to a project,
        another message is sent indicating that the mode does belong to a
        project.  This is currently used, for instance, in the openrecent
        plugin to add the project file to a recent projects menu.
        
        Additionally, this is where template processing is handled for project
        files.  If the major mode determines that it would like to use a
        template, it is applied here.
        """
        mode = msg.data
        
        # Add 'project' keyword to Buffer object if the file belongs to a
        # project
        cls.registerProject(mode)
        
        # If the file belongs to a project, send message to anyone interested
        # that we've found the project
        if mode.project_info:
            pub.sendMessage('project.file.opened', mode=mode)
        
        # handle templates for empty files
        if hasattr(mode, "isTemplateNeeded"):
            if mode.isTemplateNeeded():
                template = cls.findProjectTemplate(mode)
                if template:
                    mode.setTextFromTemplate(template)

    @classmethod
    def applyProjectSettings(cls, msg):
        """Publish/subscribe callback to load project view settings.
        
        This is called by the major mode loading process to set the default
        view parameters based on per-project defaults.
        """
        mode = msg.data
        if not mode.project_info:
            return
        
        cls.dprint("Applying settings for %s" % mode)
        # Add 'project' keyword to Buffer object if the file belongs to a
        # project
        settings = cls.findProjectConfigObject(mode, cls.classprefs.settings_directory)
        if not settings:
            # Try the global settings
            cls.dprint("Trying default settings for project %s" % mode.project_info.project_name)
            base = mode.project_info.getSettingsRelativeURL()
            url = base.resolve2(ProjectPlugin.classprefs.default_settings_file_name)
            if vfs.exists(url):
                fh = vfs.open(url)
                settings = pickle.load(fh)
                fh.close()
        if settings and isinstance(settings, dict):
            #dprint(settings)
            #mode.applyFileLocalComments(settings)
            mode.classprefsUpdateLocals(settings)
            mode.applyDefaultSettings()
    
    @classmethod
    def verifyCtagsCommand(cls):
        """Attempt to call the specified CTAGS program to verify that it is
        Exuberant CTAGS.
        
        @returns: boolean to report if successfully verified
        """
        import subprocess
        try:
            proc = subprocess.Popen([cls.classprefs.ctags_command, "--help"], stdout=subprocess.PIPE)
            stdout, stderr = proc.communicate()
            for line in stdout.splitlines():
                if 'Exuberant' in line:
                    return True
        except OSError:
            dprint("Failed starting %s" % cls.classprefs.ctags_command)
        return False
    
    @classmethod
    def verifyCtagsWithDialog(cls):
        """Verifies the CTAGS program and shows error dialog if not correct
        version.
        
        Uses L{verifyCtagsCommand} to check if the CTAGS program specified in
        the global project configuration is valid, and if not it displays an
        error dialog.
        
        The classpref containing the ctags command is cleared if it is not
        valid.
        """
        if not cls.verifyCtagsCommand():
            dlg = wx.MessageDialog(wx.GetApp().GetTopWindow(), "%s\n\ndoesn't appear to be Exuberant CTAGS.  Install from\nhttp://ctags.sourceforge.net/ for your platform and change\nthe setting in the Global Project Settings tab of the\nProject Settings dialog." % cls.classprefs.ctags_command, "Invalid CTAGS Program", wx.OK | wx.ICON_ERROR)
            retval = dlg.ShowModal()
            
            cls.classprefs.ctags_command = ""
    
    @classmethod
    def hasValidCtagsCommand(cls):
        """Convenience function for checking if the CTAGS command is valid.
        
        @returns: boolean if the CTAGS command has been previously verified by
        a call to L{verifyCtagsCommand}.  Note that it may have been verified
        in a previous invocation of peppy.
        """
        return bool(cls.classprefs.ctags_command)
    
    def getTabMenu(self, action_classes=None):
        action_classes.extend([(810, CurrentlyLoadedFilesInProject)])

    def getCompatibleActions(self, modecls):
        actions = []
        if hasattr(modecls, 'isTemplateNeeded'):
            actions.append(SaveGlobalTemplate)
            actions.extend([SaveProjectTemplate,
                            
                            BuildProject, RunProject, StopProject,
                            
                            RebuildCtags, LookupCtag,
                            
                            SaveProjectSettingsMode, SaveProjectSettingsAll])
        actions.extend([CreateProject, CreateProjectFromExisting, ShowProjectSettings])
        return actions

    def getFundamentalMenu(self, msg):
        action_classes = msg.data
        action_classes.append((-10, ShowTagAction))
    
    def getSidebars(self):
        yield ProjectSidebar

# Make ProjectPlugin a global for now until I figure out a better way to deal
# with this.
import __builtin__
__builtin__.ProjectPlugin = ProjectPlugin
