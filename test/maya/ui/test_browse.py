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
			
			
			win = ui.Window(title="File Reference")
			main = FileReferenceFinder()
			
			# setup finder
			main.finder.setProvider(FileProvider(root))
			
			finder = main.finder
			win.show()
			
			# FINDER TESTING
			################
			# without interaction, nothing is selected
			assert finder.provider() is not None
			assert finder.selectedUrl() is None
			
			# when setting a root, we have at least that
			assert finder.numUrlElements() == 1
			
			assert finder.selectedUrlItemByIndex(0) is None
			self.failUnlessRaises(IndexError, finder.selectedUrlItemByIndex, 1)
			
			
			# selection
			items = finder.urlItemsByIndex(0)
			self.failUnlessRaises(IndexError, finder.urlItemsByIndex, 1)
			
			assert items
			for item in items:
				finder.setItemByIndex(item, 0)
				assert finder.selectedUrlItemByIndex(0) == item
				assert finder.selectedUrl() == item
			# END for each item to select
			
			self.failUnlessRaises(IndexError, finder.setItemByIndex, item, 100)
			self.failUnlessRaises(ValueError, finder.setItemByIndex, "doesntexist", 0)
			
			# more complex url selection
			url_short = "ext/pydot"
			url = "ext/pyparsing/src"
			url_invalid = url_short + "/doesntexist"
			
			finder.setUrl(url)
			assert finder.selectedUrl() == url
			
			# require_all_items test - failure does not change existing value
			self.failUnlessRaises(ValueError, finder.setUrl, url_invalid)
			assert finder.selectedUrl() == url
			
			finder.setUrl(url_invalid, require_all_items=False)
			assert finder.selectedUrl() == url_short
			
			
			# ROOT_PROVIDER
			###############
			root2 = root.dirname()
			selector = main.rootselector
			self.failUnlessRaises(ValueError, selector.setItems, [root])
			selector.setItems([FileProvider(root), FileProvider(root2)])
			assert len(selector.providers()) == 2  
			
			# test removal - root path - nonexisting okay
			selector.removeItem("something")
			assert len(selector.providers()) == 2
			
			# remove by root
			selector.removeItem(root2)
			assert len(selector.providers()) == 1 and len(selector.items()) == 1  
			
			# re-add previous item
			selector.addItem(FileProvider(root2))
			assert len(selector.providers()) == 2 and len(selector.items()) == 2
			
			
			# BOOKMARKS
			###########
			bookmarks = main.bookmarks
			assert len(bookmarks.items()) == 0
			
			bookmarks.addItem(root)
			assert len(bookmarks.items()) == 1
			assert bookmarks.items()[0] == root
			
			# duplicate check
			bookmarks.addItem(root)
			assert len(bookmarks.items()) == 1
			
			root2_bm = (root2, 'git')
			bookmarks.addItem(root2_bm)
			assert len(bookmarks.items()) == 2
			
			# remove - ignores non-existing
			bookmarks.removeItem("doesntexist")
			assert len(bookmarks.items()) == 2
			
			# remove 
			bookmarks.removeItem(root)
			assert len(bookmarks.items()) == 1
			
			bookmarks.setItems([root, root2_bm])
			assert len(bookmarks.items()) == 2
			
			
			
			return
			
			# BASIC FINDER
			##############
			win = ui.Window(title="Default Finder")
			FinderLayout()
			win.show()
			
			
			# FILE OPEN FINDER
			##################
			win = ui.Window(title="File Open Finder")
			FileOpenFinder()
			win.show()
