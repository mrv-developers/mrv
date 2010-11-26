# -*- coding: utf-8 -*-
"""Contains all test related startup routines"""

import os
import sys

import mrv.test.cmd as mrvtestcmd

def sameModule(self, mod, filename):
	mod_paths = []
	if hasattr(mod, '__path__'):
		for path in mod.__path__:
			mod_paths.append(os.path.dirname(
				os.path.normpath(
				os.path.abspath(path))))
	elif hasattr(mod, '__file__'):
		mod_paths.append(os.path.dirname(
			os.path.normpath(
			os.path.abspath(mod.__file__))))
	else:
		# builtin or other module-like object that
		# doesn't have __file__; must be new
		return False
	new_path = os.path.dirname(os.path.abspath(os.path.normpath(filename)))
	for mod_path in mod_paths:
		if mod_path == new_path:
			return True
	return False

#{ Startup

def nose():
	"""Initialize nose"""
	# It is possible to pass additional args which we append to the system args.
	# This is required in case we start nose in maya UI mode and want to pass
	# nose specific arguments
	if mrvtestcmd.env_nose_args in os.environ:
		sys.argv = ['nosetests'] + os.environ[mrvtestcmd.env_nose_args].split(mrvtestcmd.nose_args_splitter)
	# END handle extra args
	
	import nose
	import nose.importer
	
	# monkey patch nose - if it fails to detect that modules are equal, we get
	# all sorts of weird import bugs
	nose.importer.Importer.sameModule = sameModule
	
	
	nose.main()

#} END startup
