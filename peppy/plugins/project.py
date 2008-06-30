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
import os

from wx.lib.pubsub import Publisher

import peppy.vfs as vfs

from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.lib.userparams import *


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



class ProjectPlugin(IPeppyPlugin):
    default_classprefs = (
        StrParam('project_directory', '.peppy-project', 'Directory used within projects to store peppy specific information'),
        StrParam('template_directory', 'templates', 'Directory used to store template files for given major modes'),
        )

    def initialActivation(self):
        if not wx.GetApp().config.exists(self.classprefs.template_directory):
            wx.GetApp().config.create(self.classprefs.template_directory)

    def activateHook(self):
        Publisher().subscribe(self.getTemplate, 'mode.preinit')

    def deactivateHook(self):
        Publisher().unsubscribe(self.getTemplate)
    
    @classmethod
    def getFilename(self, template_name):
        return wx.GetApp().config.fullpath("%s/%s" % (self.classprefs.template_directory, template_name))
    
    def getCompatibleActions(self, mode):
        if hasattr(mode, 'applyTemplate'):
            return [SaveGlobalTemplate,
                    ]
        return []

    def findTemplate(self, confdir, mode, url):
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

    def findGlobalTemplate(self, mode, url):
        """Find the global template that belongs to the particular major mode
        
        @param mode: major mode instance
        @param url: url of file that is being created
        """
        subdir = wx.GetApp().config.fullpath(self.classprefs.template_directory)
        template_url = vfs.normalize(subdir)
        return self.findTemplate(template_url, mode, url)

    def findProjectTemplate(self, mode, url):
        last = vfs.get_dirname(url)
        while True:
            path = last.resolve2("%s/%s" % (self.classprefs.project_directory, self.classprefs.template_directory))
            dprint(path.path)
            if vfs.is_folder(path):
                template = self.findTemplate(path, mode, url)
                if template:
                    return template
            path = vfs.get_dirname(path.resolve2('..'))
            if path == last:
                dprint("Done!")
                break
            last = path
        return None

    def getTemplate(self, msg):
        mode = msg.data
        if hasattr(mode, "getTemplateCallback"):
            callback = mode.getTemplateCallback()
            if callback:
                template = self.findProjectTemplate(mode, mode.buffer.url)
                if not template:
                    template = self.findGlobalTemplate(mode, mode.buffer.url)
                if template:
                    callback(template)
