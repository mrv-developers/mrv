# -*- coding: utf-8 -*-
"""module containing layouts which combine finder ui modules"""
__docformat__ = "restructuredtext"
import sys
import string

from mrv.path import Path

from control import *
from finder import *
from option import *

from util import ( FrameDecorator, handleUnsavedModifications )

import mrv.maya.ui as ui
import mrv.maya
from mrv.maya.util import (logException, notifyException)

from mrv.maya.ref import FileReference
import maya.utils as mutil
import maya.cmds as cmds

__all__ = ('FinderLayout', 'FileOpenFinder', 'FileReferenceFinder', 'FileSaveFinder')

class FinderLayout(ui.FormLayout):
	"""Implements a layout with a finder as well a surrounding elements. It can 
	be configured using class configuration variables, and allows easy modification
	through derivation
	
	**Instance Variables**
	* finder 
	* options"""
	
	#{ Configuration
	# used as names for buttons
	k_confirm_name = "OK"
	k_cancel_name = "Cancel"
	k_stack_item_remove_name = "Remove Item"
	
	t_finder=Finder
	t_finder_provider = FileProvider
	t_filepath = FilePathControl
	t_options=None
	t_bookmarks=BookmarkControl
	t_root_selector=FileRootSelectorControl
	t_stack=None
	t_filter=FileFilterControl
	#} END configuration
	
	def __new__(cls, *args, **kwargs):
		return super(FinderLayout, cls).__new__(cls)
	
	def __init__(self, *args, **kwargs):
		"""Initialize all ui elements
		:param kwargs: The following keywords are defined
		 * **defaultRoots**: default False, if True, show all roots available
		  on the system."""
		num_splits = 1 + (self.t_options is not None)
		config = (num_splits == 1 and "single") or "vertical%i" % num_splits
		pane = ui.PaneLayout(configuration=config)
		pane.p_paneSize=(1, 75, 100)
		
		# attach the elements
		t, b, l, r = self.kSides
		m = 2
		
		try:
			pane.p_staticWidthPane=1
		except (RuntimeError, TypeError):
			# maya >= 2011
			pass
		# END exception handling
		
		# populate main pane
		if pane:
			if self.t_stack is not None:
				finder_form = ui.FormLayout()
				if finder_form:
					
					sdc = FrameDecorator("Stack", self.t_stack)
					self.stack = sdc.layout
					popup = ui.PopupMenu(markingMenu=True)
					self._create_stack_menu(popup)
					
					
					fdc = FrameDecorator("Finder", self.t_finder)
					self.finder = fdc.layout
					fi, st = fdc, sdc
					
					finder_form.setup(
											attachForm=(
															(fi, t, m),
															(fi, b, m),
															(fi, l, m),
															(st, t, m),
															(st, b, m),
															(st, r, m),
														),
											attachNone=(
															(st, l)
														),
											attachControl=(
															(fi, r, m, st)
															)
										)
				# END finder form
				self.setActive()
			else:
				self.finder = self.t_finder()
			# END handle stack
			
			# setup RMB menu
			finder_popup = ui.PopupMenu(markingMenu=True)
			self._create_finder_menu(finder_popup)
			# END popupMenu
			
			if self.t_options is not None:
				self.options = self.t_options()
		# END pane layout
		self.setActive()
		
		# if we have a filter, set it to the finder
		
		# FILEPATH
		##########
		fp = self.t_filepath()
		fp.setEditable(False)
		self.fpctrl = fp
		self.finder.url_changed = fp.setPath
		
		
		# BOOKMARKS AND SELECTOR
		########################
		num_panes = (self.t_bookmarks is not None) + (self.t_root_selector is not None)
		assert num_panes, "Require at least one bookmark type or a selector type"
		
		config = "horizontal%i" % num_panes
		lpane = ui.PaneLayout(configuration=config)
		
		if lpane:
			self.rootselector, self.bookmarks = None, None
			if self.t_root_selector:
				rdc = FrameDecorator("Roots", self.t_root_selector)
				self.rootselector = rdc.layout
				self.rootselector.root_changed = self.finder.setProvider
				
				if kwargs.get('defaultRoots', False):
					roots = list()
					if not sys.platform.startswith('win'):
						roots.append(Path("/"))
					else:
						# just try all accessible drives
						for letter in string.ascii_uppercase:
							try:
								p = Path(letter + ":\\")
								p.stat()
								roots.append(p)
							except OSError:
								continue
							# END ignore exceptions
						# END for each letter
					# END handle roots
					
					if self.t_finder_provider is not None:
						for rootpath in roots:
							self.rootselector.addItem(self.t_finder_provider(rootpath))
						# END for each rootpath
						if roots:
							self.rootselector.setSelectedItem(roots[0])
					# END if we have a provider type
				# END handle default roots
			# END root selector setup
			lpane.setActive()
			if self.t_bookmarks:
				bdc = FrameDecorator("Bookmarks", self.t_bookmarks)
				self.bookmarks = bdc.layout
				self.bookmarks.bookmark_changed = self._on_bookmark_change
				
				# BOOKMARK POPUP
				pmenu = ui.PopupMenu(markingMenu=True)
				pmenu.e_postMenuCommand = self._build_bookmark_popup
			# END bookmarks setup
		# END left pane layout
		self.setActive()
		
		# FILTER ELEMENT
		################
		assert self.t_filter is not None, "Require filter element, replace it by a dummy filter if it is not required"
		self.filter = self.t_filter()
		fil = self.filter
		self.setActive()
		
		
		# BUTTONS
		#########
		bl = self._create_button_layout()
		
		
		# CONTROL ASSEMBLY
		##################
		self.setup(
					attachForm=(
								(fil, t, m),
								(fil, l, m),
								(fil, r, m),
								(lpane, l, m),
								(lpane, b, m),
								(pane, r, m),
								(fp, b, m),
								(bl, r, m),
								(bl, b, m),
								),
					
					attachNone=(
								(fp, t),
								(lpane, r),
								(fil, b),
								(bl, l),
								(bl, t),
								),
					
					attachControl=(
									(lpane, t, m, fil),
									(pane, t, m, fil),
									(pane, b, m, bl),
									(pane, l, m, lpane),
									(fp, l, m, lpane),
									(fp, r, m, bl),
									),
					)
		# END setup
	
	#{ Subclass Interface
	
	def _create_finder_menu(self, menu):
		"""Create a static menu for the finder. The active parent is a popupMenu
		at the time of this call. The default buttons allow to quickly confirm
		and cancel.
		If a stack is present, items can be added to it"""
		mi = ui.MenuItem(rp="SW", label=self.k_cancel_name)
		mi.e_command = self._cancel_button_pressed
		
		mi = ui.MenuItem(rp="SE", label=self.k_confirm_name)
		mi.e_command = self._confirm_button_pressed
		
		
	def _create_stack_menu(self, menu):
		mi = ui.MenuItem(label=self.k_stack_item_remove_name, rp="W")
		mi.e_command = self._on_stack_remove_item
		
	def _create_button_layout(self):
		"""Create a layout with two main buttons, one to confirm, the other 
		to cancel the operation
		:return: parent layout containing the buttons"""
		bform = ui.FormLayout()
		
		if bform:
			okb = ui.Button(label=self.k_confirm_name)
			okb.e_released = self._confirm_button_pressed
			
			cnclb = ui.Button(label=self.k_cancel_name)
			cnclb.e_released = self._cancel_button_pressed
		# END create buttons
		self.setActive()
		
		t, b, l, r = self.kSides
		m = 2
		bform.setup(
					attachForm=(
									(okb, t, m),
									(okb, b, m),
									(okb, l, m),
									(cnclb, t, m),
									(cnclb, b, m),
									(cnclb, r, m),
								),
					attachNone=(
									(okb, r),
								),
					attachControl=(
									(cnclb, l, m, okb),
									)
					)
		# END setup
		
		return bform
	
	#}END subclass interface
	
	#{ Callbacks
	
	def _on_stack_remove_item(self, *args):
		self.stack.removeItem(self.stack.selectedItem())
	
	def _close_parent_window(self):
		"""helper routine closing the parent window if there is one"""
		p = self.parent()
		if isinstance(p, ui.Window):
			# If its not deferred, it will crash maya for some reason, maybe
			# something related to garbage collection.
			mutil.executeDeferred(self.parent().delete)
		elif isinstance(p, ui.FormLayout) and p.startswith('layoutDialog'):
			cmds.layoutDialog(dismiss='close')
		# END close window

	def _confirm_button_pressed(self, *args):
		"""Called when the ok button was pressed to finalize the operation"""
		self._close_parent_window()
		
	def _cancel_button_pressed(self, *args):
		"""Called when the cancel button was pressed, terminating the operation without
		any changes.
		:note: if our parent is a window, we will close it through deletion"""
		self._close_parent_window()

	def _build_bookmark_popup(self, popup, *args):
		popup.p_deleteAllItems = True
		popup.setActive()
		
		mi = ui.MenuItem(label="Add Bookmark")
		mi.p_enable = self.finder.selectedUrl() is not None
		if mi.p_enable:
			mi.e_command = self._on_add_bookmark
		# END setup command
		
		mi = ui.MenuItem(label="Remove Bookmark")
		mi.p_enable = len(self.bookmarks.selectedItems()) == 1
		if mi.p_enable:
			mi.e_command = self._on_remove_bookmark
		# END setup command 

	@logException
	def _on_add_bookmark(self, item, *args):
		url = self.finder.selectedUrl()
		provider = self.finder.provider()
		
		if not hasattr(provider, 'root'):
			raise TypeError("Provider doesn't support the 'root' method")
		# END verify interface
		
		self.bookmarks.addItem((provider.root(), url))

	@logException
	def _on_remove_bookmark(self, item, *args):
		self.bookmarks.removeItem(self.bookmarks.selectedItems()[0])

	@logException
	def _on_bookmark_change(self, root, url):
		"""Propagate changed bookmarks to changed roots. If necessary, add a new
		root to the root selector. Otherwise just set the root and url of the finder"""
		cur_provider = self.finder.provider()
		if cur_provider and root == cur_provider.root() and self.finder.selectedUrl() == url:
			return
		# END early bailout
		
		if self.rootselector is None:
			ptype = type(cur_provider)
			assert ptype is not type(None), "Finder needs provider to be set beforehand"
			self.finder.setProvider(ptype(root))
		else:
			actual_provider = None
			root_item = root
			# find a provider matching the root - if not, add it
			for provider in self.rootselector.providers():
				if provider.root() == root:
					actual_provider = provider
					break
				# END handle provider match
			# END for each provider
			
			if actual_provider is None:
				actual_provider = self.t_finder_provider(root)
				self.rootselector.addItem(actual_provider)
			# END add a new provider to root selector
			
			self.rootselector.setSelectedItem(root_item)
		# END handle existance of rootselector
		self.finder.setUrl(url, allow_memory=False)
		
	#} END callbacks


class FileSaveFinder(FinderLayout):
	"""Finder optimized to choose a location to save a file"""
	#{ Configuration 
	k_confirm_name = "Save File"
	t_stack = None
	
	t_filepath = FilePathControlEditable
	t_options=None
	#} END configuration
	
	def __init__(self, *args, **kwargs):
		super(FileSaveFinder, self).__init__(*args, **kwargs)
		self.bookmarks.k_bookmark_store = "MRV_SAVE_Bookmarks"
		
		# filepath field is editable in this case
		self.fpctrl.setEditable(True)
		
	@notifyException
	def _confirm_button_pressed(self, *args, **kwargs):
		save_path = self.finder.provider().root() / self.fpctrl.path()
		mrv.maya.Scene.save(save_path)
		
		super(FileSaveFinder, self)._confirm_button_pressed(*args, **kwargs)
		

class FileOpenFinder(FinderLayout):
	"""Finder customized for opening files"""
	
	#{ Configuration 
	k_confirm_name = "Open File"
	t_stack = None
	
	t_options=FileOpenOptions
	#} END configuration
	
	def __init__(self, *args, **kwargs):
		super(FileOpenFinder, self).__init__(*args, **kwargs)
		self.bookmarks.k_bookmark_store = "MRV_OPEN_Bookmarks"
		
	@notifyException
	def _confirm_button_pressed(self, *args):
		"""Called when the ok button was pressed to finalize the operation"""
		fileToOpen = self.finder.selectedUrl(absolute=True)
		opts = self.options.fileOptions() 
		opts['open'] = True
		if not handleUnsavedModifications():
			print "Cancelled by User"
			return
		# END handle modification
		cmds.file(fileToOpen, **opts)
		super(FileOpenFinder, self)._confirm_button_pressed()


class FileReferenceFinder(FinderLayout):
	"""Finder Layout for creating references"""

	#{ Configuration
	
	k_add_single = "Add to Stack"
	k_add_and_confirm = "Add to Stack and Confirm"
	k_confirm_name = "Create Reference(s)"
	k_stack_item_remove_name = "Remove File from Stack"
	
	t_stack=FileStack
	t_options=None
	#} END configuration
	
	def __init__(self, *args, **kwargs):
		super(FileReferenceFinder, self).__init__(*args, **kwargs)
		self.bookmarks.k_bookmark_store = "MRV_REF_Bookmarks"
	
	def _create_finder_menu(self, menu):
		super(FileReferenceFinder, self)._create_finder_menu(menu)
		mi = ui.MenuItem(label=self.k_add_single, rp="E")
		mi.e_command = self._on_add_to_stack
		
		mi = ui.MenuItem(label=self.k_add_and_confirm, rp="NE")
		mi.e_command = self._on_add_to_stack
	
	
	#{ Subclass Interface
	
	def _create_references(self, refpaths):
		"""Create reference to the given reference paths, being strings to the file 
		in question"""
		for ref in refpaths:
			FileReference.create(ref)
		# END for each ref to create
	
	#} END subclass interface

	#{ Callbacks
	
	@notifyException
	def _on_add_to_stack(self, menu_item, *args):
		prov = self.finder.provider()
		if prov is None:
			raise AssertionError("Finder is not setup")
		
		# default is always add
		url = self.finder.selectedUrl(absolute=True)
		if url is None:
			raise ValueError("Please select a path and retry")
		# END handle nothing selected
		
		self.stack.addItem(url)
		
		if menu_item.p_label == self.k_add_and_confirm:
			self._confirm_button_pressed()
		# END handle confirm
	
	@notifyException
	def _confirm_button_pressed(self, *args):
		if not self.stack.base_items:
			raise ValueError("Please add at least one item to the stack and retry")
		# END handle empty refs
		
		# create refs
		self._create_references(self.stack.base_items)
		
		# finally let base take care of the rest
		# NOTE: Needs to be deferred, crashes otherwis
		mutil.executeDeferred(super(FileReferenceFinder, self)._confirm_button_pressed)
		
	
	#} END callbacks
