"""B{byronimo.nodes.geometry}

Contains implementations ( or improvements ) to mayas geometric shapes

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

import base
import types
import maya.OpenMaya as api
import iterators

	
class Shape:
	"""Interface providing common methods to all geometry shapes as they can be shaded.
	They usually support per object and per component shader assignments
	
	@note: as shadingEngines are derived from objectSet, this class deliberatly uses 
	them interchangably when it comes to set handling.
	@note: for convenience, this class implements the shader related methods 
	whereever possible
	@note: bases determined by metaclass"""
	
	__metaclass__ = base.nodes.MetaClassCreatorNodes
	
	
	
	
	#{ preset type filters
	fSetsRenderable = base.SetFilter( api.MFn.kShadingEngine, False, 0 )	# shading engines only
	fSetsDeformer = base.SetFilter( api.MFn.kSet, True , 1)				# deformer sets only 
	#} END type filters 
	
	#{ Sets Interface
	
	def _parseSetConnections( self, allow_compoents ):
		"""Manually parses the set connections from self
		@return: tuple( MObjectArray( setapiobj ), MObjectArray( compapiobj ) ) if allow_compoents, otherwise
		just a list( setapiobj )"""
		sets = api.MObjectArray()
		iogplug = self._getIOGPlug()			# from DependNode
		
		# this will never fail - logcical index creates the plug as needed
		# and drops it if it is no longer required 
		iogplug = self.iog.getByLogicalIndex( self.getInstanceNumber() )
		if allow_compoents:
			components = api.MObjectArray()
			
			# take full assignments as well - make it work as the getConnectedSets api method
			for dplug in iogplug.getOutputs():
				sets.append( dplug.getNodeApiObj() )
				components.append( api.MObject() )
			# END full objecft assignments 
			
			for compplug in iogplug.objectGroups:
				for setplug in compplug.getOutputs():
					sets.append( setplug.getNodeApiObj() )		# connected set
					
					# get the component from the data  
					compdata = compplug.objectGrpCompList.asData()
					if compdata.getLength() == 1:			# this is what we can handle 
						components.append( compdata[0] ) 	# the component itself
					else:
						raise AssertionError( "more than one compoents in list" )
						
				# END for each set connected to component 
			# END for each component group
			
			return ( sets, components )
		else:
			for dplug in iogplug.getOutputs():
				sets.append( dplug.getNodeApiObj() )
			return sets 
		# END for each object grouop connection in iog
		
	
	def getComponentAssignments( self, setFilter = fSetsRenderable ):
		"""@return: list of tuples( objectSetNode, Component ) defininmg shader 
		assignments on per component basis.
		If a shader is assigned to the whole object, the component would be a null object, otherwise
		it is an instance of a wrapped IndexedComponent class
		@param setFilter: see L{getConnectedSets}
		@note: the sets order will be the order of connections of the respective component list 
		attributes at instObjGroups.objectGroups
		@note: currently only meshes and subdees support per component assignment, whereas only 
		meshes can have per component shader assignments
		@note: SubDivision Components cannot be supported as the component type kSubdivCVComponent
		cannot be wrapped into any component function set - reevaluate that with new maya versions !
		@note: deformer set component assignments are only returned for instance 0 ! They apply to all 
		output meshes though"""
		
		# SUBDEE SPECIAL CASE 
		#########################
		# cannot handle components for subdees - return them empty
		if self._apiobj.apiType() == api.MFn.kSubdiv:
			print "WARNING: components are not supported for Subdivision surfaces due to m8.5 api limitation"
			sets = self.getConnectedSets( setFilter = setFilter )
			return [ ( setnode, api.MObject() ) for setnode in sets ]
		# END subdee handling 
		
		sets = components = None 
		                            
		# MESHES AND NURBS 
		################## 
		# QUERY SETS AND COMPONENTS 
		# for non-meshes, we have to parse the components manually 
		if not self._apiobj.hasFn( api.MFn.kMesh ):
			# check full membership
			sets,components = self._parseSetConnections( True )
		# END non-mesh handling 
		else:
			# MESH - use the function set  
			# take all fSets by default, we do the filtering
			sets = api.MObjectArray()
			components = api.MObjectArray()
			self.getConnectedSetsAndMembers( self.getInstanceNumber(), sets, components, False )
		# END sets/components query 
		
		
		# wrap the sets and components
		outlist = list()
		for setobj,compobj in zip( sets, components ):
			if not setFilter( setobj ):
				continue
			
			setobj = base.Node( api.MObject( setobj ) )								# copy obj to get memory to python
			compobj = api.MObject( compobj )											# make it ours 
			if not compobj.isNull():
				compobj = base.Component( compobj )	  
				
			outlist.append( ( setobj, compobj ) ) 
		# END for each set/component pair
		return outlist
		
	#} END set interface 



class Mesh:
	"""Implemnetation of mesh related methods to make its handling more 
	convenient"""
	__metaclass__ = base.nodes.MetaClassCreatorNodes
