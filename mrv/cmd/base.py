# -*- coding: utf-8 -*-
"""Contains routines required to initialize mrv"""
import os
import sys
import subprocess
from mrv.path import make_path, BasePath
import logging
import optparse

log = logging.getLogger("mrv.cmd.base")

__docformat__ = "restructuredtext"

__all__ = [ 'is_supported_maya_version', 'python_version_of', 'parse_maya_version', 'update_env_path', 
			'maya_location', 'update_maya_environment', 'exec_python_interpreter', 'uses_mayapy', 
			'exec_maya_binary', 'available_maya_versions', 'python_executable', 'find_mrv_script',
			'log_exception', 'SpawnedHelpFormatter', 'SpawnedOptionParser', 'SpawnedCommand']

#{ Globals
maya_to_py_version_map = {
	8.5 : 2.4, 
	2008: 2.5, 
	2009: 2.5, 
	2010: 2.6,
	2011: 2.6
}

#} END globals


#{ Maya-Intiialization
	
def is_supported_maya_version(version):
	""":return: True if version is a supported maya version
	:param version: float which is either 8.5 or 2008 to 20XX"""
	if version == 8.5:
		return True
		
	return str(version)[:2] == "20"
	
def uses_mayapy():
	""":return: True if the executable is mayapy"""
	try:
		mayapy_maya_version()
		return True
	except EnvironmentError:
		return False
	# END handle exceptions
	
def mayapy_maya_version():
	""":return: float representing the maya version of the currently running 
	mayapy interpreter. 
	:raise EnvironmentError: If called from a 'normal' python interpreter"""
	if 'maya' not in sys.executable.lower():
		raise EnvironmentError("Not running mayapy")
	# END quick first check 
	
	exec_path = make_path(os.path.realpath(sys.executable))	# Maya is capitalized on windows
	try:
		version_token = [ t[4:] for t in exec_path.splitall() if t.lower().startswith('maya') ][0]
	except IndexError:
		raise EnvironmentError("Not running mayapy or invalid path mayapy path: %s" % exec_path)
	# END handle errors
	
	if version_token.endswith('-x64'):
		version_token = version_token[:-4]
	# END handle 64 bit paths
	
	return float(version_token)
	
def parse_maya_version(arg, default):
	""":return: tuple(bool, version) tuple of bool indicating whether the version could 
	be parsed and was valid, and a float representing the parsed or default version.
	:param default: The desired default maya version"""
	parsed_arg = False
	version = default
	try:
		candidate = float(arg)
		if is_supported_maya_version(candidate):
			parsed_arg, version = True, candidate
		else:
			pass
			# in that case, we don't claim the arg and just use the default
		# END handle candidate
	except ValueError:
		pass
	# END exception handling
	
	return parsed_arg, version
	
def python_version_of(maya_version):
	""":return: python version matching the given maya version
	:raise EnvironmentError: If there is no known matching python version"""
	try:
		return maya_to_py_version_map[maya_version]
	except KeyError:
		raise EnvironmentError("Do not know python version matching the given maya version %g" % maya_version) 
	
def update_env_path(environment, env_var, value, append=False):
	"""Set the given env_var to the given value, but append the existing value
	to it using the system path separator
	
	:param append: if True, value will be appended to existing values, otherwise it will 
		be prepended"""
	curval = environment.get(env_var, None)
	# rule out empty strings
	if curval:
		if append:
			value = curval + os.pathsep + value
		else:
			value = value + os.pathsep + curval
		# END handle append
	# END handle existing value
	environment[env_var] = value

def available_maya_versions():
	""":return: list of installed maya versions which are locally available - 
	they can be used in methods that require the maya_version to be given. 
	Versions are ordered such that the latest version is given last."""
	versions = list()
	for version_candidate in sorted(maya_to_py_version_map.keys()):
		try:
			loc = maya_location(version_candidate)
			versions.append(version_candidate)
		except Exception:
			pass
		# END check maya location
	# END for each version
	return versions

def maya_location(maya_version):
	""":return: string path to the existing maya installation directory for the 
	given maya version
	:raise EnvironmentError: if it was not found"""
	mayaroot = None
	suffix = ''
	
	if sys.platform.startswith('linux'):
		mayaroot = "/usr/autodesk/maya"
		if os.path.isdir('/lib64'):
			suffix = "-x64"
		# END handle 64 bit systems
	elif sys.platform == 'darwin':
		mayaroot = "/Applications/Autodesk/maya"
	elif sys.platform.startswith('win'):
		# try to find it in all kinds of program files, prefer 64 bit versions
		tried_paths = list()
		for envvar in ('PROGRAMW6432', 'PROGRAMFILES','PROGRAMFILES(X86)'):
			if envvar not in os.environ: 
				continue
			basepath = make_path(os.environ[envvar]) / "Autodesk"
			if basepath.isdir():
				mayaroot = basepath / 'Maya'
				break
			# END if we have found Autodesk installations
			tried_paths.append(basepath)
		# END for each envvar
		if mayaroot is None:
			raise EnvironmentError("Could not find any maya installation, searched %s" % (', '.join(tried_paths)))
	# END os specific adjustments
	
	if mayaroot is None:
		raise EnvironmentError("Current platform %r is unsupported" % sys.platform)
	# END assure existance of maya root
	
	mayalocation = "%s%g%s" % (mayaroot, maya_version, suffix)
	
	# OSX special handling
	if sys.platform == 'darwin':
		mayalocation=os.path.join(mayalocation, 'Maya.app', 'Contents')
	
	if not os.path.isdir(mayalocation):
		raise EnvironmentError("Could not find maya installation at %r" % mayalocation)
	# END verfy maya location
	
	return mayalocation
	
def update_maya_environment(maya_version):
	"""Configure os.environ to allow Maya to run in standalone mode
	:param maya_version: The maya version to prepare to run, either 8.5 or 2008 to 
	20XX. This requires the respective maya version to be installed in a default location.
	:raise EnvironmentError: If the platform is unsupported or if the maya installation could not be found"""
	py_version = python_version_of(maya_version)
	
	pylibdir = None
	envppath = "PYTHONPATH"
	
	if sys.platform.startswith('linux'):
		pylibdir = "lib"
	elif sys.platform == 'darwin':
		pylibdir = "Frameworks/Python.framework/Versions/Current/lib"
	elif sys.platform.startswith('win'):
		pylibdir = "Python"
	# END os specific adjustments
	
	
	# GET MAYA LOCATION
	###################
	mayalocation = maya_location(maya_version)
	
	if not os.path.isdir(mayalocation):
		raise EnvironmentError("Could not find maya installation at %r" % mayalocation)
	# END verfy maya location
	
	
	env = os.environ
	
	# ADJUST LD_LIBRARY_PATH or PATH
	################################
	# Note: if you need something like LD_PRELOAD or equivalent, add the respective
	# variables to the environment of this process before starting it
	if sys.platform.startswith('linux'):
		envld = "LD_LIBRARY_PATH"
		ldpath = os.path.join(mayalocation, 'lib')
		update_env_path(env, envld, ldpath)
	elif sys.platform == 'darwin':
		# adjust maya location to point to the actual directtoy
		dldpath = os.path.join(mayalocation, 'MacOS')
		update_env_path(env, "DYLD_LIBRARY_PATH", dldpath)
		
		dldframeworkpath = os.path.join(mayalocation, 'Frameworks')
		update_env_path(env, "DYLD_FRAMEWORK_PATH", dldframeworkpath)
		
		env['MAYA_NO_BUNDLE_RESOURCES'] = "1"
		
		# on osx, python will only use the main frameworks path and ignore 
		# its own sitelibraries. We put them onto the PYTHONPATH for that reason
		# MayaRV will take care of the initialization
		ppath = "/Library/Python/%s/site-packages" % py_version
		update_env_path(env, envppath, ppath, append=True)
		
	elif sys.platform.startswith('win'):
		mayadll = os.path.join(mayalocation, 'bin')
		mayapydll = os.path.join(mayalocation, 'Python', 'DLLs')
		update_env_path(env, 'PATH', mayadll+os.pathsep+mayapydll, append=False)
	else:
		raise EnvironmentError("Current platform %s is unsupported" % sys.platform)
	# END handle os's
	
	
	# ADJUST PYTHON PATH
	####################
	# root project is already in the path, we add additional paths as well
	ospd = os.path.dirname
	if not sys.platform.startswith('win'):
		ppath = os.path.join(mayalocation, pylibdir, "python%s"%py_version, "site-packages")
	else:
		ppath = os.path.join(mayalocation, pylibdir, "lib", "site-packages")
	# END windows special handling
	
	# don't prepend, otherwise system-interpreter mrv versions will not be able
	# to override the possibly existing mrv version installed in maya.
	update_env_path(env, envppath, ppath, append=True)
	
	# SET MAYA LOCATION
	###################
	# its important to do it here as osx adjusts it 
	env['MAYA_LOCATION'] = mayalocation 
	
	# export the actual maya version to allow scripts to pick it up even before maya is launched
	env['MRV_MAYA_VERSION'] = "%g" % maya_version
	
def mangle_args(args):
	"""Enclose arguments in quotes if they contain spaces ... on windows only
	:return: tuple of possibly modified arguments
	
	:todo: remove this function, its unused"""
	if not sys.platform.startswith('win'):
		return args
	
	newargs = list()
	for arg in args:
		if ' ' in arg:
			arg = '"%s"' % arg
		# END put quotes around strings with spaces
		newargs.append(arg)
	# END for each arg
	return tuple(newargs)
	
def mangle_executable(executable):
	""":return: possibly adjusted path to executable in order to allow its execution
		This currently only kicks in on windows as we can't handle spaces properly.
	
	:note: Will change working dir
	:todo: remove this function, its unused"""
	if not sys.platform.startswith('win'):
		return executable
		
	# execv appears to call the shell, hence we make sure we handle whitespaecs
	# in the path, which usually happens on windows !
	# Problem here is that it cannot find the executable if it has a space in the
	# path as it will split it, and if quotes are put around, it can't find 
	# it either. Hence we chdir into it and use a relative path
	if ' ' in executable:
		os.chdir(os.path.dirname(executable))
		executable = os.path.basename(executable)
	# END handle freakin' spaces
	return executable

def init_environment(args):
	"""Intialize MRV up to the point where we can replace this process with the 
	one we prepared
	
	:param args: commandline arguments excluding the executable ( usually first arg )
	:return: tuple(use_this_interpreter, maya_version, args) tuple of Bool, maya_version, and the remaining args
		The boolean indicates whether we have to reuse this interpreter, as it is mayapy"""
	# see if first argument is the maya version
	maya_version=None
	if args:
		parsed_successfully, maya_version = parse_maya_version(args[0], default=None)
		if parsed_successfully:
			# if the user wants a specific maya version, he should get it no matter what
			args = args[1:]
		# END cut version arg
	# END if there are args at all
	
	# choose the newest available maya version if none was specified
	if maya_version is None:
		# If there is no version given, and we are in mayapy, we use the maypy 
		# version. Otherwise we use the newest available version
		if uses_mayapy():
			maya_version = mayapy_maya_version()
			# in that case, we have a valid maya environment already. This also means 
			# that we must use this interpreter !
			return (True, maya_version, tuple(args))
		else:
			versions = available_maya_versions()
			if versions:
				maya_version = versions[-1]
				log.info("Using newest available maya version: %g" % maya_version)
			# END set latest
		# END handle maya version
	# END set maya version 
	
	# The user has specified a maya version to start. As mayapy sets up everything in 
	# a distinctive way, we are kind of too late to alter that.
	# Hence we must prevent the user from starting different maya versions than 
	# the one defined by mayapy.
	# NOTE: If we use mayapy, the things mentioned above are an issue. If we 
	# use the delivered python-bin (linux) or Python (osx) executables, this 
	# is not an issue. This way, its consistent among all platforms though as 
	# windows always uses mayapy.
	if uses_mayapy():
		mayapy_version = mayapy_maya_version()
		if mayapy_version != maya_version:
			raise EnvironmentError("If using mayapy, you cannot run any other maya version than the one mayapy uses: %g" % mayapy_version)
	# END assert version
	
	if maya_version is None:
		raise EnvironmentError("Maya version not specified on the commandline, couldn't find any maya version on this system")
	# END abort if not installed
	
	update_maya_environment(maya_version)
	return (False, maya_version, tuple(args))
	
def _execute(executable, args):
	"""Perform the actual execution of the executable with the given args.
	This method does whatever is required to get it right on windows, which is 
	the only reason this method exists !
	
	:param args: arguments, without the executable as first argument
	:note: does not return """
	# on windows we spawn, otherwise we don't get the interactive input right
	actual_args = (executable, ) + args
	if sys.platform.startswith('win'):
		p = subprocess.Popen(actual_args, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
		sys.exit(p.wait())
	else:
		os.execvp(executable, actual_args)
	# END handle windows

def python_executable(py_version=None):
	""":return: name or path to python executable in this system, deals with 
	linux and windows specials"""
	if py_version is None:
		return 'python'
	# END handle simple case
	
	py_executable = "python%g" % py_version
	if sys.platform.startswith('win'):
		# so, on windows the executables don't have a . in their name, most likely
		# because windows threats the '.' in a special way as ... anyway. 
		py_executable = "python%g" % (py_version*10)
	# END win specials
	return py_executable
	
def find_mrv_script(name):
	"""Find an mrv script of the given name. This method should be used if you 
	want to figure out where the mrv executable with the given name is located.
	The returned path is either relative or absolute.

	:return: Path to script 
	:raise EnvironmentError: if the executable could not be found
	:note: Currently it only looks for executables, but handles projects
	which use mrv as a subproject"""
	import mrv
	mrvroot = os.path.dirname(mrv.__file__)
	
	tried_paths = list()
	for base in ('', 'ext', mrvroot):
		for subdir in ('bin', 'doc', os.path.join('test', 'bin')):
			path = None
			if base:
				path = os.path.join(base, subdir, name)
			else:
				path = os.path.join(subdir, name)
			# END handle base
			if os.path.isfile(path):
				return make_path(path)
			tried_paths.append(path)
		# END for each subdir
	# END for each base
	
	raise EnvironmentError("Script named %s not found, looked at %s" % (name, ', '.join(tried_paths))) 
	
def exec_python_interpreter(args, maya_version, mayapy_only=False):
	"""Replace this process with a python process as determined by the given options.
	This will either be the respective python interpreter, or mayapy.
	If it works, the function does not return
	
	:param args: remaining arguments which should be passed to the process
	:param maya_version: float indicating the maya version to use
	:param mayapy_only: If True, only mayapy will be considered for startup.
	Use this option in case the python interpreter crashes for some reason.
	:raise EnvironmentError: If no suitable executable could be started"""
	py_version = python_version_of(maya_version)
	py_executable = python_executable(py_version) 
	
	args = tuple(args)
	tried_paths = list()
	try:
		if mayapy_only:
			raise OSError()
		tried_paths.append(py_executable)
		_execute(py_executable, args)
	except OSError:
		if not mayapy_only:
			print "Python interpreter named %r not found, trying mayapy ..." % py_executable
		# END print error message
		mayalocation = maya_location(maya_version)
		mayapy_executable = os.path.join(mayalocation, "bin", "mayapy")
		
		try:
			tried_paths.append(mayapy_executable)
			_execute(mayapy_executable, args)
		except OSError, e:
			raise EnvironmentError("Could not find suitable python interpreter at paths %s : %s" % (', '.join(tried_paths), e))
		# END final exception handling
	# END exception handling
	
def exec_maya_binary(args, maya_version):
	"""Replace this process with the maya executable as specified by maya_version.
	
	:param args: The arguments to be provided to maya
	:param maya_version: Float identifying the maya version to be launched
	:rase EnvironmentError: if the respective maya version could not be found"""
	mayalocation = maya_location(maya_version)
	mayabin = os.path.join(mayalocation, 'bin', 'maya')
	
	# although execv would work on windows, we use our specialized _execute method 
	# in order to keep things consistent
	_execute(mayabin, tuple(args))
	
	
#} END Maya initialization

#{ Decorators

def log_exception( func ):
	"""Assures that exceptions result in a logging message.
	Currently only works with a SpawnedCommand as we need a log instance.
	On error, the server exits with status 64"""
	def wrapper(self, *args, **kwargs):
		try:
			return func(self, *args, **kwargs)
		except Exception, e:
			if self.parser.spawned:
				self.log.critical("Program %r aborted with a unhandled exception: %s" % (self.k_log_application_id, str(e)), exc_info=True)
				sys.exit(64)
			else:
				raise
			# END handle sysexit gracefully
	# END wrapper 
	
	wrapper.__name__ = func.__name__
	return wrapper

#} END decorators

#{ Classes

class SpawnedHelpFormatter(optparse.TitledHelpFormatter):
	"""Formatter assuring our help looks good"""
	
	def _format_text(self, text):
		"""Don't wrap the text at all"""
		if self.parser:
			text = self.parser.expand_prog_name(text)
		# END program name expansion if possible
		
		if self.level == 0:
			return text
		lines = text.splitlines(True)
		return ''.join('  '*self.level + l for l in lines)
		
	def format_usage(self, usage):
		return "usage: %s\n" % usage


class SpawnedOptionParser(optparse.OptionParser):
	"""Customized version to ease use of SpawnedCommand
	
	Initialized with the 'spawned' keyword in addition 
	to the default keywords to prevent a system exit"""
	
	def __init__(self, *args, **kwargs):
		self.spawned = kwargs.pop('spawned', False)
		kwargs['formatter'] = SpawnedHelpFormatter()
		optparse.OptionParser.__init__(self, *args, **kwargs)
	
	def exit(self, status=0, msg=None):
		if msg:
			sys.stderr.write(msg)
		
		if self.spawned:
			sys.exit(status)
		else:
			# reraise if possible as we have not been spawned
			exc_type, value, traceback = sys.exc_info()
			if value:
				raise
			else:
				raise optparse.OptParseError(msg)
		# END options
			


class SpawnedCommand(object):
	"""Implements a command which can be started easily by specifying a class path
	such as package.cmd.module.CommandClass whose instance should be started in 
	a standalone process.
	
	The target command must be derived from this class and must implement the 
	'execute' method.
	
	To use this class, derive from it and change the configuration variables
	accordingly.
	
	The instance will always own a logger instance at its member called 'log', 
	the configuration will be applied according to k_log_application_id
	
	The parser used to parse all options is vailable at its member called 'parser', 
	its set during ``option_parser``
	
	The instance may also be created within an existing process and 
	executed manually - in that case it will not exit automatically if a 
	serious event occours"""
	
	#{ Configuration 
	# If not None, the name will be available for printing help text, and other tasks
	# such as application specific initialization of modules
	k_log_application_id = None
	
	# path at which your class is located. It must be derived from SpawnedCommand
	k_class_path = "package.module.YourClass"
	
	# An identifier for the version of your command
	k_version = None
	
	# Path to the executable
	_exec_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bin', 'mrv')
	
	# additional arguments to pass on to the newly created process
	_add_args = ['--mrv-no-maya']
	
	# The usage of your command in BMF
	# i.e. %prog [options]
	k_usage = None
	
	# a short description of your command printed below its usage
	k_description = None
	
	# the name of your program's actual executable
	k_program_name = None
	
	# File mode creation mask of the daemon.
	# If None, current one will not be changed
	_daemon_umask = None
	
	# Default working directory for the daemon.
	# If None, the current one will not be changed
	_daemon_workdir = None
	
	# Default maximum for the number of available file descriptors that we try to close
	_daemon_maxfd = 64
	
	# The standard I/O file descriptors are redirected to /dev/null by default.
	if (hasattr(os, "devnull")):
	   _daemon_redirect_to = os.devnull
	else:
	   _daemon_redirect_to = "/dev/null"
	
	#} END configuration
	
	__slots__ = ('parser', 'log')
	
	
	def __init__(self, *args, **kwargs):
		"""
		:param _spawned: If True, default False, we assume we have our own process.
			Otherwise we will do nothing that would adjust the current process, such as:
			
			* sys.exit
			* change configuration of logging system"""
		try:
			super(SpawnedCommand, self).__init__(*args, **kwargs)
		except TypeError:
			# in python 2.6 and newer, object will not accept to be called with 
			# arguments anymore. Problem is that we don't know whether super is an 
			# object or some mixed in type, which is a design flaw, and which breaks
			# code as well.
			pass
		# END py 2.6 special case
		
		
		spawned = kwargs.get('_spawned', False)
		self.parser = SpawnedOptionParser(	usage=self.k_usage, version=self.k_version, 
											description=self.k_description,  add_help_option=True,
											prog=self.k_program_name, spawned=spawned)
		self.log = logging.getLogger(self.k_program_name)
		
	@classmethod
	def spawn(cls, *args, **kwargs):
		"""Spawn a new standalone process of this command type
		Additional arguments passed to the command process
		
		:param kwargs: Additional keyword arguments to be passed to Subprocess.Popen, 
			use it to configure your IO
		
		Returns: Subprocess.Popen instance"""
		import spcmd
		margs = [cls._exec_path, spcmd.__file__, cls.k_class_path]
		margs.extend(args)
		margs.extend(cls._add_args)
		
		if os.name == 'nt':
			margs.insert(0, sys.executable)
		# END handle windows inabilitiess
		
		return subprocess.Popen(margs, **kwargs)
		
	@classmethod
	def daemonize(cls, *args):
		"""
		Damonize the spawned command, passing *args to the instanciated command's
		execute method.
		
		:return: None in calling process, no return in the daemon
			as sys.exit will be called.
		:note: see configuration variables prefixed with _daemon_
		:note: based on Chad J. Schroeder createDaemon method, 
			see http://code.activestate.com/recipes/278731-creating-a-daemon-the-python-way
		"""
		if sys.platform.startswith("win"):
			raise OSError("Cannot daemonize on windows")
		# END handle operating system
		
		try:
			# Fork a child process so the parent can exit.	This returns control to
			# the command-line or shell.	It also guarantees that the child will not
			# be a process group leader, since the child receives a new process ID
			# and inherits the parent's process group ID.  This step is required
			# to insure that the next call to os.setsid is successful.
			pid = os.fork()
		except OSError, e:
			raise Exception, "%s [%d]" % (e.strerror, e.errno)
	
		if (pid != 0):
			# exit() or _exit()?
			# _exit is like exit(), but it doesn't call any functions registered
			# with atexit (and on_exit) or any registered signal handlers.	 It also
			# closes any open file descriptors.	 Using exit() may cause all stdio
			# streams to be flushed twice and any temporary files may be unexpectedly
			# removed.	It's therefore recommended that child branches of a fork()
			# and the parent branch(es) of a daemon use _exit().
			return None
		# END exit 
			
		##################
		# The first child.
		##################
		# To become the session leader of this new session and the process group
		# leader of the new process group, we call os.setsid().	The process is
		# also guaranteed not to have a controlling terminal.
		os.setsid()

		# Is ignoring SIGHUP necessary?
		#
		# It's often suggested that the SIGHUP signal should be ignored before
		# the second fork to avoid premature termination of the process.	The
		# reason is that when the first child terminates, all processes, e.g.
		# the second child, in the orphaned group will be sent a SIGHUP.
		#
		# "However, as part of the session management system, there are exactly
		# two cases where SIGHUP is sent on the death of a process:
		#
		#	 1) When the process that dies is the session leader of a session that
		#		 is attached to a terminal device, SIGHUP is sent to all processes
		#		 in the foreground process group of that terminal device.
		#	 2) When the death of a process causes a process group to become
		#		 orphaned, and one or more processes in the orphaned group are
		#		 stopped, then SIGHUP and SIGCONT are sent to all members of the
		#		 orphaned group." [2]
		#
		# The first case can be ignored since the child is guaranteed not to have
		# a controlling terminal.	The second case isn't so easy to dismiss.
		# The process group is orphaned when the first child terminates and
		# POSIX.1 requires that every STOPPED process in an orphaned process
		# group be sent a SIGHUP signal followed by a SIGCONT signal.	Since the
		# second child is not STOPPED though, we can safely forego ignoring the
		# SIGHUP signal.	In any case, there are no ill-effects if it is ignored.
		#
		# import signal			  # Set handlers for asynchronous events.
		# signal.signal(signal.SIGHUP, signal.SIG_IGN)

		try:
			# Fork a second child and exit immediately to prevent zombies.	 This
			# causes the second child process to be orphaned, making the init
			# process responsible for its cleanup.	 And, since the first child is
			# a session leader without a controlling terminal, it's possible for
			# it to acquire one by opening a terminal in the future (System V-
			# based systems).	 This second fork guarantees that the child is no
			# longer a session leader, preventing the daemon from ever acquiring
			# a controlling terminal.
			pid = os.fork()	# Fork a second child.
		except OSError, e:
			raise Exception, "%s [%d]" % (e.strerror, e.errno)

		if (pid != 0):
			# exit() or _exit()?	 See below.
			os._exit(0) # Exit parent (the first child) of the second child.
		# END exit second child
		
		###################
		# The second child.
		###################
		# Since the current working directory may be a mounted filesystem, we
		# avoid the issue of not being able to unmount the filesystem at
		# shutdown time by changing it to the root directory.
		if cls._daemon_workdir is not None:
			os.chdir(cls._daemon_workdir)
		# END set working dir
		
		# We probably don't want the file mode creation mask inherited from
		# the parent, so we give the child complete control over permissions.
		if cls._daemon_umask is not None:
			os.umask(cls._daemon_umask)
		# END set umask
			
		
	
		# Close all open file descriptors.	This prevents the child from keeping
		# open any file descriptors inherited from the parent.  There is a variety
		# of methods to accomplish this task.	Three are listed below.
		#
		# Try the system configuration variable, SC_OPEN_MAX, to obtain the maximum
		# number of open file descriptors to close.	If it doesn't exists, use
		# the default value (configurable).
		#
		# try:
		#	  maxfd = os.sysconf("SC_OPEN_MAX")
		# except (AttributeError, ValueError):
		#	  maxfd = MAXFD
		#
		# OR
		#
		# if (os.sysconf_names.has_key("SC_OPEN_MAX")):
		#	  maxfd = os.sysconf("SC_OPEN_MAX")
		# else:
		#	  maxfd = MAXFD
		#
		# OR
		#
		# Use the getrlimit method to retrieve the maximum file descriptor number
		# that can be opened by this process.	If there is not limit on the
		# resource, use the default value.
		#
		import resource		# Resource usage information.
		maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
		if (maxfd == resource.RLIM_INFINITY):
			maxfd = cls._daemon_maxfd

		debug_daemon = False
		
		# Iterate through and close all file descriptors.
		for fd in range(debug_daemon*3, maxfd):
			try:
				os.close(fd)
			except OSError: # ERROR, fd wasn't open to begin with (ignored)
				pass
		# END for each fd in range
	
		# Redirect the standard I/O file descriptors to the specified file. Since
		# the daemon has no controlling terminal, most daemons redirect stdin,
		# stdout, and stderr to /dev/null.	This is done to prevent side-effects
		# from reads and writes to the standard I/O file descriptors.
	
		# This call to open is guaranteed to return the lowest file descriptor,
		# which will be 0 (stdin), since it was closed above.
		if not debug_daemon:
			os.open(cls._daemon_redirect_to, os.O_RDWR)	# standard input (0)
		
			# Duplicate standard input to standard output and standard error.
			os.dup2(0, 1)			# standard output (1)
			os.dup2(0, 2)			# standard error (2)
		# END handle standard descriptors
	
		# RUN THE SPAWNED COMMAND
		#########################
		cmdinstance = cls(_spawned=True)
		return cmdinstance._execute(*args)
	
	def _preprocess_args(self, options, args):
		""":return: tuple(options, args) tuple of parsed options and remaining args
			The arguments can be preprocessed"""
		return options, args
	
	def _execute(self, *args):
		"""internal method handling the basic arguments in a pre-process before 
		calling ``execute``
		
		We will parse all options, process the default ones and pass on the 
		call to the ``execute`` method"""
		options, args = self._preprocess_args(*self.option_parser().parse_args(list(args)))
		
		# make sure we have a default setup at least !
		logging.basicConfig()
		
		# call the subclassed method
		try:
			return self.execute(options, args)
		except Exception, e:
			if self.parser.spawned:
				sys.stderr.write('%s: %s\n' % (type(e).__name__, str(e)))
				sys.exit(1)
			else:
				raise
		# END help the user in case he provides invalid options
		
	#{ Overridable 
	@log_exception
	def execute(self, options, args):
		"""Method implementing the actual functionality of the command
		:param options: Values instance of the optparse module
		:param args: remaining positional arguments passed to the process on the commandline
		:note: if you like to terminate, raise an exception"""
		pass
	
	def option_parser(self):
		""":return: OptionParser Instance containing all supported options
		:note: Should be overridden by subclass to add additional options and 
			option groups themselves after calling the base class implementation"""
		return self.parser
	#} END needing subclass
		
		
#} END classes

