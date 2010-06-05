# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, re
import cPickle as pickle

from wx.lib.pubsub import Publisher

import peppy.vfs as vfs

from peppy.buffers import *
from peppy.actions import *
from peppy.actions.minibuffer import *
from peppy.lib.pluginmanager import *


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


class ProjectActionMixin(object):
    """Mixin used to enable menu item if the current mode is in a project
    """
    def isEnabled(self):
        return bool(self.mode.project_info)


class LookupCtag(ProjectActionMixin, SelectAction):
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
    
    def isEnabled(self):
        return bool(self.mode.project_info) and ProjectPlugin.hasValidCtagsCommand()

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


class SaveProjectTemplate(ProjectActionMixin, OnDemandActionNameMixin, SelectAction):
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


class SaveProjectSettingsMode(ProjectActionMixin, OnDemandActionNameMixin, SelectAction):
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


class SaveProjectSettingsAll(ProjectActionMixin, SelectAction):
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
        
        ProjectPlugin.verifyCtagsWithDialog()



class ProjectPreferencesMixin(object):
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


class CreateProject(ProjectPreferencesMixin, SelectAction):
    """Create a new project"""
    name = "Project..."
    default_menu = ("File/New", 20)

    def action(self, index=-1, multiplier=1):
        self.createProject()


class CreateProjectFromExisting(ProjectPreferencesMixin, SelectAction):
    """Create a new project"""
    name = "Project From Existing Code..."
    default_menu = ("File/New", 21)

    def action(self, index=-1, multiplier=1):
        self.createProject()

class ShowProjectSettings(ProjectActionMixin, ProjectPreferencesMixin, SelectAction):
    """Edit project settings"""
    name = "Project Settings..."
    default_menu = ("Project", -990)
    
    def isEnabled(self):
        if self.popup_options:
            return bool(self.popup_options['sidebar'].getFirstSelectedProjectItem())
        else:
            return super(ShowProjectSettings, self).isEnabled()

    def action(self, index=-1, multiplier=1):
        if self.popup_options:
            sidebar = self.popup_options['sidebar']
            info = sidebar.loadProjectInfoFromFirstSelectedProject()
        elif self.mode.project_info:
            info = self.mode.project_info
        
        if info:
            self.showProjectPreferences(info)


class CurrentlyLoadedFilesInProject(ListAction):
    """Display a list of documents belonging to the same project as the current
    mode.
    
    """
    name = "Same Project"
    inline = False
    
    def getItems(self):
        wrapper = self.popup_options['wrapper']
        tab_mode = wrapper.editwin
        
        self.savelist = []
        if self.mode.project_info:
            known_url = self.mode.project_info.project_settings_dir
            #dprint("known=%s" % (known_url))
            for buf in BufferList.storage:
                url = ProjectPlugin.findProjectURL(buf.url)
                #dprint("buf.url=%s, project url=%s" % (buf.url, url))
                if url == known_url:
                    self.savelist.append(buf)
        return [buf.displayname for buf in self.savelist]

    def action(self, index=-1, multiplier=1):
        assert self.dprint("top window to %d: %s" % (index, self.savelist[index]))
        wrapper = self.popup_options['wrapper']
        self.frame.setBuffer(self.savelist[index], wrapper)



if __name__== "__main__":
    app = wx.PySimpleApp()
    ctags = ProjectInfo(vfs.normalize("/home/rob/src/peppy-git/.peppy-project"))
    print ctags.getTag('GetValue')
    ctags.regenerateTags()
