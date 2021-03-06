from mrv.test.lib import *
from mrv.path import Path 
import tempfile
import time
import os
import sys

__all__ = ('save_temp_file', 'save_for_debugging', 'get_maya_file', 'with_scene', 
            'with_undo', 'with_persistence', 'with_new_scene')


def save_temp_file(filename):
    """save the current scene as given filename in a temp directory as .ma file"""
    import mrv.maya as mrvmaya      # late import
    filepath = tempfile.mktemp(prefix=filename, suffix='.ma')
    savedfile = mrvmaya.Scene.save(filepath, force=True)
    return Path(savedfile)

def save_for_debugging(scene_name):
    """Save the currently actve scene as MayaAscii for debugging purposes
    :return: absolute path string at which the file was saved"""
    scene_path = save_temp_file(scene_name)
    print "Saved scene for debugging at: %r" % scene_path
    return scene_path

#{ Decorators
def with_scene(basename, debug=False):
    """Loads the specified scene . the basename is supposed to be in our fixtures
    directory
    If debug is True, we will stay in the scene, instead of dropping out in case of an error
    """
    import mrv.maya as mrvmaya      # late import
    if not isinstance(basename, basestring):
        raise ValueError("Need basename of a scene as string, not %r" % basename)
    # END arg check
    
    def wrapper(func):
        def scene_loader(self, *args, **kwargs):
            if os.path.isabs(basename):
                scene_path = Path(basename)
            else:
                scene_path = get_maya_file(basename)
            # end handle absolute input
            mrvmaya.Scene.open(scene_path, force=True)
            print "Opened Scene: '%s'" % basename
            
            if debug:
                rval = func(self, *args, **kwargs)
                mrvmaya.Scene.new(force=1)
                return rval
            else:
                try:
                    return func(self, *args, **kwargs)
                finally:
                    mrvmaya.Scene.new(force=1)
            # END assure new scene is loaded after test - but allow debugging in case of exceptions ! 
        # END internal wrapper

        scene_loader.__name__ = func.__name__
        return scene_loader
    # END wrapper
    return wrapper

def with_undo(func):
    """All tests that require the undo system to be enabled must be decorated that 
    way as we will assure two things: 
     * If undo is globally disabled, we state that issue to stderr and exit the test
     * If undo is just disabled within maya, we will enable it and run the test"""
    import maya.cmds as cmds
    def wrapper(*args, **kwargs):
        if not int(os.environ.get('MRV_UNDO_ENABLED', "1")):
            print >> sys.stderr, "Skipped execution of test '%s' as undo was globally disabled" % func.__name__
            return 
        # END check for globally disabled
        
        # assure undo is enabled
        prev_state = cmds.undoInfo(q=1, st=1)
        if not prev_state:
            cmds.undoInfo(swf=1)
        # END force undo enabled
        
        try:
            return func(*args, **kwargs)
        finally:
            cmds.undoInfo(swf=prev_state)
        # END handle previous state
    # END wrapper
    wrapper.__name__ = func.__name__
    return wrapper
    
def with_persistence(func):
    """Simple utility decorator which enforces the persitence system to be loaded
    before the test runs"""
    import mrv.maya.nt
    def wrapper(*args, **kwargs):
        mrv.maya.nt.enforcePersistence()
        return func(*args, **kwargs)
    # END wrapper
    
    wrapper.__name__ = func.__name__
    return wrapper

def with_new_scene(func):
    """Utility which creates a new scene before the actual function is called"""
    import mrv.maya
    def wrapper(*args, **kwargs):
        mrv.maya.Scene.new(force=True)
        return func(*args, **kwargs)
    # END wrapper
    
    wrapper.__name__ = func.__name__
    return wrapper

#} END decorator


#{ TestBases 

# must not be put in __all__ !
class StandaloneTestBase(unittest.TestCase):
    """Provides a base implementation for all standalone tests which need to 
    initialize the maya module to operate. It will bail out if the module 
    is initialized already. Otherwise it will call the post_standalone_initialized
    method to allow additional tests to run.
    
    Before the maya standalone module is initialized, the setup_environment method
    will be called in order to adjust the configuration. Whether the post_standalone_initialized
    method runs or not, the undo_setup_environment method is called for you to undo your changes.
    
    It is advised to name your TestCase class in a descriptive way as it will show 
    up in the message printed if the test cannot run."""
    
    def setup_environment(self):
        raise NotImplementedError("To be implemented in subclass")
    
    def test_init_standalone(self):
        self.setup_environment()
        try:
            st = time.time()
            import mrv.maya
            # too fast ? It was loaded already as we have not been run standalone
            if time.time() - st < 0.1:
                print "%s standalone test bailed out at it couldn't be the first one to initialize mrv.maya" % type(self).__name__
                return
            # END handle non-standalone mode
            
            self.post_standalone_initialized()
        finally:
            self.undo_setup_environment()
        # END assure environment setup gets undone
            
    def undo_setup_environment(self):
        raise NotImplementedError("To be implemented in subclass")
        
    def post_standalone_initialized(self):
        raise NotImplementedError("To be implemented in subclass")
#} END testbases
