"""B{byronimo.maya.reference}

Allows convenient access and handling of references in an object oriented manner
@todo: more documentation

@newfield revision: Revision
@newfield id: SVN Id
"""
                                            
__author__='$Author: byron $'
__contact__='byron@byronimo.de'
__version__=1
__license__='MIT License'
__date__="$Date: 2008-05-29 02:30:46 +0200 (Thu, 29 May 2008) $"
__revision__="$Revision: 16 $"
__id__="$Id: configuration.py 16 2008-05-29 00:30:46Z byron $"
__copyright__='(c) 2008 Sebastian Thiel'

from byronimo.path import Path
from byronimo.exceptions import *
scene = __import__( "byronimo.maya.scene", globals(), locals(), ["scene"] )
from byronimo.maya.namespace import Namespace
import maya.cmds as cmds
from byronimo.util import iDagItem


################
## FILTERS ###
###########
#{ Exceptions
class FileReferenceError( ByronimoError ):
	pass 

#}

################
## FILTERS ###
###########
#{ Filters 



#}




################
## Classes ###
###########
class FileReference( Path, iDagItem ):
	"""Represents a Maya file reference
	@note: do not cache these instances but get a fresh one when you have to work with it"""
	
	
	editTypes = [	'setAttr','addAttr','deleteAttr','connectAttr','disconnectAttr','parent' ]
	
	def __new__( cls, filepath = None, refnode = None, **kwargs ):
		def handleCreation(  refnode ):
			""" Initialize the instance by a reference node - lets not trust paths """
			path = cmds.referenceQuery( refnode, filename=1 )
			buf = path.split( '{' )
			
			self = Path.__new__( cls, buf[0] )
			self._copynumber = 0
			self._refnode = refnode					# keep it for now 
			if len( buf ) > 1:
				self._copynumber = int( buf[1][:-1] )
			return self
		# END creation handler 
		
		if refnode:
			return handleCreation( refnode )
		if filepath:
			return handleCreation( cmds.referenceQuery( filepath, rfn=1 ) )
		raise ValueError( "Specify either filepath or refnode" )
	
	def __init__( self, *args, **kwargs ):
		""" Initialize our iDagItem base """
		return iDagItem.__init__( self, separator = '/' )
	
	#{ Static Methods 
	@staticmethod
	def create( filename, namespace, deferred = False ):
		raise NotImplementedError( )
	
	@staticmethod
	def remove( fileReference ):
		raise NotImplementedError( )
	
	@staticmethod
	def replace( fileReference, filepath ):
		raise NotImplementedError( )
		
	@staticmethod
	def importRef( fileReference, depth=1 ):
		"""Import the given fileReference until the given depth is reached
		@param fileReference: the reference to import
		@param depth: 
		   - x<1: import all references and subreferences
		   - x: import until level x is reached, 1 imports just fileReference such that
		   all its children are on the same level as fileReference was before import
		@return: list of fileReference objects that are now in the root namespace """ 
		raise NotImplementedError( )
	#}
	
	#{Edit Methods	
	def cleanup( self, unresolvedEdits = True, 
				 editTypes = editTypes ):
		"""remove unresolved edits or all edits on this reference
		@param unresolvedEdits: if True, only dangling connections will be removed, 
		if False, all reference edits will be removed - the reference will be unloaded for this.
		The loading state of the reference will stay unchanged after the operation.
		@param editTypes: list of edit types to remove during cleanup"""
		wasloaded = self.p_loaded
		if not unresolvedEdits:
			self.p_loaded = False
			
		for etype in editTypes:
			cmds.file( cr=self._refnode, editCommand=etype )
			
		if not unresolvedEdits:
			self.p_loaded = wasloaded
		
		
	def setLocked( self, state ):
		"""Set the reference to be locked or unlocked
		@param state: if True, the reference is locked , if False its unlocked and 
		can be altered"""
		if self.isLocked( ) == state:
			return 
			
		# unload ref 
		wasloaded = self.p_loaded
		self.p_loaded = False 
		
		# set locked
		cmds.setAttr( self._refnode+".locked", state )
		
		# reset the loading state
		self.p_loaded = wasloaded
		
		
	def setLoaded( self, state ):
		"""set the reference loaded or unloaded
		@param state: True = unload reference, True = load reference """
		
		if state == self.isLoaded( ):			# already desired state
			return
		
		if state:
			cmds.file( loadReference=self._refnode )
		else:
			cmds.file( unloadReference=self._refnode )
	
	
	def setNamespace( self, namespace ):
		"""set the reference to use the given namespace
		@param namespace: Namespace instance or name of the short namespace
		@raise RuntimeError: if namespace already exists or if reference is not root"""
		shortname = namespace
		if isinstance( namespace, Namespace ):
			shortname = namespace.getBasename( )
		
		# set the namespace
		cmds.file( self.getFullPath(), e=1, ns=shortname )
		
	#}END Edit Methods
	
	
	#{Query Methods
	def isLocked( self ):
		"""@return: True if reference is locked
		@todo: ues byronimo wrapped refnode here"""
		return cmds.getAttr( self._refnode + ".locked" )
		
	def isLoaded( self ):
		"""@return: True if the reference is loaded"""
		return cmds.file( rfn=self._refnode, q=1, dr=1 ) == False
		
	def getParent( self ):
		"""@return: the parent reference of this instance or None if we are root"""
		parentrfn = cmds.referenceQuery( self._refnode, rfn=1, p=1 )
		if not parentrfn:
			return None
		return FileReference( refnode = parentrfn )
		
	def getChildren( self , predicate = lambda x: True ):
		""" @return: all intermediate child references of this instance """
		return scene.Scene.lsReferences( referenceFile = self, predicate = predicate )
		
		
	def getCopyNumber( self ):
		"""@return: the references copy number - starting at 0 for the first reference"""
		return self._copynumber
		
	def getNamespace( self ):
		"""@return: namespace object of the namespace holding all objects in this reference"""
		fullpath = self.getFullPath()
		refspace = cmds.file( fullpath, q=1, ns=1 )
		parentspace = cmds.file( fullpath, q=1, pns=1 )[0]		# returns lists, although its always just one string
		if parentspace:
			parentspace += ":"
			
		return Namespace( ":" + parentspace + refspace )
			
	def getFullPath( self ):
		"""@return: string with full path including copy number"""
		suffix = ""
		if self._copynumber != 0:
			suffix = '{%i}' % self._copynumber
		return ( str(self) + suffix )
		
	#}END query methods
		
	#{ Properties 
	p_locked = property( isLocked, setLocked )
	p_loaded = property( isLoaded, setLoaded )
	p_copynumber = property( getCopyNumber )
	p_namespace = property( getNamespace, setNamespace )
	#}
		
	
	
