# -*- coding: utf-8 -*-
import os
import sys
import mrv.test.maya.util as tutil
from mrv.test.lib import *

class TestCompatability(tutil.StandaloneTestBase):
	"""Make sure that mrv's monkey patches don't interfere with other built-in
	frameworks, such as pymel"""
	def setup_environment(self):
		pass
		# os.environ['MRV_STANDALONE_INIT_OPTIONVARS'] = "1"
		
		
		
	def undo_setup_environment(self):
		pass
		# os.environ['MRV_STANDALONE_INIT_OPTIONVARS'] = "0"
		
		
		
	def post_standalone_initialized(self):
		import mrv.maya.nt 
		try:
			import pymel.all as pymel
		except ImportError:
			# ignore standalone runs
			return
		#END import pymel
		
		# assure we can wrap nodes
		n = pymel.PyNode("persp")
		try:
			str(n.tx)
		except Exception, e:
			raise AssertionError(str(e))
		#END handle exception
