# -*- coding: utf-8 -*-
"""Contains ui modules to build a finder-like browser for items of any kind"""
__docformat__ = "restructuredtext"
from mrv.interface import Interface
import mrv.maya.ui as ui
from mrv.maya.util import (	logException, OptionVarDict)

from mrv.path import Path

opts = OptionVarDict()

__all__ = ('iFinderProvider', 'iFinderFilter', 'iOptions',
			'FileProvider', 'Finder', 'FinderLayout', 
			'BookmarkControl', 'StackControl', 'FileOpenOptions', 
			'FileOpenFinder')


#{ Interfaces
class iFinderProvider(object):
	"""Interface defining the capabilities of a provider to be usable by a Finder
	control. Every finder as a root, which is used as basis for listing urls.
	
	Besides its function to provide sub-items for given urls, it is also used 
	to store recently selected items on a given level of a url. This memory
	allows the finder to restore common portions of URLs accordingly.
	
	The base implementation of the memorization feature already. """
	
	__slots__ = '_mem_items'
	
	#{ Configuration
	# if True, items of urls will be memorized, if False, this information
	# will be discarded
	memorize_urlItems = True
	#} END configuration
	
	def __init__(self, root):
		self._root = root
		self._mem_items = dict()
	
	#{ Interface 
	
	def urlItems(self, url):
		"""
		:return: list of string-like items which can be found at the given url.
		If this url is combined with one of the returned items separated by a slash, 
		a valid url is formed, i.e. url/item
		:param url: A given slash-separated url like base/subitem or '', which 
			requests items at the root of all urls"""
		raise NotImplementedError("To be implemented by subclass")
		
	def formatItem(self, url_base, url_index, url_item):
		"""Given the url_item, as well as additional information such as its base
		and its index inside of the url, this method encodes the item for presentation
		in the user interface.
		:param url_base: relative url at which the url_item resides. Is "" if url_index 
			is 0
		:param url_index: index representing the position of the url_item within the
			url
		:param url_item: item which is to be formatted.
		:return: string representing the formatted url."""
		return url_item
			
	def storeUrlItem(self, url_index, url_item):
		"""Stores and associates a given url_index with a url_item. Makes the stored
		item queryable by the ``storedUrlItemByIndex`` method
		:param url_index: index from 0 to n, where 0 corresponds to the first item
			in the url
		:param url_item: the string item to store at the given index"""
		if not self.memorize_urlItems:
			return
		# END ignore store call
		self._mem_items[url_index] = url_item
		
	def storedUrlItemByIndex(self, url_index):
		""":return: string item previously stored at the given index, or None 
		if there is no information available"""
		return self._mem_items.get(url_index, None)
		
	def root(self):
		""":return: string representing the file root"""
		return self._root
		
	#} END interface
	
class iFinderFilter(object):
	"""Filter interface suitable to perform item filter operations for Finder controls"""
	
	#{ Interface
	
	def filtered(self, finder, element_index, base_url, items):
		""":return: list of items which may be shown in the element at element_index
		:param finder: finder instance issueing the call
		:param element_index: index of the element which is to be filled with items
		:param base_url: url at which the given items exist
		:param items: list of relative item ids which are to be shown in the finder element"""
		return items
		
	#} END interface


class iOptions(object):
	"""Interface for all custom options layouts to be used with the FinderLayout. 
	They take a weak-reference to their parent FinderLayout allowing them to 
	set themselves up if necessary.
	The options they represent must be read by a custom implementation of the
	FinderLayout"""
	
	#{ Interface
	
	#} END interface

#} END interfaces

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
		
	
	
class FinderElement(ui.TextScrollList):
	"""Element with special abilities to suite the finder better. This involves
	keeping a list of unformatted items which can be used as unique item identifiers.
	
	Set the items to a list of unique identifiers which represent the possibly different
	items actually present in the list."""
	
	def __init__(self, *args, **kwargs):
		self.items = list()
		
	def selectedUnformattedItem(self):
		""":return: unformatted selected item or None"""
		index = self.selectedIndex()
		if index < 0:
			return None
		return self.items[index-1]
		
	def selectUnformattedItem(self, index_or_item):
		"""Select the unformatted item as identified by either the index or item
		:param index_or_item: integer representing the 0-based index of the item to 
			select, or the item's id
		:raise ValueError: if the item does not exist"""
		index = index_or_item
		if not isinstance(index_or_item, int):
			index = self.items.index(index_or_item)
		self.p_selectIndexedItem = index+1
			
		
class FilePathControl(ui.TextField):
	"""Control displaying a relative url. If it is ediable, a filepath may be 
	entered and queried"""
	
	#{ Interface
	def path(self):
		""":return: string representing the currently active path"""
		return self.p_text
		
	def setPath(self, path):
		"""Set the control to display the given path"""
		self.p_text = str(path)
		
	def setEditable(self, state):
		self.p_editable = state
		
	def editable(self):
		""":return: True if the control can be edited by the user"""
		return self.p_editable
	#} END interface
	
	
class BookmarkControl(ui.TextScrollList):
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
		self._bms = list()
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
		
	
	def _format_bookmark(self, root, path):
		if not root.endswith("/"):
			root += "/"
		return root + path
		
	def _selection_changed(self, *args):
		"""Convert the default callback into our signals"""
		root, path = self._bms[self.selectedIndex()-1]
		self.bookmark_changed.send(root, path)
		# as we are one-time actions only, deselect everything
		self.setSelectedItem(None)
		
	def addItem(self, bookmark):
		"""Add a new bookmark
		:param bookmark: tuple of root,relative_path or a single absolute path. In the 
			latter case, the root will be the natural root of the absolute path"""
		root, path = self._parse_bookmark(bookmark)
		bm_formatted = self._format_bookmark(root, path)
		# duplicate prevention
		if bm_formatted in self.items():
			return
		# END handle duplicates
		self._bms.append((root, path))
		super(BookmarkControl, self).addItem(bm_formatted)
		self._store_bookmark(root, path, add=True)
		
	def setItems(self, bookmarks):
		"""Set this control to a list of bookmarks
		:param bookmarks: list of either tuples of (root, path) pairs or absolute paths
			whose root will be chosen automatically"""
		bms = list()
		self._bms = list()
		for item in bookmarks:
			self._bms.append(self._parse_bookmark(item))
			bms.append(self._format_bookmark(*self._bms[-1]))
		# END for each item
		super(BookmarkControl, self).setItems(bms)
		
		# store all items together
		del(opts[self.k_bookmark_store])
		self._store_item_list(self._bms)
		
	def removeItem(self, bookmark):
		"""Remove the given bookmark from the list of bookmarks
		:param bookmark: full path to the bookmark to remove. Its not an error
			if it doesn't exist in the first place"""
		items = self.items()
		try:
			index = self.items().index(bookmark)
			root, path = self._bms[index]
			del(self._bms[index])
			super(BookmarkControl, self).removeItem(bookmark)
			self._store_bookmark(root, path, add=False)
		except ValueError:
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
	

class StackControl(ui.TextScrollList):
	"""Simple stack implementation"""


class FileOpenOptions(ui.ColumnLayout, iOptions):
	"""Options implementation providing options useful during file-open"""
	

class Finder(ui.EventSenderUI):
	"""The Finder control implements a finder-like browser, which displays URLs.
	URLs consist of items separated by the "/" character. Whenever a item is selected, 
	an iProvider compatible instance will be asked for the subitems of the corresponding URL. 
	Using these, a new field will be set up for presentation.
	A filter can be installed to prevent items from being shown.
	
	An added benefit is the ability to automatically match previously selected path
	items on a certain level of the URL with the available ones, allowing to quickly
	parse through URLs with a similar structure.
	
	A limitation of the current implementation is, that you can only keep one
	item selected at once in each url item area."""

	#{ Configuration
	t_element = FinderElement
	#} END configuration
	
	#{ Signals
	
	# s()
	selection_changed = ui.Signal()
	
	# s(url)
	url_changed = ui.Signal() 
	
	#} END signals
	
	def __init__(self, provider=None, filter=None):
		self._provider = None
		self._filter = None
		
		# initialize layouts
		self._form = ui.FormLayout()
		self._form.setParentActive()
		
		self.setProvider(provider)
		self.setFilter(filter)
		
	# { Query
	
	def provider(self):
		""":return: current url provider"""
		return self._provider
	
	def selectedUrl(self):
		""":return: string representing the currently selected, / separated URL, or
			None if there is no url selected"""
		items = list()
		for elm in self._form.listChildren():
			if not elm.p_manage:
				break
			sel_item = elm.selectedUnformattedItem()
			if sel_item is not None:
				items.append(sel_item)
			else:
				break
		# END for each element
		
		return "/".join(items) or None
		
	def numUrlElements(self):
		""":return: number of url elements that are currently shown. A url of 1/2 would
		have two url elements"""
		return len(tuple(c for c in self._form.listChildren() if c.p_manage))
		
	def selectedUrlItemByIndex(self, index):
		""":return: The selected url item at the given element index or None if nothing 
			is selected
		:param index: 0 to numUrlElements()-1
		:raies IndexError:"""
		return self._form.listChildren()[index].selectedUnformattedItem()
		
	def urlItemsByIndex(self, index):
		""":return: list of item ids which are currently being shown
		:param index: 0 based element index to numUrlElements()-1
		:raise IndexError:"""
		return list(self._form.listChildren()[index].items) 
		
	
	#} END Query
	
	#{ Edit
	
	def setFilter(self, filter=None):
		"""Set or unset a filter. All items will be sent through the filter, and will
		be shown only if they pass.
		:param filter: Functor called f(url,t) and returns True for each item which may
			be shown in the Finder. The url is the full relative url leading to, but 
			excluding the item t, whose visibility is being decided upon"""
		self._filter = filter
		
	def setProvider(self, provider=None):
		"""Set the provider to use
		:param provider: ``iFinderProvider`` compatible instance, or None
			If no provider is set, the instance will be blank"""
		if self._provider is provider:
			return
		# END early bailout
		self._provider = provider
		
		if provider is not None:
			self._set_element_visible(0)
		# END handle initial setup
		
		self.selection_changed.send()
		self.url_changed.send(self.selectedUrl())
	
	def _set_item_by_index(self, elm, index, item):
		self._set_element_visible(index)
		elm.selectUnformattedItem(item)
		self.provider().storeUrlItem(index, item)
		self._set_element_visible(index+1)
	
	def setItemByIndex(self, item, index):
		"""Set the given string item, which sits at the given index of a url
		:raise ValueError: if item does not exist at given index
		:raise IndexError: if index is not currently shown"""
		assert self.provider() is not None, "Provider is not set"
		elm = self._form.listChildren()[index]
		if elm.selectedUnformattedItem() == item:
			return
		# END early abort if nothing changes
		self._set_item_by_index(elm, index, item)
		
		self.selection_changed.send()
		self.url_changed.send(self.selectedUrl())
		
	def setUrl(self, url, require_all_items=True):
		"""Set the given url to be selected
		:param url: / separated relative url. The individual items must be available
			in the provider.
		:parm require_all_items: if False, the control will display as many items as possible.
			Otherwise it must display all given items, or raise ValueError"""
		assert self.provider() is not None, "Provider is not set"
		cur_url = self.selectedUrl()
		if cur_url == url:
			return
		# END ignore similar urls
		
		for eid, item in enumerate(url.split("/")):
			elm = self._form.listChildren()[eid]
			if elm.selectedUnformattedItem() == item:
				continue
			# END skip items which already match
			try:
				self._set_item_by_index(elm, eid, item)
			except ValueError:
				if not require_all_items:
					break
				# restore previous url
				self.setUrl(cur_url)
				raise
			# END handle exceptions
		# END for each item to set
		
		self.selection_changed.send()
		self.url_changed.send(self.selectedUrl())
		
		
		
	#} END edit
	
	#{ Callbacks
	
	@logException
	def _element_selection_changed(self, element, *args):
		"""Called whenever any element changes its value, which forces the following 
		elements to refresh"""
		index = self._index_by_item_element(element)
		# store the currently selected item
		self.provider().storeUrlItem(index, element.selectedUnformattedItem())
		self._set_element_visible(index+1)
		
		self.selection_changed.send()
		self.url_changed.send(self.selectedUrl())
		
	#} END callbacks
	
	#{ Utilities
	
	def _index_by_item_element(self, element):
		""":return: index matching the given item element, which must be one of our children"""
		assert '|' in element
		for cid, c in enumerate(self._form.listChildren()):
			if c == element:
				return cid
		# END for each child to enumerate
		raise ValueError("Didn't find element: %s" % element)
		
	def _set_element_items(self, start_elm_id, elements ):
		"""Fill the items from the start_elm_id throughout to all elements, until
		one url does not yield any items, or the item cannot be selected 
		:param elements: a full list of all available child elements."""
		
		# obtain the root url
		root_url = "/".join(c.selectedUnformattedItem() for c in elements[:start_elm_id])
		
		manage = True
		for elm_id in range(start_elm_id, len(elements)):
				
			# refill the items according to our provider
			elm = elements[elm_id]
			elm.p_manage=manage
			
			if not manage:
				continue
			# END abort if we just disable all others
			
			items = self.provider().urlItems(root_url)
			elm.items = items
			if not items:
				# keep one item visible, even though empty, if its the only one
				if len(elements) > 1:
					elm.p_manage=False
				manage=False
				continue
			# END skip on first empty url
			
			if elm.p_numberOfItems:
				elm.p_removeAll = True
			# END remove prior to re-append
			
			for item in items:
				elm.p_append = self.provider().formatItem(root_url, elm_id, item)
			# END for each item to append
			
			# try to reselect the previously selected item
			sel_item = self.provider().storedUrlItemByIndex(elm_id)
			if sel_item is None:
				# make sure next item is not being shown
				manage=False
				continue
			# END handle item memorization
			
			try:
				elm.selectUnformattedItem(sel_item)
			except (RuntimeError, ValueError):
				manage=False
				continue
			# END handle exception
			
			# update the root
			if root_url:
				root_url += "/"
			# END assure / is not the first character
			root_url += sel_item
		# END for each url to handle
		
	
	def _set_element_visible(self, index):
		"""Possibly create and fill the given element index, all following elements
		are set invivisble"""
		children = self._form.listChildren()
		
		# create as many new scrollLists as required,
		elms_to_create = max(0, (index+1) - len(children))
		if elms_to_create:
			self._form.setActive()
			for i in range(elms_to_create):
				# make sure we keep our array uptodate
				child = self._form.add(self.t_element(allowMultiSelection=False, font="smallFixedWidthFont"))
				children.append(child)
				
				child.e_selectCommand = self._element_selection_changed
				
				t, b, l, r = self._form.kSides
				m = 2
				
				# they are always attached top+bottom
				self._form.setup(	attachForm=((child, t, m), (child, b, m)),
									attachNone=(child, r)	)
				
				# we generally keep the right side un-attached
				if len(children) == 1:
					# first element goes left
					self._form.setup(attachForm=(child, l, m))
				else:
					# all other elements attach to the right side
					self._form.setup(attachControl=(child, l, m, children[-2]))
				# END handle amount of children
				# children.append(child)
			# END for each element to add
		# END if elms to create
		
		self._set_element_items(index, children)
		
	#} END utilities

#} END modules


#{ Layouts

class FinderLayout(ui.FormLayout):
	"""Implements a layout with a finder as well a surrounding elements. It can 
	be configured using class configuration variables, and allows easy modification
	through derivation
	
	**Instance Variables**
	* finder 
	* options"""
	
	#{ Configuration
	t_finder=Finder
	t_finder_provider = FileProvider
	t_filepath = FilePathControl
	t_options=None
	t_bookmarks=BookmarkControl
	t_root_selector=FileRootSelectorControl
	t_stack=None
	t_filter=FileFilterControl
	#} END configuration
	
	def __init__(self):
		"""Initialize all ui elements"""
		num_splits = 1 + (self.t_stack is not None) + (self.t_options is not None)
		config = (num_splits == 1 and "single") or "vertical%i" % num_splits
		pane = ui.PaneLayout(configuration=config)
		pane.p_paneSize=(1, 75, 100)
		
		try:
			pane.p_staticWidthPane=1
		except (RuntimeError, TypeError):
			# maya >= 2011
			pass
		# END exception handling
		
		# populate main pane
		if pane:
			self.finder = self.t_finder()
			
			if self.t_stack is not None:
				pass
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
				self.rootselector = self.t_root_selector()
				self.rootselector.root_changed = self.finder.setProvider
			# END root selector setup
			if self.t_bookmarks:
				self.bookmarks = self.t_bookmarks()
				self.bookmarks.bookmark_changed = self._on_bookmark_change
				
				# BOOKMARK POPUP
				pmenu = ui.PopupMenu()
				pmenu.e_postMenuCommand = self._build_bookmark_popup
			# END bookmarks setup
		# END left pane layout
		self.setActive()
		
		# FILTER ELEMENT
		################
		assert self.t_filter is not None, "Require filter element, replace it by a dummy filter if it is not required"
		self.filter = self.t_filter()
		fil = self.filter
		
		# attach the elements
		t, b, l, r = self.kSides
		m = 2
		self.setup(
					attachForm=(
								(fil, t, m),
								(fil, l, m),
								(fil, r, m),
								(lpane, l, m),
								(lpane, b, m),
								(pane, r, m),
								(fp, b, m),
								(fp, r, m),
								),
					
					attachNone=(
								(fp, t),
								(lpane, r),
								(fil, b),
								),
					
					attachControl=(
									(lpane, t, m, fil),
									(pane, t, m, fil),
									(pane, b, m, fp),
									(pane, l, m, lpane),
									(fp, l, m, lpane),
									),
					)
		# END setup
	
	#{ Callbacks

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
		if root == self.finder.provider().root() and self.finder.selectedUrl() == url:
			return
		# END early bailout
		
		if self.rootselector is None:
			ptype = type(self.finder.provider())
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
		self.finder.setUrl(url)
		
	#} END callbacks
	

class FileOpenFinder(FinderLayout):
	"""Finder customized for opening files"""
	
	#{ Configuration 
	t_stack=StackControl
	t_options=FileOpenOptions
	#} END configuration

#} END layouts
