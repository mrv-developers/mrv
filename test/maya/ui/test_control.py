# -*- coding: utf-8 -*-
from mrv.test.maya import *
from util import *
import mrv.maya.ui as ui

import maya.cmds as cmds

if not cmds.about(batch=1):
	class TestControls(unittest.TestCase):
		def test_base(self):
			win = ui.Window(title="Controls Test")
			col = ui.ColumnLayout(adj=True)
			
			tsl = ui.TextScrollList(allowMultiSelection=True)
			first = "one"
			tsl.addItem(first)
			tsl.addItem("two")
			
			assert tsl.selectedIndex() == -1
			assert tsl.selectedItem() is None
			assert len(tsl.selectedItems()) == 0
			assert len(tsl.selectedIndices()) == 0
			
			tsl.p_selectIndexedItem = 1
			assert tsl.selectedIndex() == 1
			assert tsl.selectedItem() == first
			assert len(tsl.selectedItems()) == 1
			assert len(tsl.selectedIndices()) == 1
			
			
			tsl.p_selectIndexedItem = 2
			# just shows the first selected one
			assert tsl.selectedIndex() == 1
			assert tsl.selectedItem() == first
			assert len(tsl.selectedItems()) == 2
			assert len(tsl.selectedIndices()) == 2
			
			# add item
			third = "hi"
			tsl.addItems((third, "there"))
			assert len(tsl.items()) == 4
			
			# selectItem
			tsl.setSelectedItem(third)
			assert len(tsl.selectedItems()) == 3

			
			# remove item - non-existing is no error
			tsl.removeItem("doesnt exist")
			tsl.removeItem(third)
			assert len(tsl.items()) == 3
			
			win.show()
