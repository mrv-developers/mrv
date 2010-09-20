# -*- coding: utf-8 -*-
"""Contains misc utiltiies"""
__docformat__ = "restructuredtext"

import mrv.maya.ui as ui

def concat_url(root, path):
	if not root.endswith("/"):
		root += "/"
	return root + path

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
