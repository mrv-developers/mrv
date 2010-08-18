# -*- coding: utf-8 -*-
from mrv.test.maya import *
from util import *

import mrv.maya.ui as ui
from mrv.test.maya.ui import instructor

import maya.cmds as cmds

if not cmds.about(batch=1):
	class TestItemBrowser(unittest.TestCase):
		def test_base(self):
			pass
