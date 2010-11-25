# -*- coding: utf-8 -*-
""" Test the quality assurance framework and it's mel bindings """
from mrv.test.maya import *
import mrv.automation.qa as bqa
import mrv.maya.automation.qa as qa
import mrv.automation.processes as processes
import mrv.test.automation.workflows as workflows
import mrv.test.automation.processes as processes
import maya.mel as mmel

#  create test methods
index_proc_create = """global proc string[] b_test_index( )
{
	return { "test1", "test1descr", 1, "test2", "test2descr", 1 };
}"""
mmel.eval( index_proc_create )

check_proc_create = """global proc string[] b_test_check( string $cname, int $should_fix )
{
	string $rval[] = { (string) 0, $cname };
	// have failed items if we do not fix it
	if( ! $should_fix )
		$rval[ size( $rval ) ] = "persp";
	return $rval;
}"""
mmel.eval( check_proc_create )


class TestMELQAProcess( processes.QACheckProcess, qa.QAMELMixin ):
	"""Test class providing some configuration"""
	mel_index_proc = "b_test_index"
	mel_check_proc = "b_test_check"

	def assureQuality( self, check, mode, *args, **kwargs ):
		"""Run mel checks"""
		assert self.isMELCheck( check )
		return self.handleMELCheck( check, mode )

class TestMELQAProcessDynamic( TestMELQAProcess ):

	static_mel_plugs = False

	# implement the method returning the checks
	def plugs( self, predicate = lambda p: True ):
		checks = self.melChecks( predicate )
		checks.extend( super( TestMELQAProcessDynamic, self ).plugs( predicate ) )
		return checks

# add instance to the workflow
workflows.qualitychecking.addNode( TestMELQAProcess( id="TestMELProcess" ) )
workflows.qualitychecking.addNode( TestMELQAProcessDynamic( id="TestMELProcessDynamic" ) )


class TestQualityAssurance( unittest.TestCase ):
	"""Test qa framework"""

	def test_melqa_workflow( self ):

		wfl = workflows.qualitychecking
		tprocess = wfl.TestMELProcess
		tprocessDynamic = wfl.TestMELProcessDynamic

		assert len( tprocess.listChecks() ) == 4
		assert len( tprocess.listMELChecks() ) == 2
		assert len( tprocessDynamic.listChecks() ) == 6
		assert len( tprocessDynamic.listMELChecks() ) == 4

		# run mel checks
		melchecks = tprocess.listMELChecks( )
		for mode in bqa.QAProcessBase.eMode:
			results = wfl.runChecks( melchecks, mode = mode )
			assert len( results ) == len( melchecks )

			for shell, result in results:
				if mode == tprocess.eMode.fix:
					assert result.isSuccessful()
					assert not result.failedItems()
				else:
					assert not result.isSuccessful()
					assert result.failedItems()
			# END for each shell's result
		# END for each mode


