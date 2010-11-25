# -*- coding: utf-8 -*-
"""Contains ui modules to build a finder-like browser for items of any kind"""
__docformat__ = "restructuredtext"

from interface import (iFinderProvider, iFinderFilter)

import mrv.maya.ui as ui
from mrv.maya.util import (OptionVarDict, logException )
from util import concat_url

from mrv.path import Path
opts = OptionVarDict()

__all__ = ( 'FileProvider', 'BookmarkControl',  
			'FilePathControl', 'FileFilterControl', 'FinderElement', 
			'FileStack', 'FileRootSelectorControl', 'FilePathControlEditable')



#{ Utilities

class FileProvider(iFinderProvider):
	"""Implements a provider for a file system"""
	__slots__ = "_root"
	
	def __init__(self, root):
		super(FileProvider, self).__init__(root)
		self._root = Path(self._root)
	
	def formatItem(self, url_base, url_index, url_item):
		return url_item
		
	def urlItems(self, url):
		"""Return directory items alphabetically, directories first"""
		path = self._root / url
		dirs, files = list(), list()
		
		try:
			for abs_path in path.listdir():
				if abs_path.isdir():
					dirs.append(abs_path)
				else:
					files.append(abs_path)
				# END sort by type
			# END for each listed path
			dirs.sort()
			files.sort()
			return [abspath.basename() for abspath in (dirs + files)] 
		except OSError:
			# ignore attempts to get path on a file for instance
			return list()
		# END exception handling
	

class StackControlBase(ui.TextScrollList):
	"""stack base implementation. A stack keeps multiple items which can be added 
	and removed. Additionally, it allows to remap the items, effectively showing 
	a formatted item, which is kept in sync with an unformatted item.
	:note: for now, only adding items, format will be applied. All other methods
		operate on the formatted items."""
	
	
	def __init__(self, *args, **kwargs):
		super(StackControlBase, self).__init__(*args, **kwargs)
		# unformatted items
		self.base_items = list()
		
	#{ Interface
	
	def formatItem(self, item):
		""":return: formatted version of item"""
		return item
		
	def selectedUnformattedItem(self):
		""":return: unformatted selected item or None"""
		index = self.selectedIndex()
		if index < 0:
			return None
		return self.base_items[index-1]
		
	def selectUnformattedItem(self, index_or_item):
		"""Select the unformatted item as identified by either the index or item
		:param index_or_item: integer representing the 0-based index of the item to 
			select, or the item's id
		:raise ValueError: if the item does not exist"""
		index = index_or_item
		if not isinstance(index_or_item, int):
			index = self.base_items.index(index_or_item)
		self.p_selectIndexedItem = index+1
		
	#} END Interface
	
	#{ Overridden Methods
	
	def removeItem(self, item):
		"""Remove the given formatted item from the list, as well as the corresponding
		unformtted item. Its not an error if the item does not exist"""
		try:
			index = self.items().index(item)
			del(self.base_items[index])
			super(StackControlBase, self).removeItem(item)
		except (ValueError, IndexError):
			pass
		# END exception handling
		return self
	
	def addItem(self, item):
		self.base_items.append(item)
		return super(StackControlBase, self).addItem(self.formatItem(item))
	
	#} END overridden methods
	
	
class FinderElement(StackControlBase):
	"""Element with special abilities to suite the finder better. This involves
	keeping a list of unformatted items which can be used as unique item identifiers.
	
	Set the items to a list of unique identifiers which represent the possibly different
	items actually present in the list."""
	
	
class FileStack(StackControlBase):
	"""Implements a stack which shows only the base names of files"""
	
	#{ Overrides 
	
	def formatItem(self, item):
		return Path(item).basename()
	
	#} END overrides
	
			
class FilePathControl(ui.TextField):
	"""Control displaying a relative url. If it is ediable, a filepath may be 
	entered and queried"""
	
	#{ Interface
	def path(self):
		""":return: string representing the currently active path"""
		return self.p_text
		
	def setPath(self, path):
		"""Set the control to display the given path"""
		if path is None:
			path = ''
		self.p_text = str(path)
		
	def setEditable(self, state):
		self.p_editable = state
		
	def editable(self):
		""":return: True if the control can be edited by the user"""
		return self.p_editable
	#} END interface
	

class FilePathControlEditable(FilePathControl):
	"""A filepath control which tries to maintain changes applied by the user.
	It assumes that the system will use setPath to adjust the path, and checks
	for changes in the path string which will be reapplied to the newly set path
	if possible"""
	
	def __init__(self, *args, **kwargs):
		super(FilePathControlEditable, self).__init__(*args, **kwargs)
		self._prev_path = ''
	
	def setPath(self, path):
		# figure out the changes - only care for append operations
		if path is not None:
			appended_text = self.p_text.replace(self._prev_path, '', 1)
			self._prev_path = path
			path += appended_text
		# END handle previous path
		super(FilePathControlEditable, self).setPath(path)
	
	
class BookmarkControl(StackControlBase):
	"""Control allowing to display a set of custom bookmarks, which are stored
	in optionVars"""
	#{ Configuration
	# Default name used to store bookmarks in optionVars. Adjust this id in case
	# you have different sets of bookmarks to store 
	k_bookmark_store = "MRV_bookmarks"
	#} END configuration
	
	#{ Signals
	# s(root, path)
	bookmark_changed = ui.Signal()
	#} END signals
	
	def __init__(self, *args, **kwargs):
		# fill ourselves with the stored bookmarks
		# List of tuples: root,relative_path
		super(BookmarkControl, self).__init__(*args, **kwargs)
		self.setItems(self._unpack_stored_bookmarks())
		self.e_selectCommand = self._selection_changed
	
	def _parse_bookmark(self, bookmark):
		""":return: root,path tuple or raise"""
		root, path = None, None
		if isinstance(bookmark, tuple) and len(bookmark) == 2:
			root, path = bookmark
		else:
			bookmark = Path(bookmark)
			root = bookmark.root()
			root_with_sep = (root.endswith(root.sep) and root) or (root + root.sep)
			path = Path(bookmark.replace(root_with_sep, '', 1))
		# END handle bookmark
		
		return root, path
	
	def _unpack_stored_bookmarks(self):
		""":return: list of tuples of root,path pairs"""
		miter = iter(opts.get(self.k_bookmark_store, list()))
		return [item for item in zip(miter, miter)]
	
	def _store_item_list(self, items):
		"""Store a list of pairs"""
		flattened_list = list()
		for pair in items:
			flattened_list.extend(pair)
		# END flatten list
		opts[self.k_bookmark_store] = flattened_list
	
	def _store_bookmark(self, root, path, add=True):
		"""Store the given path under the given root
		:param add: if True, the path will be added to the bookmarks of the given 
			root, otherwise it will be removed"""
		items = self._unpack_stored_bookmarks()
		index_to_remove = None
		for index, (oroot, opath) in enumerate(items):
			if oroot == root and opath == path:
				if add:
					return
				else:
					index_to_remove = index
					break
				# END skip existing
			# END similar item is stored already
		# END for each stored item
		
		if add:
			items.append((root, path))
		else:
			if index_to_remove is None:
				return
			# END ignore items that do not exist
			del(items[index_to_remove])
		# END end handle stored
		
		self._store_item_list(items)
		
	@logException
	def _selection_changed(self, *args):
		"""Convert the default callback into our signals"""
		if not self.base_items:
			return
		root, path = self.base_items[self.selectedIndex()-1]
		self.bookmark_changed.send(root, path)
		# as we are one-time actions only, deselect everything
		self.setSelectedItem(None)
		
	#{ StackControl Interface
	def formatItem(self, root_path_tuple):
		if isinstance(root_path_tuple, tuple):
			return Path(root_path_tuple[-1]).basename()
		else:
			return Path(root_path_tuple).basename()
	
	#} END stackcontrol interface
		
	def addItem(self, bookmark):
		"""Add a new bookmark
		:param bookmark: tuple of root,relative_path or a single absolute path. In the 
			latter case, the root will be the natural root of the absolute path"""
		root, path = self._parse_bookmark(bookmark)
		bm_formatted = self.formatItem((root, path))
		# duplicate prevention
		if bm_formatted in self.items():
			return
		# END handle duplicates
		self._store_bookmark(root, path, add=True)
		super(BookmarkControl, self).addItem((root, path))
		
		
	def setItems(self, bookmarks):
		"""Set this control to a list of bookmarks
		:param bookmarks: list of either tuples of (root, path) pairs or absolute paths
			whose root will be chosen automatically"""
		bms = list()
		self.base_items = list()
		for item in bookmarks:
			self.base_items.append(self._parse_bookmark(item))
			bms.append(self.formatItem(self.base_items[-1]))
		# END for each item
		super(BookmarkControl, self).setItems(bms)
		
		# store all items together
		del(opts[self.k_bookmark_store])
		self._store_item_list(self.base_items)
		
	def removeItem(self, bookmark):
		"""Remove the given bookmark from the list of bookmarks
		:param bookmark: full path to the bookmark to remove. Its not an error
			if it doesn't exist in the first place"""
		items = self.items()
		try:
			index = self.items().index(bookmark)
			root, path = self.base_items[index]
			super(BookmarkControl, self).removeItem(bookmark)
			self._store_bookmark(root, path, add=False)
		except (ValueError, IndexError):
			return
		# END exception handling
	
	
class FileRootSelectorControl(ui.TextScrollList):
	"""Keeps a list of possible roots which can be chosen. Each root is represented 
	by a Provider instance."""
	
	#{ Signals
	# s(Provider)
	root_changed = ui.Signal()
	#} END signals
	
	def __init__(self, *args, **kwargs):
		self._providers = list()
		self.e_selectCommand = self._selection_changed
	
	def _provider_by_root(self, root):
		""":return: provider instance having the given root, or None"""
		for p in self._providers:
			if p.root() == root:
				return p
			# END check match
		# END for each of our providers
		return None
	
	def setItems(self, providers):
		"""Set the given providers to be used by this instance
		:param providers: list of FileProvider instances"""
		for provider in providers:
			if not isinstance(provider, FileProvider):
				raise ValueError("Require %s instances" % FileProvider)
			# END verify type
		# END for each provider
		self._providers = providers
		super(FileRootSelectorControl, self).setItems(p.root() for p in self._providers)
		
	def addItem(self, provider):
		"""Add the given provider to our list of provides"""
		super(FileRootSelectorControl, self).addItem(provider.root())
		self._providers.append(provider)
		
	def removeItem(self, provider):
		"""Remove the given provider from the list
		:param provider: FileProvider instance or root from which the provider
			can be determined"""
		if isinstance(provider, basestring):
			provider = self._provider_by_root(provider)
			if provider is None:
				return
			# END abort if not found
		# END handle provider type
		
		try:
			self._providers.remove(provider)
		except ValueError:
			return
		else:
			self.setItems(self._providers)
		# END exception handling
		
	def setSelectedItem(self, item):
		"""Fires a root_changed event if the item actually caused a selection change"""
		cur_index = self.selectedIndex()
		super(FileRootSelectorControl, self).setSelectedItem(item)
		if cur_index == self.selectedIndex():
			return
		# END skip if no change
		self._selection_changed()
		
		
	#{ Interface
	
	def providers(self):
		""":return: list of currently used providers"""
		return list(self._providers)
		
	#} END interface
	
	#{ Callbacks
	
	def _selection_changed(self, *args):
		index = self.selectedIndex()-1
		self.root_changed.send(self._providers[index])
	#} END callbacks
		
#} END utilities

#{ Modules

class FileFilterControl(ui.FormLayout, iFinderFilter):
	"""Control providing a filter for finder urls which are file paths"""
	



#} END modules



