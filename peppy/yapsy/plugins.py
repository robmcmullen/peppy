"""
Base class for peppy plugins
"""

from peppy.yapsy.IPlugin import IPlugin

class IPeppyPlugin(object):
	"""
	Some peppy-specific methods in addition to the yapsy plugin methods.
	"""

	def __init__(self):
		"""
		Set the basic variables.
		"""
		self.is_activated = False

	def activate(self):
		"""
		Called at plugin activation.
		"""
		self.is_activated = True

	def deactivate(self):
		"""
		Called when the plugin is disabled.
		"""
		self.is_activated = False

	def isInUse(self):
		"""
		Used in deactivation processing -- if the plugin reports that
		it is currently in use, it won't be deactivated.
		"""
		return False

