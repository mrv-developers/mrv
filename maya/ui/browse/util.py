# -*- coding: utf-8 -*-
"""Contains misc utiltiies"""
__docformat__ = "restructuredtext"

import mrv.maya
import mrv.maya.ui as ui

def concat_url(root, path):
	if not root.endswith("/"):
		root += "/"
	return root + path
	
def handleUnsavedModifications():
	"""Ask the user whether he wants to handle his unsaved modifications.
	This may cause the current file to be saved, or the modifications to be 
	discarded.
	:return: True if the changes have been handled properly, or False if the 
		caller should not proceed"""
	if not mrv.maya.Scene.isModified():
		return True
		
	save = "Save and Proceed"
	abort = "Cancel"
	discard = "Discard Modifications"
	msg = "The currently loaded scene contains unsaved modifications.\n"
	msg += "Would you like to discard them, or save the scene before proceeding ?"
	answer = ui.ChoiceDialog(	t="Unsaved Modifications",
								m=msg, 
								c=[save, discard, abort],
								dc=save,
								cc=abort).choice()
								
	if answer == save:
		if mrv.maya.Scene.name().endswith("untitled"):
			import layout
			import maya.cmds
			maya.cmds.layoutDialog(ui=lambda *args: layout.FileSaveFinder(defaultRoots=True))
			
			# still no valid name ?
			if mrv.maya.Scene.name().endswith("untitled"):
				return False
		# END handle untitled file
		mrv.maya.Scene.save()
	elif answer == discard:
		mrv.maya.Scene.new(force=True)
	else:
		return False
	# END handle answer 
	
	return True


class FrameDecorator(ui.FrameLayout):
	"""A simple helper to wrap a box around a layout or control."""
	def __new__(cls, name, layoutCreator):
		"""Provide the name of the decorator, which will be wrapped around the layoutCreator, 
		which will be called to create the layout. It will be kept and mayde availale 
		through the 'layout' member, the currently available layout will not be changed."""
		self = super(FrameDecorator, cls).__new__(cls, label=name, borderStyle="etchedOut")
		self.layout = layoutCreator()
		self.setParentActive();
		return self
		
