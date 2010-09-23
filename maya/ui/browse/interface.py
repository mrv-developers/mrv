# -*- coding: utf-8 -*-
"""module with interfaces to define contracts"""
__docformat__ = "restructuredtext"
from mrv.interface import Interface

__all__ = ('iFinderProvider', 'iOptions', 'iFinderFilter')

class iFinderProvider(Interface):
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
	
class iFinderFilter(Interface):
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


class iOptions(Interface):
	"""Interface for all custom options layouts to be used with the FinderLayout. 
	They take a weak-reference to their parent FinderLayout allowing them to 
	set themselves up if necessary.
	The options they represent must be read by a custom implementation of the
	FinderLayout"""
	
	#{ Interface
	
	#} END interface

