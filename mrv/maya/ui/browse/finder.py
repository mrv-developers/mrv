# -*- coding: utf-8 -*-
__docformat__ = "restructuredtext"
import mrv.maya.ui as ui
from mrv.maya.util import (logException,)

from control import FinderElement

from util import concat_url

__all__ = ('Finder', )

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
	
	def layout(self):
		""":return: the finder's main layout which contains all controls"""
		return self._form
	
	def provider(self):
		""":return: current url provider"""
		return self._provider
	
	def selectedUrl(self, absolute=False):
		""":return: string representing the currently selected, / separated URL, or
			None if there is no url selected
		:param absolute: if True, an absolute URL will be provided using the provider's
			root"""
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
		
		url = "/".join(items) or None
		if absolute and url is not None:
			url = concat_url(self.provider().root(), url)
		# END handle absolute urls
		return url
		
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
		return list(self._form.listChildren()[index].base_items) 
		
	
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
		
	def setUrl(self, url, require_all_items=True, allow_memory=False):
		"""Set the given url to be selected
		:param url: / separated relative url. The individual items must be available
			in the provider.
		:parm require_all_items: if False, the control will display as many items as possible.
			Otherwise it must display all given items, or raise ValueError
		:param allow_memory: if true, provider memory may be used to show the longest chosen url, 
			being possibly more than you specify. Currently not implemented"""
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
			elm.base_items = items
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

