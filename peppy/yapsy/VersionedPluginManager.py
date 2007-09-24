#!/usr/bin/python
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

"""
Defines the basic interface for a plugin manager that also keeps track
of versions of plugins
"""

import sys, os
import logging
import ConfigParser
from distutils.version import StrictVersion

from PluginManager import PluginManager, PluginInfo, PLUGIN_NAME_FORBIDEN_STRING
from IPlugin import IPlugin

class VersionedPluginInfo(PluginInfo):
	"""
	Gather some info about a plugin such as its name, author,
	description...
	"""
	
	def __init__(self, plugin_name, plugin_path):
		"""
		Set the namle and path of the plugin as well as the default
		values for other usefull variables.
		"""
		PluginInfo.__init__(self, plugin_name, plugin_path)
		# version number is now required to be a StrictVersion object
		self.version	= StrictVersion("0.0")

	def setVersion(self, vstring):
		self.version = StrictVersion(vstring)


class VersionedPluginManager(PluginManager):
	"""
	Manage several plugins by ordering them in several categories with
	versioning capabilities.
	"""

	def __init__(self, 
				 categories_filter={"Default":IPlugin}, 
				 directories_list=[os.path.dirname(__file__)], 
				 plugin_info_ext="yapsy-plugin"):
		"""
		Initialize the mapping of the categories and set the list of
		directories where plugins may be. This can also be set by
		direct call the methods: 
		  - ``setCategoriesFilter`` for ``categories_filter``
		  - ``setPluginPlaces`` for ``directories_list``
		  - ``setPluginInfoExtension`` for ``plugin_info_ext``

		You may look at these function's documentation for the meaning
		of each corresponding arguments.
		"""
		PluginManager.__init__(self, categories_filter, directories_list,
							   plugin_info_ext)
		self.candidates = []

	def setCategoriesFilter(self, categories_filter):
		"""
		Set the categories of plugins to be looked for as well as the
		way to recognise them.

		The ``categories_filter`` first defines the various categories
		in which the plugins will be stored via its keys and it also
		defines the interface tha has to be inherited by the actual
		plugin class belonging to each category.
		"""
		PluginManager.setCategoriesFilter(self, categories_filter)
		# prepare the mapping of the latest version of each plugin
		self.latest_mapping = {}
		for categ in self.categories_interfaces.keys():
			self.latest_mapping[categ] = []

	def getLatestPluginsOfCategory(self,category_name):
		"""
		Return the list of all plugins belonging to a category.
		"""
		return self.latest_mapping[category_name]

	def getActivePluginObjects(self, interface=None):
		"""
		Return the list of all plugins.
		"""
		active = []
		for plugin in self.all_plugins:
			#print "checking plugin %s for interface %s" % (plugin.name, interface)
			obj = plugin.plugin_object
			if obj.is_activated:
				#print "  plugin %s activated!: class=%s" % (obj, obj.__class__)
				#print "     mro=%s" % str(obj.__class__.__mro__)
				if interface is not None:
					if isinstance(obj, interface):
						active.append(obj)
				else:
					active.append(obj)
		return active

	def locatePlugins(self, info_class=PluginInfo):
		"""
		Walk through the plugins' places and look for plugins.  Then
		for each plugin candidate look for its category, load it and
		stores it in the appropriate slot of the category_mapping.
		"""
		for directory in map(os.path.abspath,self.plugins_places):
			# first of all, is it a directory :)
			if not os.path.isdir(directory):
				logging.debug("%s skips %s (not a directory)" % (self.__class__.__name__,directory))
				continue
			# iteratively walks through the directory
			logging.debug("%s walks into directory: %s" % (self.__class__.__name__,directory))
			for item in os.walk(directory):
				dirpath = item[0]
				for filename in item[2]:
					# eliminate the obvious non plugin files
					if not filename.endswith(".%s" % self.plugin_info_ext):
						continue
					# now we can consider the file as a serious candidate
					candidate_infofile = os.path.join(dirpath,filename)
					logging.debug("""%s found a candidate: 
	%s""" % (self.__class__.__name__, candidate_infofile))
					# parse the information file to get info about the plugin
					config_parser = ConfigParser.SafeConfigParser()
					try:
						config_parser.read(candidate_infofile)
					except:
						logging.debug("Could not parse the plugin file %s" % candidate_infofile)					
 						continue
					# check if the basic info is available
					if not config_parser.has_section("Core"):
						continue
					if not config_parser.has_option("Core","Name") or not config_parser.has_option("Core","Module"):
						continue
					# check that the given name is valid
					name = config_parser.get("Core", "Name")
					name = name.strip()
					if PLUGIN_NAME_FORBIDEN_STRING in name:
						continue				
					# start collecting essential info
					plugin_info = info_class(name, 
											 os.path.join(dirpath,config_parser.get("Core", "Module")))
					# collect additional (but usually quite usefull) information
					if config_parser.has_section("Documentation"):
						if config_parser.has_option("Documentation","Author"):
							plugin_info.author	= config_parser.get("Documentation", "Author")
						if config_parser.has_option("Documentation","Version"):
							plugin_info.setVersion(config_parser.get("Documentation", "Version"))
						if config_parser.has_option("Documentation","Website"): 
							plugin_info.website	= config_parser.get("Documentation", "Website")
						if config_parser.has_option("Documentation","Copyright"):
							plugin_info.copyright	= config_parser.get("Documentation", "Copyright")
					
					# now determine the path of the file to execute,
					# depending on wether the path indicated is a
					# directory or a file
					if os.path.isdir(plugin_info.path):
						candidate_filepath = os.path.join(plugin_info.path,"__init__.py")
					else:
						candidate_filepath = plugin_info.path

					self.candidates.append((candidate_infofile, candidate_filepath, plugin_info))
		return len(self.candidates)

	def loadPlugins(self, callback = None):
		"""
		Load the candidate plugins identified, calling the callback
		function after every attempt.
		"""
		for candidate_infofile, candidate_filepath, plugin_info in self.candidates:
			# now execute the file and get its content into a
			# specific dictionnary
			candidate_globals = {}
			try:
				execfile(candidate_filepath+".py",candidate_globals)
			except Exception,e:
				logging.debug("Unable to execute the code in plugin: %s" % candidate_filepath)
				logging.debug("\t The following problem occured: %s %s " % (os.linesep, e))

			if callback is not None:
				callback(plugin_info)

			# now try to find and initialise the first subclass of the correct plugin interface
			for element in candidate_globals.values():
				current_category = None
				for category_name in self.categories_interfaces.keys():
					try:
						is_correct_subclass = issubclass(element, self.categories_interfaces[category_name])
					except:
						continue
					if is_correct_subclass:
						if element is not self.categories_interfaces[category_name]:
							current_category = category_name
							break
				if current_category is not None:
					if not (candidate_infofile in self._category_file_mapping[current_category]): 
						# we found a new plugin: initialise it and search for the next one
						plugin_info.plugin_object = element()
						plugin_info.category = current_category
						self.category_mapping[current_category].append(plugin_info)
						self._category_file_mapping[current_category].append(candidate_infofile)
						current_category = None
					break
		
		# Search through all the loaded plugins to find the latest
		# version of each.
		self.all_plugins = []
		for categ, items in self.category_mapping.iteritems():
			unique_items = {}
			for item in items:
				self.all_plugins.append(item)
				if item.name in unique_items:
					stored = unique_items[item.name]
					if item.version > stored.version:
						unique_items[item.name] = item
				else:
					unique_items[item.name] = item
			self.latest_mapping[categ] = unique_items.values()

	def collectPlugins(self):
		"""
		Walk through the plugins' places and look for plugins.  Then
		for each plugin candidate look for its category, load it and
		stores it in the appropriate slot of the category_mapping.
		"""
		PluginManager.collectPlugins(self, info_class=VersionedPluginInfo)
		
		# Search through all the loaded plugins to find the latest
		# version of each.
		self.all_plugins = []
		for categ, items in self.category_mapping.iteritems():
			unique_items = {}
			for item in items:
				self.all_plugins.append(item)
				if item.name in unique_items:
					stored = unique_items[item.name]
					if item.version > stored.version:
						unique_items[item.name] = item
				else:
					unique_items[item.name] = item
			self.latest_mapping[categ] = unique_items.values()
