# -*- coding: utf-8 -*-
"""Test basic node features """
from mayarv.test.maya import *
import mayarv.maya as bmaya
import mayarv.maya.nodes as nodes
import maya.OpenMaya as api
import maya.cmds as cmds

class TestTransform( unittest.TestCase ):
	
	def test_tranformation_overrides(self):
		p = nodes.Node('persp')
		getters = ('getScale', 'getShear')
		setters = ('setScale', 'setShear')
		def cmp_val(lhs, rhs, loose):
			if loose:
				assert lhs != rhs
			else:
				assert lhs == rhs
		# END util
		
		def assert_values(fgetname, fsetname, loose):
			getter = getattr(p, fgetname)
			v = getter()
			assert isinstance(v, api.MVector)
			
			nv = api.MVector(i+v.x+1.0, i+v.y+2.0, i+v.z+3.0)
			getattr(p, fsetname)(nv)
			
			cmp_val(nv, getter(), loose)
			
			cmds.undo()
			cmp_val(v, getter(), loose)
			cmds.redo()
			cmp_val(nv, getter(), loose)
		# END utility
		
		for i,(fgetname, fsetname) in enumerate(zip(getters, setters)):
			assert_values(fgetname, fsetname, loose=False)
		# END for each fname
		
		setters = ("scaleBy", "shearBy")
		for i,(fgetname, fsetname) in enumerate(zip(getters, setters)):
			assert_values(fgetname, fsetname, loose=True)
		# END for each name
		
	def test_usage_examples(self):
		bmaya.Scene.new(force=True)
		# NOTE: If this test fails ( because of name changes for instance ), the 
		# documentation needs to be fixed as well, usage.rst.
		from mayarv.maya.nodes import *
		import __builtin__
		
		# NODES
		#######
		p = Node("persp")
		t = Node("time1")
		assert p == p
		assert p != t
		assert p in [p]
		
		s = __builtin__.set()
		s.add(p)
		s.add(t)
		assert p in s and t in s and len(s | s) == 2
		
		# getApiObject returns the api object which represents the underlying maya node best
		assert isinstance(p.getApiObject(), api.MDagPath)
		assert isinstance(t.getApiObject(), api.MObject)
		
		# api types
		assert isinstance(p, Transform) and p.getApiType() == api.MFn.kTransform
		assert isinstance(t, Time) and t.getApiType() == api.MFn.kTime
		assert p.hasFn(p.getApiType())
		
		# get the MObject repreentation
		assert isinstance(p.getMObject(), api.MObject) and isinstance(t.getMObject(), api.MObject)
		
		# DagNodes have a DagPath as well
		assert p.getDagPath() == p.getMDagPath()
		assert isinstance(p.getDagPath(), DagPath) and not isinstance(p.getMDagPath(), DagPath)
		
		
		# METHODS
		#########
		self.failUnlessRaises(AttributeError, getattr, p, 'doesnt_exist')
		
		assert p.getName == p.name
		
		assert isinstance(p.getMFnClasses(), list)
		
		# DAG NAVIGATION
		################
		ps = p.getChildren()[0]
		assert ps == p[0]
		assert ps[-1] == p
		
		assert ps == p.getShapes()[0]
		assert ps.getParent() == p == ps.getTransform()
		
		# filtering
		assert len(p.getChildrenByType(Transform)) == 0
		assert p.getChildrenByType(Camera) == p.getChildrenByType(Shape)
		
		# deep and iteration
		assert ps.iterParents().next() == p == ps.getRoot()
		assert ps.getParentDeep()[0] == p
		assert p.getChildrenDeep()[0] == ps
		
		# NODE CREATION
		###############
		cs = createNode("namespace:subspace:group|other:camera|other:cameraShape", "camera")
		assert len(cs.getParentDeep()) == 2
		
		m = Mesh()
		assert isinstance(m, Mesh) and m.isValid()
		
		assert m == Mesh(forceNewLeaf=False) 
		
		# NODE DUPLICATION
		##################
		# this duplicated tweaks, set and shader assignments as well
		md = m.duplicate()
		assert md != m
		
		# NAMESPACES
		#############
		ons = cs.getNamespace()
		assert ons == cs[-1].getNamespace()
		
		sns = cs[-2].getNamespace()
		assert sns != ons
		
		pns = sns.getParent()
		assert pns.getChildren()[0] == sns
		
		assert len(sns.getSelectionList()) == 1
		assert len(pns.listObjectStrings()) == 0
		assert len(pns.getSelectionList(depth=2)) == 1
		
		# DAG MANIPULATION
		##################
		csp = cs.getTransform()
		cs.setParent(p)
		assert cs.getInstanceCount(0) == 1
		csi = cs.addParent(csp)
		
		assert csi.isInstanced() and cs.getInstanceCount(0) == 2
		assert csi != cs
		assert csi.getMObject() == cs.getMObject()
		
		assert cs.getParentAtIndex(0) == p
		assert cs.getParentAtIndex(1) == csp
		
		p.removeChild(csi)
		assert not cs.isValid() and csi.isValid()
		assert not csi.isInstanced()
		
		
		# reparent
		cspp = csp[-1]
		csi.reparent(cspp)
		
		csp.unparent()
		assert csp.getParent() is None and len(csp.getChildren()) == 0
		assert len(cspp.getChildren()) == 1
		
		
		# NODE- AND GRAPH-ITERATION
		###########################
		for dagnode in it.iterDagNodes():
			assert isinstance(dagnode, DagNode)
			
		for dg_or_dagnode in it.iterDgNodes():
			assert isinstance(dg_or_dagnode, DependNode)
		
		rlm = Node("renderLayerManager")
		assert len(list(it.iterGraph(rlm))) == 2
		
		# SELECTIONLISTS
		################
		nl = (p, t, rlm)
		sl = toSelectionList(nl)
		assert isinstance(sl, api.MSelectionList) and len(sl) == 3
		
		sl2 = api.MSelectionList.fromList(nl)
		sl3 = api.MSelectionList.fromStrings([str(n) for n in nl])
		
		
		osl = getSelection()
		select(sl)
		select(p, t)
		# clear the selection
		select()
		assert len(getSelection()) == 0
		
		for n in sl:
			assert isinstance(n, DependNode)
		
		assert list(sl) == sl.toList()
		assert list(sl.toIter()) == list(it.iterSelectionList(sl))
		
		# OBJECTSETS AND PARTITIONS
		###########################
		objset = ObjectSet()
		aobjset = ObjectSet()
		partition = Partition()
		
		assert len(objset) == 0
		objset.addMembers(sl)
		objset.add(csp)
		aobjset.addMember(csi)
		assert len(objset)-1 == len(sl)
		assert len(aobjset) == 1
		assert csp in objset
		
		partition.addSets([objset, aobjset])
		assert objset in partition and aobjset in partition
		partition.discard(aobjset)
		assert aobjset not in partition
		
		assert len(objset + aobjset) == len(objset) + len(aobjset)
		assert len(objset & aobjset) == 0
		aobjset.add(p)
		assert len(aobjset) == 2
		assert len(aobjset & objset) == 1
		assert len(aobjset - objset) == 1
		
		assert len(aobjset.clear()) == 0
		
		
		# COMPONENTS AND COMPONENT ASSIGNMENTS
		######################################
		# create a polycube and pipe its output into our mesh shape
		isb = Node("initialShadingGroup")
		pc = PolyCube()
		pc.output > m.inMesh
		assert m.numVertices() == 8
		assert m not in isb                            # it has no shaders on object level
		assert len(m.getComponentAssignments()) == 0   # nor on component leveld 
		
		# object level
		m.addTo(isb)
		assert m in isb
		
		assert m.getSets(m.fSetsRenderable)[0] == isb
		m.removeFrom(isb)
		assert not m.isMemberOf(isb)
		
		# component level
		isb.add(m, m.cf[range(0,6,2)])     # add every second face
		isb.discard(m, m.cf[:])	            # remove all component assignments
		
		isb.add(m, m.cf[:3])				# add faces 0 to 2
		isb.add(m, m.cf[3])					# add single face 3
		isb.add(m, m.cf[4,5])				# add remaining faces
		
		# query assignments
		se, comp = m.getComponentAssignments()[0]
		assert se == isb
		e = comp.getElements()
		assert len(e) == 6					# we have added all 6 faces
		
		
		# Plugs and Attributes
		######################
		# PLUGS #
		assert isinstance(p.translate, api.MPlug)
		assert p.translate == p.findPlug('translate')
		assert p.t == p.translate
		
		# connections
		( p.tx > p.ty ) > p.tz		# parantheses enforce connection order in this case
		assert p.tx >= p.ty
		assert p.ty.isConnectedTo(p.tz)
		assert not p.tz >= p.ty
		
		( p.tx | p.ty ) | p.tz		# disconnect all
		assert len(p.ty.p_inputs) + len(p.tz.getInputs()) == 0
		assert p.tz.getInput().isNull()
		
		p.tx > p.tz
		self.failUnlessRaises(RuntimeError, p.ty.connectTo, p.tz, force=False)     # tz is already connected
		p.ty >> p.tz                                         # force the connection
		p.tz.disconnect()                                    # disconnect all
		
		# query
		assert isinstance(p.tx.asFloat(), float)
		assert isinstance(t.outTime.asMTime(), api.MTime)
		
		ninst = p.getInstanceNumber()
		pewm = p.worldMatrix.elementByLogicalIndex(ninst)
		
		matfn = api.MFnMatrixData(pewm.asMObject())
		matrix = matfn.matrix()                       # wrap data manually

		dat = pewm.asData()							# or get a wrapped version right away
		assert matrix == dat.matrix()				
	
		
		# set values
		newx = 10.0
		p.tx.setDouble(newx)
		assert p.tx.asDouble() == newx
		
		meshdata = m.outMesh.asMObject()
		meshfn = api.MFnMesh(meshdata)
		meshfn.deleteFace(0)                        # delete one face of copied cube data
		assert meshfn.numPolygons() == 5
		
		mc = Mesh()                                 # create new empty mesh to 
		mc.cachedInMesh.setMObject(meshdata)        # hold the new mesh in the scene
		assert mc.numPolygons() == 5
		assert m.numPolygons() == 6
		
		# compounds and arrays
		pc = p.t.getChildren()
		assert len(pc) == 3
		assert (pc[0] == p.tx) and (pc[1] == p.ty)
		assert pc[2] == p.t['tz']
		assert p.tx.getParent() == p.t
		assert p.t.isCompound()
		assert p.tx.isChild()
		
		assert p.wm.isArray()
		assert len(p.wm) == 1
		
		for element_plug in p.wm:
			assert element_plug.isElement()
		
		
		# ATTRIBUTES #
		cattr = CompoundAttribute.create("compound", "co")
		cattr.setArray(True)
		if cattr:
			sattr = TypedAttribute.create("string", "str", TypedAttribute.kString)
			pattr = NumericAttribute.createPoint("point", "p")
			mattr = MessageAttribute.create("mymessage", "mmsg")
			mattr.setArray(True)
			
			cattr.addChild(sattr)
			cattr.addChild(pattr)
			cattr.addChild(mattr)
		# END compound attribute
		
		n = Network()
		n.addAttribute(cattr)
		assert n.compound.isArray()
		assert n.compound.isCompound()
		assert len(n.compound.getChildren()) == 3
		assert n.compound['mymessage'].isArray()
		
		n.removeAttribute(n.compound.getAttribute())
		
		
		# MESH COMPONENT ITERATION
		average_x = 0.0
		for vit in m.vtx:                  # iterate the whole mesh
			average_x += vit.position().x
		average_x /= m.numVertices()
		assert m.vtx.iter.count() == m.numVertices()
		
		sid = 3
		for vit in m.vtx[sid:sid+3]:       # iterate subsets
			assert sid == vit.index()
			sid += 1
		
		for eit in m.e:                    # iterate edges
			eit.point(0); eit.point(1)
			
		for fit in m.f:                    # iterate faces
			fit.isStarlike(); fit.isPlanar()
			
		for mit in m.map:                  # iterate face-vertices
			mit.faceId(); mit.vertId() 
		
		
		
		# SELECTIONS
		#############
		# 
		
		
		
