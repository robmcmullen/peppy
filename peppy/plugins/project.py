# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Project support in peppy

This plugin provides support for projects, including individual templates for
projects, makefile and compilation support, and more.  Eventually.

Templates can exist as global templates, or can exist within projects that
will override the global templates.  Global templates are stored in the peppy
configuration directory, while project templates are stored within the project
directory.
"""
import os, re

from wx.lib.pubsub import Publisher

import peppy.vfs as vfs

from peppy.buffers import *
from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.lib.userparams import *
from peppy.lib.processmanager import *


class CTAGS(InstancePrefs):
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
        dprint(self.project_top_dir)
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
        dprint(cmd)
        
        output = JobOutputSaver(self.regenerateFinished)
        ProcessManager().run(cmd, cwd, output)
    
    def regenerateFinished(self, output):
        dprint(output)
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
                    fields = match.group(4).split('\t')
                    self.dprint("tag=%s file=%s addr=%s field=%s" % (tag, file, addr, str(fields)))
                    if tag not in self.tags:
                        self.tags[tag] = []
                    self.tags[tag].append((file, addr, fields))
                    #dprint(self.tags[tag])
                else:
                    self.dprint(line)
        except LookupError, e:
            dprint("Tag file %s not found" % filename)
            pass
    
    def getTag(self, tag):
        return self.tags.get(tag, None)


class ProjectInfo(CTAGS):
    default_prefs = (
        StrParam('project_name', '', 'Project name'),
        DirParam('build_dir', '', 'working directory in which to build', fullwidth=True),
        StrParam('build_command', '', 'shell command to build project, relative to working directory', fullwidth=True),
        DirParam('run_dir', '', 'working directory in which to execute the project', fullwidth=True),
        StrParam('run_command', '', 'shell command to executee project, relative to working directory', fullwidth=True),
        )
    
    def __init__(self, url):
        self.project_settings_dir = url
        self.project_top_dir = vfs.get_dirname(url)
        self.project_config = None
        self.loadPrefs()
        self.loadTags()
    
    def __str__(self):
        return "ProjectInfo: settings=%s top=%s" % (self.project_settings_dir, self.project_top_dir)
    
    def getSettingsRelativeURL(self, name):
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
                dprint("%s = %s" % (param.keyword, getattr(self, param.keyword)))
            dprint(self.configToText())
        except LookupError:
            dprint("Project file not found -- using defaults.")
            self.setDefaultPrefs()
    
    def savePrefs(self):
        try:
            fh = vfs.open_write(self.project_config)
            text = self.configToText()
            fh.write(text)
        except:
            dprint("Failed writing project config file")
    
    def build(self):
        dprint("Compiling %s in %s" % (self.build_command, self.build_dir))
    
    def run(self):
        dprint("Running %s in %s" % (self.run_command, self.run_dir))


##### Actions

class ShowTagAction(ListAction):
    name = "CTAGS"
    inline = False
    menumax = 20

    def isEnabled(self):
        return bool(self.mode.project_info) and hasattr(self, 'tags') and bool(self.tags)

    def getNonInlineName(self):
        lookup = self.mode.check_spelling[0]
        dprint(lookup)
        return lookup or "ctags unavailable"

    def getItems(self):
        # Because this is a popup action, we can save stuff to this object.
        # Otherwise, we'd save it to the major mode
        if self.mode.project_info:
            lookup = self.mode.check_spelling[0]
            dprint(lookup)
            self.tags = self.mode.project_info.getTag(lookup)
            if self.tags:
                links = [t[0] for t in self.tags]
                return links
        return [_('No suggestions')]
    
    def action(self, index=-1, multiplier=1):
        file = self.tags[index][0]
        addr = self.tags[index][1]
        dprint("opening %s at line %s" % (file, addr))
        try:
            line = int(addr)
            file = "%s#%d" % (file, line)
        except:
            pass
        self.frame.findTabOrOpen(file)


class RebuildCtags(SelectAction):
    """Rebuild tag file"""
    name = "Rebuild Tag File"
    default_menu = ("Project", -500)

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
        pathname = ProjectPlugin.getFilename(self.mode.keyword)
        dprint(pathname)
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


class BuildProject(SelectAction):
    """Build the project"""
    name = "Build..."
    icon = 'icons/cog.png'
    default_menu = ("Project", 100)
    key_bindings = {'default': "F7"}

    def isEnabled(self):
        return bool(self.mode.project_info and self.mode.project_info.build_command)

    def action(self, index=-1, multiplier=1):
        self.mode.project_info.build()


class RunProject(SelectAction):
    """Run the project"""
    name = "Run..."
    icon = 'icons/application.png'
    default_menu = ("Project", 100)

    def isEnabled(self):
        return bool(self.mode.project_info and self.mode.project_info.run_command)

    def action(self, index=-1, multiplier=1):
        self.mode.project_info.run()


class ProjectSettings(wx.Dialog):
    dialog_title = "Project Settings"
    
    def __init__(self, parent, project, title=None):
        if title is None:
            title = self.dialog_title
        wx.Dialog.__init__(self, parent, -1, title,
                           size=(700, 500), pos=wx.DefaultPosition, 
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.panel = InstancePanel(self, project)
        sizer.Add(self.panel, 1, wx.EXPAND)
        
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
        self.panel.update()



class ProjectActionMixin(object):
    def getProjectDir(self, cwd):
        dlg = wx.DirDialog(self.frame, "Choose Top Level Directory",
                           defaultPath = cwd)
        retval = dlg.ShowModal()
        if retval == wx.ID_OK:
            path = dlg.GetPath()
            dprint(path)
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

    def action(self, index=-1, multiplier=1):
        if self.mode.project_info:
            info = self.mode.project_info
            self.showProjectPreferences(info)


class ProjectPlugin(IPeppyPlugin):
    default_classprefs = (
        StrParam('project_directory', '.peppy-project', 'Directory used within projects to store peppy specific information'),
        StrParam('project_file', 'project.ini', 'File within project directory used to store per-project information'),
        StrParam('template_directory', 'templates', 'Directory used to store template files for given major modes'),
        PathParam('ctags_command', 'exuberant-ctags', 'Path to ctags command', fullwidth=True),
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

    def deactivateHook(self):
        Publisher().unsubscribe(self.projectInfo)
        Publisher().unsubscribe(self.getFundamentalMenu)
    
    @classmethod
    def getFilename(cls, template_name):
        return wx.GetApp().config.fullpath("%s/%s" % (cls.classprefs.template_directory, template_name))
    
    @classmethod
    def findTemplate(cls, confdir, mode, url):
        """Find the template (if any) that belongs to the particular major mode
        
        @param mode: major mode instance
        @param url: url of file that is being created
        """
        filename = vfs.get_filename(url)
        names = []
        if '.' in filename:
            ext = filename.split('.')[-1]
            names.append(confdir.resolve2("%s.%s" % (mode.keyword, ext)))
        names.append(confdir.resolve2(mode.keyword))
        for configname in names:
            try:
                dprint("Trying to load template %s" % configname)
                fh = vfs.open(configname)
                template = fh.read()
                return template
            except:
                pass
        return None

    @classmethod
    def findGlobalTemplate(cls, mode, url):
        """Find the global template that belongs to the particular major mode
        
        @param mode: major mode instance
        @param url: url of file that is being created
        """
        subdir = wx.GetApp().config.fullpath(cls.classprefs.template_directory)
        template_url = vfs.normalize(subdir)
        return cls.findTemplate(template_url, mode, url)

    @classmethod
    def findProjectTemplate(cls, mode):
        dprint(mode)
        if mode.project_info:
            url = mode.project_info.getSettingsRelativeURL(cls.classprefs.template_directory)
            dprint(url)
            if vfs.is_folder(url):
                template = cls.findTemplate(url, mode, mode.buffer.url)
                if template:
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
        dprint(str(last.path))
        while not last.path.is_relative() and True:
            path = last.resolve2("%s" % (cls.classprefs.project_directory))
            dprint(path.path)
            if vfs.is_folder(path):
                cls.known_project_dirs[url] = path
                return path
            path = vfs.get_dirname(path.resolve2('..'))
            if path == last:
                dprint("Done!")
                break
            last = path
        return None

    @classmethod
    def registerProject(cls, mode, url=None):
        if url is None:
            url = cls.findProjectURL(mode.buffer.url)
        if url:
            if url not in cls.known_projects:
                info = ProjectInfo(url)
                cls.known_projects[url] = info
            else:
                info = cls.known_projects[url]
            if mode:
                mode.project_info = info
            dprint("found project %s" % info)
            return info
        elif mode:
            mode.project_info = None
    
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
        vfs.make_folder(proj_dir)
        info = cls.registerProject(None, proj_dir)
        info.savePrefs()
        dprint(info)
        buffers = BufferList.getBuffers()
        for buffer in buffers:
            if buffer.url.scheme != "file":
                continue
            dprint("prefix=%s topdir=%s" % (buffer.url.path.get_prefix(url.path), url.path))
            if buffer.url.path.get_prefix(url.path) == url.path:
                dprint("belongs in project! %s" % buffer.url.path)
                for mode in buffer.iterViewers():
                    mode.project_info = info
            else:
                dprint("not in project: %s" % buffer.url.path)
        return info

    @classmethod
    def projectInfo(cls, msg):
        mode = msg.data
        
        # Add 'project' keyword to Buffer object if the file belongs to a
        # project
        cls.registerProject(mode)
        if hasattr(mode, "getTemplateCallback"):
            callback = mode.getTemplateCallback()
            if callback:
                template = cls.findProjectTemplate(mode)
                if template:
                    callback(template)

    def getCompatibleActions(self, mode):
        actions = []
        if hasattr(mode, 'getTemplateCallback'):
            actions.append(SaveGlobalTemplate)
        if mode.buffer.url in self.known_project_dirs:
            actions.extend([SaveProjectTemplate, BuildProject, RunProject, RebuildCtags])
        actions.extend([CreateProject, CreateProjectFromExisting, ShowProjectSettings])
        return actions

    def getFundamentalMenu(self, msg):
        action_classes = msg.data
        action_classes.append(ShowTagAction)

if __name__== "__main__":
    app = wx.PySimpleApp()
    ctags = ProjectInfo(vfs.normalize("/home/rob/src/peppy-git/.peppy-project"))
    print ctags.getTag('GetValue')
    ctags.regenerateTags()
