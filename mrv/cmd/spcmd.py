#!/usr/bin/env python
__docformat__ = "restructuredtext"
import sys


def main(args):
	"""Run the spawned command
	:param args: arguments excluding the executable path"""
	if len(args) < 1:
		raise Exception("Invalid Arguments, call command as follows:\nspcmd package.module.ServerClassName [additional options for execute method]")

	# needs that order as paths will be adjusted here
	try:
		tokens = args[0].split('.')
		args = args[1:]		# remaining args
		module, classname = ".".join(tokens[:-1]), tokens[-1]
		module = __import__(module, globals(), locals(), [module])
		cmdtype = getattr(module, classname)
		
		cmdinstance = cmdtype(_spawned=True)
		
		# EXECUTE FUNCTION
		found = False
		try:
			func = getattr(cmdinstance, '_execute')
			found = True
			func(*args)
		except AttributeError,e:
			raise
	except Exception, e:
		import logging
		# all other exceptions should result in some red blinking light
		logging.critical("Unhandled Exception", exc_info=True)
		raise

# END main

if __name__ == '__main__':
	main(sys.argv[1:])

