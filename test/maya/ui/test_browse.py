# -*- coding: utf-8 -*-
from mrv.test.maya import *
from util import *

from mrv.path import make_path
from mrv.maya.ui.browse import *

import mrv.maya.ui as ui
from mrv.test.maya.ui import instructor

import maya.cmds as cmds

if not cmds.about(batch=1):
	class TestItemBrowser(unittest.TestCase):
		def test_layout(self):
			
			root = make_path(__file__).dirname().dirname().dirname().dirname()
			
			
			win = ui.Window(title="Finder")
			main = FileOpenFinder()
			
			# setup finder
			main.finder.set_provider(FileProvider(root))
			
			finder = main.finder
			
			win.show()
			
			# FINDER TESTING
			################
			# without interaction, nothing is selected
			assert finder.provider() is not None
			assert finder.selected_url() is None
			
			# when setting a root, we have at least that
			assert finder.num_url_elements() == 1
			
			assert finder.selected_url_item_by_index(0) is None
			self.failUnlessRaises(IndexError, finder.selected_url_item_by_index, 1)
			
			
			# selection
			items = finder.url_items_by_index(0)
			self.failUnlessRaises(IndexError, finder.url_items_by_index, 1)
			
			assert items
			for item in items:
				finder.set_item_by_index(item, 0)
				assert finder.selected_url_item_by_index(0) == item
				assert finder.selected_url() == item
			# END for each item to select
			
			self.failUnlessRaises(IndexError, finder.set_item_by_index, item, 100)
			self.failUnlessRaises(ValueError, finder.set_item_by_index, "doesntexist", 0)
			
			# more complex url selection
			url_short = "ext/pydot"
			url = "ext/pyparsing/src"
			url_invalid = url_short + "/doesntexist"
			
			finder.set_url(url)
			assert finder.selected_url() == url
			
			# require_all_items test - failure does not change existing value
			self.failUnlessRaises(ValueError, finder.set_url, url_invalid)
			assert finder.selected_url() == url
			
			finder.set_url(url_invalid, require_all_items=False)
			assert finder.selected_url() == url_short
			
			
			# ROOT_PROVIDER
			###############
			root2 = root.dirname()
			selector = main.rootselector
			self.failUnlessRaises(ValueError, selector.set_items, [root])
			selector.set_items([FileProvider(root), FileProvider(root2)])
			assert len(selector.providers()) == 2  
			
			# test removal - root path - nonexisting okay
			selector.remove_item("something")
			assert len(selector.providers()) == 2
			
			# remove by root
			selector.remove_item(root2)
			assert len(selector.providers()) == 1 and len(selector.items()) == 1  
			
			# re-add previous item
			selector.add_item(FileProvider(root2))
			assert len(selector.providers()) == 2 and len(selector.items()) == 2
			
			
			# BOOKMARKS
			###########
			bookmarks = main.bookmarks
			assert len(bookmarks.items()) == 0
			
			bookmarks.add_item(root)
			assert len(bookmarks.items()) == 1
			assert bookmarks.items()[0] == root
			
			# duplicate check
			bookmarks.add_item(root)
			assert len(bookmarks.items()) == 1
			
			root2_bm = (root2, 'git')
			bookmarks.add_item(root2_bm)
			assert len(bookmarks.items()) == 2
			
			# remove - ignores non-existing
			bookmarks.remove_item("doesntexist")
			assert len(bookmarks.items()) == 2
			
			# remove 
			bookmarks.remove_item(root)
			assert len(bookmarks.items()) == 1
			
			bookmarks.set_items([root, root2_bm])
			assert len(bookmarks.items()) == 2
			
			
			
			
			
