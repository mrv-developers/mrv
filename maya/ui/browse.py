# -*- coding: utf-8 -*-
"""Contains ui modules to build a finder-like browser for items of any kind"""
__docformat__ = "restructuredtext"
from mrv.interface import Interface
import mrv.maya.ui as ui
from mrv.maya.util import logException

from mrv.path import Path

__all__ = ('iFinderProvider', 'FileProvider', 'Finder', 'FinderLayout')


#{ Interfaces
class iFinderProvider(object):
	"""Interface defining the capabilities of a provider to be usable by a Finder
	control.
	
	Besides its function to provide sub-tokens for given urls, it is also used 
	to store recently selected items on a given level of a url. This memory
	allows the finder to restore common portions of URLs accordingly.
	
	The base implementation of the memorization feature already. """
	
	__slots__ = '_mem_tokens'
	
	#{ Configuration
	# if True, tokens of urls will be memorized, if False, this information
	# will be discarded
	memorize_url_tokens = True
	#} END configuration
	
	def __init__(self):
		self._mem_tokens = dict()
	
	#{ Interface 
	
	def url_tokens(self, url):
		"""
		:return: tuple of string-like tokens which can be found at the given url.
		If this url is combined with one of the returned tokens separated by a slash, 
		a valid url is formed, i.e. url/token
		:param url: A given slash-separated url like base/subitem or '', which 
			requests tokens at the root of all urls"""
		raise NotImplementedError("To be implemented by subclass")
			
	def store_url_token(self, url_index, url_token):
		"""Stores and associates a given url_index with a url_token. Makes the stored
		token queryable by the ``url_token_by_index`` method
		:param url_index: index from 0 to n, where 0 corresponds to the first token
			in the url
		:param url_token: the string token to store at the given index"""
		if not self.memorize_url_tokens:
			return
		# END ignore store call
		self._mem_tokens[url_index] = url_token
		
	def url_token_by_index(self, url_index):
		""":return: string token previously stored at the given index, or None 
		if there is no information available"""
		return self._mem_tokens.get(url_index, None)
		
	
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
		
	def url_tokens(self, url):
		path = self._root / url
		try:
			return tuple(abspath.basename() for abspath in path.listdir())
		except OSError:
			# ignore attempts to get path on a file for instance
			return tuple()
		# END exception handling
	
			
#} END utilities

#{ Modules

class Finder(ui.EventSenderUI):
	"""The Finder control implements a finder-like browser, which displays URLs.
	URLs consist of tokens separated by the "/" character. Whenever a token is selected, 
	an iProvider compatible instance will be asked for the subtokens of the corresponding URL. 
	Using these, a new field will be set up for presentation.
	A filter can be installed to prevent tokens from being shown.
	
	An added benefit is the ability to automatically match previously selected path
	tokens on a certain level of the URL with the available ones, allowing to quickly
	parse through URLs with a similar structure.
	
	A limitation of the current implementation is, that you can only keep one
	item selected at once in each url token area."""
	
	
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
		
	def num_url_tokens(self):
		""":return: number of url tokens that are currently shown. A url of 1/2 would
		have two url tokens"""
		return len(tuple(c for c in self._form.listChildren() if c.p_manage))
		
	def url_token_by_index(self, index):
		""":return: The selected url token at the given index
		:param index: 0 to num_url_tokens()-1
		:raies IndexError:"""
	
	#} END Query
	
	#{ Edit
	
	def set_filter(self, filter=None):
		"""Set or unset a filter. All items will be sent through the filter, and will
		be shown only if they pass.
		:param filter: Functor called f(url,t) and returns True for each token which may
			be shown in the Finder. The url is the full relative url leading to, but 
			excluding the token t, whose visibility is being decided upon"""
		self._filter = filter
		
	def set_provider(self, provider=None):
		"""Set the provider to use
		:param provider: ``iFinderProvider`` compatible instance, or None
			If no provider is set, the instance will be blank"""
		self._provider = provider
		
		if provider is not None:
			self._set_element_visible(0)
		# END handle initial setup
	
	def set_token(self, token, index):
		"""Set the given string token, which sits at the given index of a url
		:raise ValueError: if token does not exist at given index
		:raise IndexError: if index is not currently shown"""
		assert self.provider() is not None, "Provider is not set"
	
	def set_url(self, url, require_all_tokens=True):
		"""Set the given url to be selected
		:param url: / separated relative url. The individual tokens must be available
			in the provider.
		:parm require_all_tokens: if False, the control will display as many tokens as possible.
			Otherwise it must display all given tokens, or raise ValueError"""
		assert self.provider() is not None, "Provider is not set"
		
	#} END edit
	
	#{ Callbacks
	
	@logException
	def _element_selection_changed(self, element, *args):
		"""Called whenever any element changes its value, which forces the following 
		elements to refresh"""
		index = self._index_by_token_element(element)
		# store the currently selected item
		self.provider().store_url_token(index, element.selectedItem())
		self._set_element_visible(index+1)
		
	#} END callbacks
	
	#{ Utilities
	
	def _index_by_token_element(self, element):
		""":return: index matching the given token element, which must be one of our children"""
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
		root_url = "/".join(c.selectedItem() for c in elements[:start_elm_id])
		
		manage = True
		for elm_id in range(start_elm_id, len(elements)):
				
			# refill the items according to our provider
			elm = elements[elm_id]
			elm.p_manage=manage
			
			if not manage:
				continue
			# END abort if we just disable all others
			
			items = self.provider().url_tokens(root_url)
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
				elm.p_append = item
			# END for each item to append
			
			# try to reselect the previously selected item
			sel_item = self.provider().url_token_by_index(elm_id)
			if sel_item is None:
				# make sure next item is not being shown
				manage=False
				continue
			# END handle item memorization
			
			try:
				elm.p_selectItem = sel_item
			except RuntimeError:
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
				child = self._form.add(ui.TextScrollList(allowMultiSelection=False))
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
	t_options=None
	t_bookmarks=None
	t_root_selector=None
	t_stack=None
	t_filter=None
	#} END configuration
	
	def __init__(self):
		"""Initialize all ui elements"""
		num_splits = 1 + (self.t_stack is not None) + (self.t_options is not None)
		config = (num_splits == 1 and "single") or "vertical%i" % num_splits
		pane = ui.PaneLayout(configuration=config)
		pane.p_paneSize=(1, 75, 100)
		
		try:
			pane.p_staticWidthPane=1
		except RuntimeError:
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
		
		# attach the elements
		t, b, l, r = self.kSides
		m = 2
		self.setup(
					attachForm=(
								(pane, t, m),
								(pane, b, m),
								(pane, l, m),
								(pane, r, m),
								)
					)
		# END setup
	
	


#} END layouts
