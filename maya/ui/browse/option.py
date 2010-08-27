# -*- coding: utf-8 -*-
"""module with option implementations, to be shown in finder layouts"""
__docformat__ = "restructuredtext"

from interface import iOptions
import mrv.maya.ui as ui

class FileOpenOptions(ui.ColumnLayout, iOptions):
	"""Options implementation providing options useful during file-open"""
	
