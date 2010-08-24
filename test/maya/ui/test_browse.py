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
			main = FinderLayout()
			
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
			assert finder.num_url_tokens() == 1
			
			self.failUnlessRaises(IndexError, finder.stored_url_token_by_index, 0)
			
			
			
			
