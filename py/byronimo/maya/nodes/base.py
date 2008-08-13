"""B{byronimo.nodes.base}

Contains some basic  classes that are required to run the nodes system

All classes defined here can replace classes in the node type hierarachy if the name
matches. This allows to create hand-implemented types.

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


from byronimo.util import capitalize
from byronimo.maya.util import StandinClass
nodes = __import__( "byronimo.maya.nodes", globals(), locals(), ['nodes'] )
import maya.OpenMaya as api


############################
#### Methods 		  	####
##########################

def apiTypeToNodeTypeCls( apiobj ):
	""" Convert the given api object ( MObject ) to the respective python node type class  """ 
	fnDepend = api.MFnDependencyNode( apiobj )      
	mayaType = capitalize( fnDepend.typeName( ) )
	try: 
		nodeTypeCls = getattr( nodes, mayaType )
	except AttributeError:
		raise TypeError( "NodeType %s unknown - it cannot be wrapped" % mayaType ) 
	
	# CHECK FOR STANDIN CLASS 
	###########################
	# The class type could still be a standin - call it  
	if isinstance( nodeTypeCls, StandinClass ):
		nodeTypeCls = nodeTypeCls.createCls( )
	
	return nodeTypeCls

def toApiObject( nodeName, dagPlugs=True ):
	""" Get the API MPlug, MObject or (MObject, MComponent) tuple given the name 
	of an existing node, attribute, components selection
	@param dagPlugs: if True, plug result will be a tuple of type (MDagPath, MPlug)
	@note: based on pymel          
	""" 
	sel = api.MSelectionList()
	try:	# DEPEND NODE ?
		sel.add( nodeName )
	except:
		if "." in nodeName :
			# COMPOUND ATTRIBUTES
			#  sometimes the index might be left off somewhere in a compound attribute 
			# (ex 'Nexus.auxiliary.input' instead of 'Nexus.auxiliary[0].input' )
			#  but we can still get a representative plug. this will return the equivalent of 'Nexus.auxiliary[-1].input'
			try:
				buf = nodeName.split('.')
				obj = toApiObject( buf[0] )
				plug = api.MFnDependencyNode(obj).findPlug( buf[-1], False )
				if dagPlugs and isValidMDagPath(obj): 
					return (obj, plug)
				return plug
			except RuntimeError:
				return
	else:
		if "." in nodeName :
			try:
				# Plugs
				plug = api.MPlug()
				sel.getPlug( 0, plug )
				if dagPlugs:
					try:
						# Plugs with DagPaths
						sel.add( nodeName.split('.')[0] )
						dag = api.MDagPath()
						sel.getDagPath( 1, dag )
						#if isValidMDagPath(dag) :
						return (dag, plug)
					except RuntimeError: pass
				return plug
			
			except RuntimeError:
				# Components
				dag = api.MDagPath()
				comp = api.MObject()
				sel.getDagPath( 0, dag, comp )
				#if not isValidMDagPath(dag) :	 return
				return (dag, comp)
		else:
			try:
				# DagPaths
				dag = api.MDagPath()
				sel.getDagPath( 0, dag )
				#if not isValidMDagPath(dag) : return
				return dag
		                                                                                    
			except RuntimeError:
				# Objects
				obj = api.MObject()
				sel.getDependNode( 0, obj )			 
				#if not isValidMObject(obj) : return	 
				return obj
	# END if no exception on selectionList.add  
	return None
	

############################
#### Classes		  	####
##########################

class MayaNode( object ):
	"""Common base for all maya nodes, providing access to the maya internal object 
	representation
	Use this class to directly create a maya node of the required type"""
	__metaclass__ = nodes.MetaClassCreatorNodes
	
	def __new__ ( cls, *args, **kwargs ):
		"""return a class of the respective type
		@param args: arg[0] is the node to be wrapped
			- string: wrap the API object with the respective name 
			- MObject
			- MObjectHandle
			- MDagPath
		@todo: support for instances of MayaNodes ( as kind of copy constructure ) """
		

		if not args:
			raise ValueError( "First argument must specify the node to be wrapped" )
			
		objorname = args[0]
		apiobj = None
		
		# GET AN API OBJECT
		if isinstance( objorname, ( api.MObject, api.MDagPath ) ):
			apiobj = objorname
		elif isinstance( objorname, api.MObjectHandle ):
			apiobj = objorname.object()
		elif isinstance( objorname, basestring ):
			if objorname.find( '.' ) != -1:
				raise ValueError( "%s cannot be handled" % objorname ) 
			apiobj = toApiObject( objorname )
			
			# currently we only handle objects - subclasses will get the type they need
			if isinstance( apiobj, api.MDagPath ):
				apiobj = apiobj.node()
			
		else:
			raise ValueError( "objects of type %s cannot be handled" % type( objorname ) )
			
			
		
		if not apiobj or apiobj.isNull( ):
			raise ValueError( "object could not be handled: %s" % objorname )
		
		
		# get the node type class for the api type object
		nodeTypeCls = apiTypeToNodeTypeCls( apiobj )
		
		
		# NON-MAYA NODE Type 
		# if an explicit type was requested, assure we are at least compatible with 
		# the given cls type - our node type is supposed to be the most specialized one
		# cls is either of the same type as ours, or is a superclass 
		if cls is not MayaNode and nodeTypeCls is not cls:
			if not issubclass( nodeTypeCls, cls ):
				raise TypeError( "Explicit class %r must be %r or a superclass of it" % ( cls, nodeTypeCls ) )
			else:
				nodeTypeCls = cls						# respect the wish of the client
		# END if explicit class given 
		
		
		
		
		# FININSH INSTANCE 
		self = super( MayaNode, cls ).__new__( nodeTypeCls )
		self._apiobj = apiobj
		
		return self
	
	

class DependNode( MayaNode ):
	""" Implements access to dependency nodes 
	
	Depdency Nodes are manipulated using an MObjectHandle which is safest to go with, 
	but consumes more memory too !"""
	__metaclass__ = nodes.MetaClassCreatorNodes
	
	
	
	
class Entity( DependNode ):
	"""Common base for dagnodes and paritions"""
	__metaclass__ = nodes.MetaClassCreatorNodes


class DagNode( Entity ):
	""" Implements access to DAG nodes """
	__metaclass__ = nodes.MetaClassCreatorNodes
	
	

	
