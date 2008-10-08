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

import peppy.vfs as vfs

from peppy.buffers import *
from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.actions.minibuffer import *
from peppy.lib.userparams import *
from peppy.lib.pluginmanager import *
from peppy.lib.processmanager import *


class CTAGS(InstancePrefs):
    """Exuberant CTAGS support for projects.
    
    Exuberant-ctags is a modern update to the classic Unix ctags program.  It
    scans files and creates relationships among the source files of a project.
    
    Peppy uses exuberant-ctags as way to cross-reference files within
    the project.  Rather than writing a similar program in python, it's
    much easier just to call an external program to do the work for you.
    But, because ctags is an external program, it must be installed
    before the ctags functionality can be used.  Check your system's
    package manager for instructions on how to add exuberant-ctags, or see
    U{ctags.sourceforge.net} for instructions.
    """
    # lookup table for kinds of ctags
    kind_of_tag = {
        'c': 'class name',
        'd': 'define',
        'e': 'enumerator',
        'f': 'function',
        'F': 'file name',
        'g': 'enumeration name',
        'm': 'member',
        'p': 'function prototype',
        's': 'structure name',
        't': 'typedef',
        'u': 'union name',
        'v': 'variable',
        }
    
    special_tags = {
        'file:': '(static scope)',
        }
    
    default_prefs = (
        StrParam('ctags_extra_args', '', 'extra arguments for the ctags command', fullwidth=True),
        StrParam('ctags_exclude', '', 'files, directories, or wildcards to exclude', fullwidth=True),
        IndexChoiceParam('tags_file_location',
                         ['project root directory', 'project settings directory'],
                         1, 'Where to store the tags file'),
        )
    
    def getTagFileURL(self):
        if self.tags_file_location == 0:
            base = self.project_top_dir
        else:
            base = self.project_settings_dir
        url = base.resolve2(ProjectPlugin.classprefs.ctags_tag_file_name)
        return url

    def regenerateTags(self):
        # need to operate on the local filesystem
        self.dprint(self.project_top_dir)
        if self.project_top_dir.scheme != "file":
            raise TypeError("Can only process ctags on local filesystem")
        cwd = str(self.project_top_dir.path)
        ctags_file = str(self.getTagFileURL().path)
        wildcards = self.ctags_exclude.split()
        excludes = " ".join(["--exclude=%s" % w for w in wildcards])
        
        # Put the output file last in this list because extra spaces at the end
        # don't get squashed like they do from the shell.  Ctags will actually
        # try to look for a filename called " ", which fails.
        args = "%s %s %s -o %s" % (ProjectPlugin.classprefs.ctags_args, self.ctags_extra_args, excludes, ctags_file)
        cmd = "%s %s" % (ProjectPlugin.classprefs.ctags_command, args)
        self.dprint(cmd)
        
        output = JobOutputSaver(self.regenerateFinished)
        ProcessManager().run(cmd, cwd, output)
    
    def regenerateFinished(self, output):
        self.dprint(output)
        if output.exit_code == 0:
            self.loadTags()
        else:
            Publisher().sendMessage('peppy.log.error', output.getErrorText())
    
    def loadTags(self):
        url = self.getTagFileURL()
        self.parseCtags(url)
    
    def parseCtags(self, filename):
        self.tags = {}
        tagre = re.compile('(.+)\t(.+)\t(.+);"\t(.+)')
        try:
            fh = vfs.open(filename)
            for line in fh:
                match = tagre.match(line)
                if match:
                    tag = match.group(1)
                    file = match.group(2)
                    addr = match.group(3)
                    fields = match.group(4)
                    self.dprint("tag=%s file=%s addr=%s field=%s" % (tag, file, addr, str(fields)))
                    if tag not in self.tags:
                        self.tags[tag] = []
                    self.tags[tag].append((file, addr, fields))
                    #dprint(self.tags[tag])
                else:
                    self.dprint(line)
        except LookupError, e:
            self.dprint("Tag file %s not found" % filename)
            pass
    
    def getTag(self, tag):
        return self.tags.get(tag, None)
    
    def getTagInfo(self, tag):
        """Get a text description of all the tags associated with the given
        keyword.
        
        Returns a string of text suitable to be used in a grep-style output
        reporter; that is, a bunch of lines starting with the string
        'filename:line number:' followed by descriptive text about each tag.
        """
        tags = self.getTag(tag)
        refs = []
        for t in tags:
            info = "%s:%s: %s  " % (t[0], t[1], tag)
            fields = t[2].split('\t')
            for field in fields:
                if ':' in field:
                    if field in self.special_tags:
                        info += self.special_tags[field]
                    else:
                        info += field + " "
                elif field in self.kind_of_tag:
                    info += "kind:" + self.kind_of_tag[field] + " "
            refs.append(info)
        if refs:
            text = os.linesep.join(refs) + os.linesep
        else:
            text = ''
        return text

    def getSortedTagList(self):
        tags = self.tags.keys()
        tags.sort()
        return tags


class ProjectInfo(CTAGS):
    """Main project support class for peppy.
    
    A project is simply a directory that contains related files.  The root
    directory of the project is indicated by a project settings directory,
    by default named ".peppy-project".  Any directory on the filesystem that
    contains the project settings directory will become a project directory.
    
    It unsupported and not recommended, but it is possible to nest projects
    inside other projects.  Files in the nested project will only report being
    members of the nested project, not the outer level project.
    """
    default_prefs = (
        StrParam('project_name', '', 'Project name'),
        DirParam('build_dir', '', 'working directory in which to build', fullwidth=True),
        StrParam('build_command', '', 'shell command to build project, relative to working directory', fullwidth=True),
        DirParam('run_dir', '', 'working directory in which to execute the project', fullwidth=True),
        StrParam('run_command', '', 'shell command to execute project, absolute path needed or will search current PATH environment variable', fullwidth=True),
        )
    
    def __init__(self, url):
        self.project_settings_dir = url
        self.project_top_dir = vfs.get_dirname(url)
        self.project_config = None
        self.loadPrefs()
        self.loadTags()
        self.process = None
    
    def __str__(self):
        return "ProjectInfo: settings=%s top=%s" % (self.project_settings_dir, self.project_top_dir)
    
    def getProjectName(self):
        return self.project_name
    
    def getSettingsRelativeURL(self, name=""):
        return self.project_settings_dir.resolve2(name)
    
    def getTopRelativeURL(self, name):
        return self.project_top_dir.resolve2(name)
    
    def loadPrefs(self):
        self.project_config = self.project_settings_dir.resolve2(ProjectPlugin.classprefs.project_file)
        try:
            fh = vfs.open(self.project_config)
            if fh:
                self.readConfig(fh)
            for param in self.iterPrefs():
                self.dprint("%s = %s" % (param.keyword, getattr(self, param.keyword)))
            self.dprint(self.configToText())
        except LookupError:
            self.dprint("Project file not found -- using defaults.")
            self.setDefaultPrefs()
    
    def savePrefs(self):
        try:
            fh = vfs.open_write(self.project_config)
            text = self.configToText()
            fh.write(text)
        except:
            self.dprint("Failed writing project config file")
    
    def registerProcess(self, job):
        self.process = job
    
    def deregisterProcess(self, job):
        self.process = None
    
    def isRunning(self):
        return bool(self.process)
    
    def build(self, frame):
        self.dprint("Compiling %s in %s" % (self.build_command, self.build_dir))
        output = JobOutputSidebarController(frame, self.registerProcess, self.deregisterProcess)
        ProcessManager().run(self.build_command, self.build_dir, output)
    
    def run(self, frame):
        self.dprint("Running %s in %s" % (self.run_command, self.run_dir))
        output = JobOutputSidebarController(frame, self.registerProcess, self.deregisterProcess)
        ProcessManager().run(self.run_command, self.run_dir, output)
    
    def stop(self):
        if self.process:
            self.process.kill()


##### Actions

class ShowTagAction(ListAction):
    name = "CTAGS"
    inline = False
    menumax = 20

    def isEnabled(self):
        return bool(self.mode.project_info) and hasattr(self, 'tags') and bool(self.tags)

    def getNonInlineName(self):
        lookup = self.mode.check_spelling[0]
        self.dprint(lookup)
        return "ctags: %s" % lookup or "ctags unavailable"

    def getItems(self):
        # Because this is a popup action, we can save stuff to this object.
        # Otherwise, we'd save it to the major mode
        if self.mode.project_info:
            lookup = self.mode.check_spelling[0]
            self.dprint(lookup)
            self.tags = self.mode.project_info.getTag(lookup)
            if self.tags:
                links = []
                for t in self.tags:
                    info = ''
                    fields = t[2].split('\t')
                    for field in fields:
                        if ':' in field:
                            info += field + " "
                    if info:
                        info += "in "
                    info += t[0]
                    links.append(info)
                return links
        return [_('No suggestions')]
    
    def action(self, index=-1, multiplier=1):
        file = self.tags[index][0]
        addr = self.tags[index][1]
        self.dprint("opening %s at line %s" % (file, addr))
        try:
            line = int(addr)
            file = "%s#%d" % (file, line)
        except:
            pass
        url = self.mode.project_info.project_top_dir.resolve2(file)
        self.frame.findTabOrOpen(url)


class LookupCtag(SelectAction):
    """Display all references given a tag name"""
    name = "Lookup Tag"
    default_menu = ("Project", -400)
    key_bindings = {'emacs': "C-c C-t"}

    def action(self, index=-1, multiplier=1):
        tags = self.mode.project_info.getSortedTagList()
        minibuffer = StaticListCompletionMinibuffer(self.mode, self, _("Lookup Tag:"), list=tags)
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, name):
        text = self.mode.project_info.getTagInfo(name)
        if not text:
            text = "No information about %s" % name
        Publisher().sendMessage('peppy.log.info', text)


class RebuildCtags(SelectAction):
    """Rebuild tag file"""
    name = "Rebuild Tag File"
    default_menu = ("Project", 499)

    def action(self, index=-1, multiplier=1):
        if self.mode.project_info:
            info = self.mode.project_info
            info.regenerateTags()


class SaveGlobalTemplate(OnDemandActionNameMixin, SelectAction):
    """Save as the default (application-wide) template for this major mode.
    """
    name = "Save as Global %s Template"
    default_menu = (("Project/Templates", -700), -100)

    def getMenuItemName(self):
        return self.__class__.name % self.mode.keyword

    def action(self, index=-1, multiplier=1):
        pathname = ProjectPlugin.getTemplateFilename(self.mode.keyword)
        self.dprint(pathname)
        self.mode.save(pathname)


class SaveProjectTemplate(OnDemandActionNameMixin, SelectAction):
    """Save as the project template for this major mode.
    """
    name = "Save as Project %s Template"
    default_menu = (("Project/Templates", -700), 110)

    def getMenuItemName(self):
        return self.__class__.name % self.mode.keyword

    def action(self, index=-1, multiplier=1):
        project = ProjectPlugin.findProjectURL(self.mode.buffer.url)
        if project:
            url = project.resolve2(self.mode.keyword)
            self.mode.save(url)
        else:
            self.mode.setStatusText("Not in a project.")


class SaveProjectSettingsMode(OnDemandActionNameMixin, SelectAction):
    """Save view settings for this major mode as the default settings for all
    new instances of this mode in this project.
    """
    name = "As Defaults for %s Mode in Project"
    default_menu = ("View/Apply Settings", -500)

    def getMenuItemName(self):
        return self.__class__.name % self.mode.keyword

    def action(self, index=-1, multiplier=1):
        url = ProjectPlugin.findProjectSettingsURL(self.mode)
        if url:
            locals = self.mode.classprefsDictFromLocals()
            fh = vfs.open_write(url)
            pickle.dump(locals, fh)
            fh.close()


class SaveProjectSettingsAll(SelectAction):
    """Save as the project template for this major mode.
    """
    name = "As Defaults for All Modes in Project"
    default_menu = ("View/Apply Settings", 510)

    def action(self, index=-1, multiplier=1):
        base = ProjectPlugin.findProjectConfigDir(self.mode)
        if base:
            url = base.resolve2(ProjectPlugin.classprefs.default_settings_file_name)
            locals = self.mode.classprefsDictFromLocals()
            fh = vfs.open_write(url)
            pickle.dump(locals, fh)
            fh.close()


class BuildProject(SelectAction):
    """Build the project"""
    name = "Build..."
    icon = 'icons/cog.png'
    default_menu = ("Project", 100)
    key_bindings = {'default': "F7"}

    def isEnabled(self):
        return bool(self.mode.project_info and self.mode.project_info.build_command and not self.mode.project_info.isRunning())

    def action(self, index=-1, multiplier=1):
        self.mode.project_info.build(self.frame)


class RunProject(SelectAction):
    """Run the project"""
    name = "Run..."
    icon = 'icons/application.png'
    default_menu = ("Project", 101)

    def isEnabled(self):
        return bool(self.mode.project_info and self.mode.project_info.run_command and not self.mode.project_info.isRunning())

    def action(self, index=-1, multiplier=1):
        self.mode.project_info.run(self.frame)


class StopProject(SelectAction):
    """Stop the build or run of the project"""
    name = "Stop"
    icon = 'icons/stop.png'
    default_menu = ("Project", 109)

    def isEnabled(self):
        return bool(self.mode.project_info and self.mode.project_info.run_command and self.mode.project_info.isRunning())

    def action(self, index=-1, multiplier=1):
        self.mode.project_info.stop()


class ProjectSettings(wx.Dialog):
    dialog_title = "Project Settings"
    
    def __init__(self, parent, project, title=None):
        if title is None:
            title = self.dialog_title
        wx.Dialog.__init__(self, parent, -1, title,
                           size=(700, 500), pos=wx.DefaultPosition, 
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self)
        sizer.Add(self.notebook, 1, wx.EXPAND)
        
        self.local = InstancePanel(self.notebook, project)
        self.notebook.AddPage(self.local, _("This Project"))
        
        pm = wx.GetApp().plugin_manager
        plugins = pm.getPluginInfo(ProjectPlugin)
        #dprint(plugins)
        
        self.plugin = PluginPanel(self.notebook, plugins[0])
        self.notebook.AddPage(self.plugin, _("Global Project Settings"))
        
        btnsizer = wx.StdDialogButtonSizer()
        
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        self.SetSizer(sizer)
        self.Layout()
    
    def applyPreferences(self):
        self.local.update()
        self.plugin.update()



class ProjectActionMixin(object):
    def getProjectDir(self, cwd):
        dlg = wx.DirDialog(self.frame, "Choose Top Level Directory",
                           defaultPath = cwd)
        retval = dlg.ShowModal()
        if retval == wx.ID_OK:
            path = dlg.GetPath()
            self.dprint(path)
            info = ProjectPlugin.createProject(path)
        else:
            info = None
        dlg.Destroy()
        return info
    
    def showProjectPreferences(self, info):
        dlg = ProjectSettings(self.frame, info)
        retval = dlg.ShowModal()
        if retval == wx.ID_OK:
            dlg.applyPreferences()
            info.savePrefs()
    
    def createProject(self):
        cwd = self.frame.cwd()
        info = self.getProjectDir(cwd)
        if info:
            self.showProjectPreferences(info)
            info.regenerateTags()


class CreateProject(ProjectActionMixin, SelectAction):
    """Create a new project"""
    name = "Project..."
    default_menu = ("File/New", 20)

    def action(self, index=-1, multiplier=1):
        self.createProject()


class CreateProjectFromExisting(ProjectActionMixin, SelectAction):
    """Create a new project"""
    name = "Project From Existing Code..."
    default_menu = ("File/New", 21)

    def action(self, index=-1, multiplier=1):
        self.createProject()

class ShowProjectSettings(ProjectActionMixin, SelectAction):
    """Edit project settings"""
    name = "Project Settings..."
    default_menu = ("Project", -990)

    def isEnabled(self):
        return bool(self.mode.project_info)
    
    def action(self, index=-1, multiplier=1):
        if self.mode.project_info:
            info = self.mode.project_info
            self.showProjectPreferences(info)


class ProjectPlugin(IPeppyPlugin):
    default_classprefs = (
        StrParam('project_directory', '.peppy-project', 'Directory used within projects to store peppy specific information'),
        StrParam('project_file', 'project.cfg', 'File within project directory used to store per-project information'),
        StrParam('template_directory', 'templates', 'Directory used to store template files for given major modes'),
        StrParam('settings_directory', 'settings', 'Directory used to store files used to save project-specific settings for major modes'),
        StrParam('default_settings_file_name', 'default-settings', 'File name used to store default view settings for all major modes in this project'),
        PathParam('ctags_command', 'ctags', 'Path to ctags command', fullwidth=True),
        PathParam('ctags_tag_file_name', 'tags', 'name of the generated tags file', fullwidth=True),
        StrParam('ctags_args', '-R -n', 'extra arguments for the ctags command', fullwidth=True),
        )
    
    # mapping of known project URLs to their Project objects
    known_projects = {}
    
    # mapping of buffer URLs to the project directory that is closest to it in
    # the hierarchy.
    known_project_dirs = {}

    def initialActivation(self):
        if not wx.GetApp().config.exists(self.classprefs.template_directory):
            wx.GetApp().config.create(self.classprefs.template_directory)

    def activateHook(self):
        Publisher().subscribe(self.projectInfo, 'mode.preinit')
        Publisher().subscribe(self.getFundamentalMenu, 'fundamental.context_menu')
        Publisher().subscribe(self.applyProjectSettings, 'fundamental.default_settings_applied')

    def deactivateHook(self):
        Publisher().unsubscribe(self.projectInfo)
        Publisher().unsubscribe(self.getFundamentalMenu)
        Publisher().unsubscribe(self.applyProjectSettings)
    
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
            cls.dprint(url)
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
            cls.dprint(url)
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
        if url in cls.known_project_dirs:
            path = cls.known_project_dirs[url]
            if vfs.is_folder(path):
                return path
            del cls.known_project_dirs[url]
        
        # Look for a new project path
        last = vfs.normalize(vfs.get_dirname(url))
        cls.dprint(str(last.path))
        while not last.path.is_relative() and True:
            path = last.resolve2("%s" % (cls.classprefs.project_directory))
            cls.dprint(path.path)
            if vfs.is_folder(path):
                cls.known_project_dirs[url] = path
                return path
            path = vfs.get_dirname(path.resolve2('..'))
            if path == last:
                cls.dprint("Done!")
                break
            last = path
        return None

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
            if url not in cls.known_projects:
                info = ProjectInfo(url)
                cls.known_projects[url] = info
            else:
                info = cls.known_projects[url]
            cls.dprint("found project %s" % info)
        elif mode:
            cls.dprint("no project for %s" % str(mode.buffer.url))
            info = None
        
        if cls.debuglevel > 0:
            cls.dprint("Registered projects:")
            for url, project_info in cls.known_projects.iteritems():
                cls.dprint("%s\t%s" % (project_info.getProjectName(), str(url)))
        
        if mode:
            mode.project_info = info
        return info

    @classmethod
    def getProjectInfo(cls, mode):
        url = cls.findProjectURL(mode.buffer.url)
        if url and url in cls.known_projects:
            return cls.known_projects[url]
        return None
    
    @classmethod
    def createProject(cls, topdir):
        url = vfs.normalize(topdir)
        if url in cls.known_projects:
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
            cls.dprint("prefix=%s topdir=%s" % (buffer.url.path.get_prefix(url.path), url.path))
            if buffer.url.path.get_prefix(url.path) == url.path:
                cls.dprint("belongs in project! %s" % buffer.url.path)
                for mode in buffer.iterViewers():
                    mode.project_info = info
            else:
                cls.dprint("not in project: %s" % buffer.url.path)
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
            Publisher().sendMessage('project.file.opened', mode)
        
        # handle templates for empty files
        if hasattr(mode, "getTemplateCallback"):
            callback = mode.getTemplateCallback()
            if callback:
                template = cls.findProjectTemplate(mode)
                if template:
                    callback(template)

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

    def getCompatibleActions(self, mode):
        actions = []
        if hasattr(mode, 'getTemplateCallback'):
            actions.append(SaveGlobalTemplate)
        if mode.buffer.url in self.known_project_dirs:
            actions.extend([SaveProjectTemplate,
                            
                            BuildProject, RunProject, StopProject,
                            
                            RebuildCtags, LookupCtag,
                            
                            SaveProjectSettingsMode, SaveProjectSettingsAll])
        actions.extend([CreateProject, CreateProjectFromExisting, ShowProjectSettings])
        return actions

    def getFundamentalMenu(self, msg):
        action_classes = msg.data
        action_classes.append((-10, ShowTagAction))

if __name__== "__main__":
    app = wx.PySimpleApp()
    ctags = ProjectInfo(vfs.normalize("/home/rob/src/peppy-git/.peppy-project"))
    print ctags.getTag('GetValue')
    ctags.regenerateTags()
