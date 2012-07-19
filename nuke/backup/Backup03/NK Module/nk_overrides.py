
# -----------------------------------------------------
# This module contains functions that override and extend 
# the default behavior of nuke's internal functions
# ----------------------------------------------------

import nuke

nukeOriginalSelectedNodes = nuke.selectedNodes

def customSelectedNodes(nodeClass=None):
	# Tricks nuke.selectedNodes() to return a list of nodes *in the order by which they were selected*
	sel = nukeOriginalSelectedNodes(nodeClass) if nodeClass else nukeOriginalSelectedNodes()
	sel.reverse()
	return sel

nuke.selectedNodes = customSelectedNodes