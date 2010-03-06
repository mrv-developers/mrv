# -*- coding: utf-8 -*-
"""Initialize the UI framework allowing convenient access to most common user interfaces

All classes of the ui submodules can be accessed by importing this package.
"""


############################
#### Exceptions		 	####
#########################

if 'init_done' not in locals():
	init_done = False


#{ Initialization Utilities
def _force_type_creation():
	"""Enforce the creation of all ui types - must be called once all custom types 
	were imported"""
	from mayarv.maya.util import StandinClass
	for cls in globals().itervalues():
		if isinstance( cls, StandinClass ):
			cls.createCls()
		# END create type 
	# END for each stored type

#} END initialization utilities

if not init_done:
	import typ
	typ.init_classhierarchy()				# populate hierarchy DAG from cache
	typ.init_wrappers( )					# create wrappers for all classes
	
	import base
	base._uidict = globals()

	# assure we do not run several times
	# import modules - this way we overwrite actual wrappers lateron
	from base import *
	from control import *
	from dialog import *
	from layout import *
	from panel import *
	from editor import *
	
	# automatic types need to be created in the end !
	_force_type_creation()
# END initialization

init_done = True