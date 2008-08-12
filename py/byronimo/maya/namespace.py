"""B{byronimo.maya.namespace}

Allows convenient access and handling of namespaces in an object oriented manner
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

from byronimo.maya.util import noneToList
from byronimo.util import iDagItem, CallOnDeletion
import maya.cmds as cmds


class Namespace( unicode, iDagItem ):
	""" Represents a Maya namespace
	Namespaces follow the given nameing conventions:
	   - Paths starting with a column are absolute
	      - :absolute:path
	   - Path separator is ':'"""
	
	
	rootNamespace = ':'
	_defaultns = [ 'UI','shared' ]			# default namespaces that we want to ignore in our listings  
	
	#{ Overridden Methods
		
	def __new__( cls, namespacepath, absolute = True ):
		""" Initialize the namespace with the given namespace path
		@param namespacepath: the namespace to wrap - it should be absolut to assure
		relative namespaces will not be interpreted in an unforseen manner ( as they 
		are relative to the currently set namespace
		Set it ":" to describe the root namespace 
		@param force_absolute: if True, incoming namespace names will be made absolute if not yet the case 
		@note: the namespace does not need to exist, but many methods will not work if so.
		NamespaceObjects returned by methods of this class are garantueed to exist"""
		
		if namespacepath != cls.rootNamespace:
			if absolute:
				if not namespacepath.startswith( ":" ):		# do not force absolute namespace !
					namespacepath = ":" + namespacepath
			# END if absolute 
			if namespacepath.endswith( ":" ):
				namespacepath = namespacepath[:-1]
		# END if its not the root namespace 
		return unicode.__new__( cls, namespacepath )
	
	def __init__( self , *args, **kwargs ):
		""" Initialise the base classes """
		return iDagItem.__init__( self, separator=":" )
		
	def __add__( self, other ):
		"""Properly catenate namespace objects - other must be relative namespace
		@return: new namespace object """
		if other.startswith( self._sep ):
			raise ValueError( "RHS namespace operant is expected to be relative, but was " + other )
		inbetween = self._sep
		if self.endswith( self._sep ):
			inbetween = ''
			
		return Namespace( "%s%s%s" % ( self, inbetween, other ) )
	#}END Overridden Methods

	#{Edit Methods
	@staticmethod
	def getCurrent( ):
		"""@return: the currently set absolute namespace """
		# will return namespace relative to the root - thus is absolute in some sense
		nsname = cmds.namespaceInfo( cur = 1 )
		if not nsname.startswith( ':' ):		# assure we return an absoslute namespace
			nsname = ":" + nsname
		return Namespace( nsname )
		
	@staticmethod
	def create( namespaceName ):
		"""Create a new namespace
		@param namespaceName: the name of the namespace, absolute or relative - 
		it may contain subspaces too, i.e. :foo:bar.
		fred:subfred is a relative namespace, created in the currently active namespace
		@return: the create Namespace object"""
		newns = Namespace( namespaceName )
		
		if newns.exists():		 # skip work
			return newns
		
		previousns = Namespace.getCurrent()
		cleanup = CallOnDeletion( None )
		if newns.isAbsolute():	# assure root is current if we are having an absolute name 
			Namespace( Namespace.rootNamespace ).setCurrent( )
			cleanup.callableobj = lambda : previousns.setCurrent()
		
		# create each token accordingly ( its not root here )
		tokens = newns.split( newns._sep )
		for i,token in enumerate( tokens ):		# skip the root namespac
			base = Namespace( ':'.join( tokens[:i+1] ) )
			if base.exists( ):
				continue
			# otherwise add the baes to its parent ( that should exist 
			cmds.namespace( p=base.getParent() , add=base.getBasename() )
		# END for each token
		
		return newns
		
		
	def rename( self, newName ):
		"""Rename this namespace to newName - the original namespace will cease to exist
		@note: if the namespace already exists, the existing one will be returned with 
		all objects from this one added accordingly
		@param newName: the absolute name of the new namespace
		@return: Namespace with the new name"""
		# TODO: actually the objects 
		newnamespace = Namespace( newName )
		
		
		# recursively move children
		def moveChildren( curparent, newname ):
			for child in curparent.getChildren( ):
				moveChildren( child, newname + child.getBasename( ) )
			# all children should be gone now, move the
			curparent.delete( move_to_namespace = newname, autocreate=True )
		# END internal method
		moveChildren( self, newnamespace )
		return newnamespace
		
	def moveObjects( self, targetNamespace, force = True, autocreate=True ):
		"""Move objects from this to the targetNamespace
		@param force: if True, namespace clashes will be resolved by renaming, if false 
		possible clashes would result in an error
		@param autocreate: if True, targetNamespace will be created if it does not exist yet"""
		targetNamespace = Namespace( targetNamespace )
		if autocreate and not targetNamespace.exists( ):
			targetNamespace = Namespace.create( targetNamespace )
			
		cmds.namespace( mv=( self, targetNamespace ), force = force )
	
	def delete( self, move_to_namespace = rootNamespace, autocreate=True ):
		"""Delete this namespace and move it's obejcts to the given move_to_namespace
		@param move_to_namespace: if None, the namespace to be deleted must be empty
		If Namespace, objects in this namespace will be moved there prior to namespace deletion
		move_to_namespace must exist
		@param autocreate: if True, move_to_namespace will be created if it does not exist yet
		@note: can handle sub-namespace properly
		@raise RuntimeError:"""
		if self == self.rootNamespace:
			raise ValueError( "Cannot delete root namespace" )
		
		if not self.exists():					# its already gone - all fine
			return
		
		# assure we have a namespace type
		if move_to_namespace:
			move_to_namespace = Namespace( move_to_namespace )
			
		# assure we do not loose the current namespace - the maya methods could easily fail
		previousns = Namespace.getCurrent( )
		cleanup = CallOnDeletion( None ) 
		if previousns != self:		# cannot reset future deleted namespace
			cleanup.callableobj = lambda : previousns.setCurrent()
		
		
		# recurse into children for deletion
		for childns in self.getChildren( ):
			childns.delete( move_to_namespace = move_to_namespace )
			
		# make ourselves current 
		self.setCurrent( )
		
		if move_to_namespace:
			self.moveObjects( move_to_namespace, autocreate=autocreate )
		 
		# finally delete the namespace
		cmds.namespace( rm=self )
		
	
	def setCurrent( self ):
		"""Set this namespace to be the current one - new objects will be put in it 
		by default"""
		cmds.namespace( set = self )
	
	#}
	
	#{Query Methods
	def exists( self ):
		"""@return: True if this namespace exists"""
		return cmds.namespace( ex=self )
		
	def isAbsolute( self ):
		"""@return: True if this namespace is an absolut one, defining a namespace
		from the root namespace like ":foo:bar"""
		return self.startswith( self._sep )
		
	def getParent( self ):
		"""@return: parent namespace of this instance"""
		if self == self.rootNamespace:
			return None
			
		parent = iDagItem.getParent( self )	# considers children like ":bar" being a root
		if parent == None:	# we are just child of the root namespcae
			parent = self.rootNamespace
		return Namespace( parent )
		
	def getChildren( self, predicate = lambda x: True ):
		"""@return: list of child namespaces
		@param predicate: return True to include x in result"""
		lastcurrent = self.getCurrent()
		self.setCurrent( )
		out = []
		for ns in noneToList( cmds.namespaceInfo( lon=1 ) ):		# returns root-relative names !
			if ns in self._defaultns or not predicate( ns ):
				continue
			out.append( Namespace( ns ) )
		# END for each subspace
		lastcurrent.setCurrent( )
		
		return out

	def getRelativeNamespace( self, basenamespace ):
		"""@return: this namespace relative to the given basenamespace 
		@param basenamespace: the namespace to which the returned one should be 
		relative too
		@raise ValueError: If this or basenamespace is not absolule or if no relative 
		namespace exists
		@return: relative namespace"""
		if not self.isAbsolute() or not basenamespace.isAbsolute( ):
			raise ValueError( "All involved namespaces need to be absoslute: " + self + " , " + basenamespace )
		
		suffix = self._sep
		if basenamespace.endswith( self._sep ):
			suffix = ''
		relnamespace = Namespace( self.replace( str( basenamespace ) + suffix, '' ) )
	
	def getObjectsIter( self ):
		"""@return: generator returning all objects in this namespace"""
		raise NotImplementedError()
		
		
	#} END query methods 
