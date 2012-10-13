#-*-coding:utf-8-*-
"""
@package mrv.automation.report
@brief contains report implementations allowing to analyse the callgraph of 

@copyright 2012 Sebastian Thiel
"""


class ReportBase( object ):
    """Provides main interface for all reports as well as the basic implementation"""

    def __init__( self, callgraph ):
        """intiialize the report with the given callgraph"""
        self._callgraph = callgraph


    # -------------------------
    ## @name Interface
    # @{
    
    def makeReport( self ):
        """@return report as result of a prior Callgraph analysis"""
        raise NotImplementedError( "This method needs to be implemented by subclasses" )

    ## -- End Interface -- @}


class Plan( ReportBase ):
    """Create a plan-like text describing how the target is being made"""

    def _analyseCallgraph( self  ):
        """Create a list of ProcessData instances that reflects the call order"""
        kwargs = dict()
        kwargs[ 'reverse' ] = True
        return self._callgraph.toCallList( **kwargs )


    def makeReport( self, headline=None ):
        """
        @return list of strings ( lines ) resembling a plan-like formatting
            of the call graph
        @param headline line to be given as first line """
        cl = self._analyseCallgraph( )

        out = list()
        if headline:
            out.append( headline )

        for i,pedge in enumerate( cl ):
            sp,ep = pedge
            i += 1      # plans start at 1
            # its an edge
            if ep:
                line = "%i. %s provides %r through %s to %s" % ( i, sp.process.id(), sp.result(), sp.plug, ep.process.noun )
            else:
                # its root
                line = "%i. %s %s %r when asked for %s" % ( i, sp.process.id(), sp.process.verb, sp.result(), sp.plug )
            out.append( line )
        # END for each process data edge
        return out

