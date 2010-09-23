# -*- coding: utf-8 -*-
"""module with option implementations, to be shown in finder layouts"""
__docformat__ = "restructuredtext"

from interface import iOptions
import mrv.maya.ui as ui
import mrv.maya
import mrv.maya.util
Mel = mrv.maya.Mel
opts = mrv.maya.util.optionvars

class FileOpenOptions(ui.ColumnLayout, iOptions):
	"""Options implementation providing options useful during file-open"""
	
	#{ Configuration
	kOVExecuteScriptNodes = 'fileExecuteSN'
	kOVIgnoreVersion = 'fileOpenIgnoreVersion'
	kOVSelectivePreload = 'fileSelPreload'
	kOVRefLoadSetting = 'fileOpenRefLoadSetting'
	#} END configuration
	
	def __init__(self):
		self._create_ui_elements()
		self._restore_saved_values()
		
	def _create_ui_elements(self):
		self.cbScriptNodes = ui.CheckBox(label="Execute ScriptNodes", value=1)   
		self.cbIgnoreVersion = ui.CheckBox(label="Ignore Version")
		
		self.omReference = ui.OptionMenu(label="Load Settings")
	
		ui.MenuItem(label="Load Default References")
		ui.MenuItem(label="Load All References")
		ui.MenuItem(label="Load Top References")
		ui.MenuItem(label="Load No References")
		
		self.cbSelectivePreload = ui.CheckBox(label="Selective Preload")
		
	def _restore_saved_values(self):
		self.cbScriptNodes.p_value = opts.get(self.kOVExecuteScriptNodes, True)
		self.cbIgnoreVersion.p_value = opts.get(self.kOVIgnoreVersion, False)
		self.cbSelectivePreload.p_value = opts.get(self.kOVSelectivePreload, False)
		self.omReference.p_select = opts.get(self.kOVRefLoadSetting, 1)
		
	def fileOptions(self):
		""":return: dict with keyword options reflecting the settings of the
		interface. These should be given to the file command"""
		options = dict()
		options['ignoreVersion'] = self.cbIgnoreVersion.p_value
		options['executeScriptNodes'] = self.cbScriptNodes.p_value
		
		# TODO: Handle selective Preload !
		
		# TODO: use conditionals to work in older maya versions as well
		refsl = self.omReference.p_sl
		if refsl == 2:
			options['loadAllReferences'] = True
		elif refsl == 3:
			options['loadReferenceDepth'] = "topOnly"
		elif refsl == 4:
			options['loadNoReferences'] = True
		
		return options
