#-*-coding:utf-8-*-
"""
@package mrv.test.automation.workflows
@brief tests for mrv.automation.workflows

@copyright 2012 Sebastian Thiel
"""

import mrv.test.automation.processes as process # assure procs are initialized
import mrv.automation.base as wflbase
from mrv.path import make_path
from mrv.automation.qa import QAWorkflow

# ==============================================================================
## @name Interface
# ------------------------------------------------------------------------------
## @{

def createWorkflow( workflowName ):
    """Create the workflow matching the given name """
    return wflbase.loadWorkflowFromDotFile( make_path( __file__ ).parent() / workflowName + ".dot" )
    
## -- End Interface -- @}


# ==============================================================================
## @name Initialization
# ------------------------------------------------------------------------------
## @{

def init_loadWorkflows( ):
    _this_module = __import__( "mrv.test.automation.workflows", globals(), locals(), ['workflows'] )
    wflbase.addWorkflowsFromDotFiles( _this_module, make_path( __file__ ).parent().glob( "*.dot" ) )
    wflbase.addWorkflowsFromDotFiles( _this_module, make_path( __file__ ).parent().glob( "*.dotQA" ), workflowcls = QAWorkflow )

## -- End Initialization -- @}

# load all the test workflows
init_loadWorkflows()
