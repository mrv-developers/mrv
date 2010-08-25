# -*- coding: utf-8 -*-
"""Contains ui modules to build a finder-like browser for items of any kind"""
__docformat__ = "restructuredtext"
from mrv.interface import Interface
import mrv.maya.ui as ui
from mrv.maya.util import logException

from mrv.path import Path

__all__ = ('iFinderProvider', 'iFinderFilter', 'iSelector', 'iOptions',
			'FileProvider', 'Finder', 'FinderLayout', 'SelectorControl', 
			'BookmarkControl', 'StackControl', 'FileOpenOptions', 
			'FileOpenFinder')


#{ Interfaces
class iFinderProvider(object):
	"""Interface defining the capabilities of a provider to be usable by a Finder
	control.
	
	Besides its function to provide sub-items for given urls, it is also used 
	to store recently selected items on a given level of a url. This memory
	allows the finder to restore common portions of URLs accordingly.
	
	The base implementation of the memorization feature already. """
	
	__slots__ = '_mem_items'
	
	#{ Configuration
	# if True, items of urls will be memorized, if False, this information
	# will be discarded
	memorize_url_items = True
	#} END configuration
	
	def __init__(self):
		self._mem_items = dict()
	
	#{ Interface 
	
	def url_items(self, url):
		"""
		:return: list of string-like items which can be found at the given url.
		If this url is combined with one of the returned items separated by a slash, 
		a valid url is formed, i.e. url/item
		:param url: A given slash-separated url like base/subitem or '', which 
			requests items at the root of all urls"""
		raise NotImplementedError("To be implemented by subclass")
		
	def format_item(self, url_base, url_index, url_item):
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
			
	def store_url_item(self, url_index, url_item):
		"""Stores and associates a given url_index with a url_item. Makes the stored
		item queryable by the ``stored_url_item_by_index`` method
		:param url_index: index from 0 to n, where 0 corresponds to the first item
			in the url
		:param url_item: the string item to store at the given index"""
		if not self.memorize_url_items:
			return
		# END ignore store call
		self._mem_items[url_index] = url_item
		
	def stored_url_item_by_index(self, url_index):
		""":return: string item previously stored at the given index, or None 
		if there is no information available"""
		return self._mem_items.get(url_index, None)
		
	
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

class iSelector(object):
	"""Interface representing a stack of items, effectively being a simple list
	of items that can be appended to and queried"""
	

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
		""":param root: Path representing the root file url, as path into the file system"""
		super(FileProvider, self).__init__()
		self._root = root

	def format_item(self, url_base, url_index, url_item):
		return url_item
		
	def url_items(self, url):
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
		
	def selected_unformatted_item(self):
		""":return: unformatted selected item or None"""
		index = self.selectedIndex()
		if index < 0:
			return None
		return self.items[index-1]
		
	def select_unformatted_item(self, index_or_item):
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
		
	def set_path(self, path):
		"""Set the control to display the given path"""
		self.p_text = str(path)
		
	def set_editable(self, state):
		self.p_editable = state
		
	def editable(self):
		""":return: True if the control can be edited by the user"""
		return self.p_editable
	#} END interface
	
	
class SelectorControl(ui.TextScrollList, iSelector):
	"""Control allowing to select items, selection changes trigger an event"""
	
	
class BookmarkControl(SelectorControl):
	"""Control allowing to display a set of custom bookmarks, which are stored
	in optionVars"""
	
	
#} END utilities

#{ Modules

class FileFilterControl(ui.FormLayout, iFinderFilter):
	"""Control providing a filter for finder urls which are file paths"""
	

class StackControl(SelectorControl):
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
		# initialize layouts
		self._form = ui.FormLayout()
		self._form.setParentActive()
		
		self.set_provider(provider)
		self.set_filter(filter)
		
	# { Query
	
	def provider(self):
		""":return: current url provider"""
		return self._provider
	
	def selected_url(self):
		""":return: string representing the currently selected, / separated URL, or
			None if there is no url selected"""
		items = list()
		for elm in self._form.listChildren():
			if not elm.p_manage:
				break
			sel_item = elm.selected_unformatted_item()
			if sel_item is not None:
				items.append(sel_item)
			else:
				break
		# END for each element
		
		return "/".join(items) or None
		
	def num_url_elements(self):
		""":return: number of url elements that are currently shown. A url of 1/2 would
		have two url elements"""
		return len(tuple(c for c in self._form.listChildren() if c.p_manage))
		
	def selected_url_item_by_index(self, index):
		""":return: The selected url item at the given element index or None if nothing 
			is selected
		:param index: 0 to num_url_elements()-1
		:raies IndexError:"""
		return self._form.listChildren()[index].selected_unformatted_item()
		
	def url_items_by_index(self, index):
		""":return: list of item ids which are currently being shown
		:param index: 0 based element index to num_url_elements()-1
		:raise IndexError:"""
		return list(self._form.listChildren()[index].items) 
		
	
	#} END Query
	
	#{ Edit
	
	def set_filter(self, filter=None):
		"""Set or unset a filter. All items will be sent through the filter, and will
		be shown only if they pass.
		:param filter: Functor called f(url,t) and returns True for each item which may
			be shown in the Finder. The url is the full relative url leading to, but 
			excluding the item t, whose visibility is being decided upon"""
		self._filter = filter
		
	def set_provider(self, provider=None):
		"""Set the provider to use
		:param provider: ``iFinderProvider`` compatible instance, or None
			If no provider is set, the instance will be blank"""
		self._provider = provider
		
		if provider is not None:
			self._set_element_visible(0)
		# END handle initial setup
	
	def _set_item_by_index(self, elm, index, item):
		self._set_element_visible(index)
		elm.select_unformatted_item(item)
		self.provider().store_url_item(index, item)
		self._set_element_visible(index+1)
	
	def set_item_by_index(self, item, index):
		"""Set the given string item, which sits at the given index of a url
		:raise ValueError: if item does not exist at given index
		:raise IndexError: if index is not currently shown"""
		assert self.provider() is not None, "Provider is not set"
		elm = self._form.listChildren()[index]
		if elm.selected_unformatted_item() == item:
			return
		# END early abort if nothing changes
		self._set_item_by_index(elm, index, item)
		
		self.selection_changed.send()
		self.url_changed.send(self.selected_url())
		
	def set_url(self, url, require_all_items=True):
		"""Set the given url to be selected
		:param url: / separated relative url. The individual items must be available
			in the provider.
		:parm require_all_items: if False, the control will display as many items as possible.
			Otherwise it must display all given items, or raise ValueError"""
		assert self.provider() is not None, "Provider is not set"
		cur_url = self.selected_url()
		if cur_url == url:
			return
		# END ignore similar urls
		
		for eid, item in enumerate(url.split("/")):
			elm = self._form.listChildren()[eid]
			if elm.selected_unformatted_item() == item:
				continue
			# END skip items which already match
			try:
				self._set_item_by_index(elm, eid, item)
			except ValueError:
				if not require_all_items:
					break
				# restore previous url
				self.set_url(cur_url)
				raise
			# END handle exceptions
		# END for each item to set
		
		self.selection_changed.send()
		self.url_changed.send(self.selected_url())
		
		
		
	#} END edit
	
	#{ Callbacks
	
	@logException
	def _element_selection_changed(self, element, *args):
		"""Called whenever any element changes its value, which forces the following 
		elements to refresh"""
		index = self._index_by_item_element(element)
		# store the currently selected item
		self.provider().store_url_item(index, element.selected_unformatted_item())
		self._set_element_visible(index+1)
		
		self.selection_changed.send()
		self.url_changed.send(self.selected_url())
		
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
		root_url = "/".join(c.selected_unformatted_item() for c in elements[:start_elm_id])
		
		manage = True
		for elm_id in range(start_elm_id, len(elements)):
				
			# refill the items according to our provider
			elm = elements[elm_id]
			elm.p_manage=manage
			
			if not manage:
				continue
			# END abort if we just disable all others
			
			items = self.provider().url_items(root_url)
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
				elm.p_append = self.provider().format_item(root_url, elm_id, item)
			# END for each item to append
			
			# try to reselect the previously selected item
			sel_item = self.provider().stored_url_item_by_index(elm_id)
			if sel_item is None:
				# make sure next item is not being shown
				manage=False
				continue
			# END handle item memorization
			
			try:
				elm.select_unformatted_item(sel_item)
			except (RuntimeError, ValueError):
				manage=False
				continue
			# END handle exception
			
			# update the root
			root_url += "/%s" % sel_item
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
	has_bookmarks=False
	has_root_selector=False
	has_filter=False
	
	t_finder=Finder
	t_finder_provider = FileProvider
	t_filepath = FilePathControl
	t_options=None
	t_bookmarks=BookmarkControl
	t_root_selector=SelectorControl
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
		fp.set_editable(False)
		self.fpctrl = fp
		self.finder.url_changed = fp.set_path
		
		
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
			# END root selector setup
			if self.t_bookmarks:
				self.bookmarks = self.t_bookmarks()
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
	
	

class FileOpenFinder(FinderLayout):
	"""Finder customized for opening files"""
	
	#{ Configuration 
	t_stack=StackControl
	t_options=FileOpenOptions
	#} END configuration

#} END layouts
