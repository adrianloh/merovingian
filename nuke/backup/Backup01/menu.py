import nuke
import nk
import os
import sys
import re

# ENVIRONMENT #
# JOBS and JOB must be set prior to launching Nuke.
# SHOT is temporarily set to pwd here upon launch and properly set by nk.initScriptEnv() when scripts are loaded.
# SCRIPTNAME is a shorthand for the name of the script minus the ".nk" extension.
# A JOB's directory "ecosystem" is expected to follow the structure:
#
#		job --> shot01 --> anything_optional --> shot01_testv1_v1.nk
# or:
#		job --> shot01 --> gi_test_shot01_v1.nk
#
# Note that the name of nuke scripts are expected to contain (anywhere) the name of their parenting SHOT directory.
# This is how nk.initScriptEnv() figures out SHOT from a script to script basis.

os.environ["JOBS"] = "G:/jobs"
os.environ["JOB"] = "%s/cup" % os.environ["JOBS"]
os.environ["SHOT"] = os.getcwd()
os.environ["SCRIPTNAME"] = "UNTITLED"

nuke.createNode = nk.customCreateNode
nuke.selectedNodes = nk.customSelectedNodes
nuke.getClipname = nk.customGetClipname
nuke.getFilename = nk.customGetClipname

nuke.addFormat("1280 720 0 0 1280 720 1 HD720p")
nuke.knobDefault("Root.format","HD720p")

toolbar = nuke.menu('Nodes')
myMenu = toolbar.addMenu('NK')
myMenu.addCommand("Mark In","nk.setRange(0)","Shift+i")
myMenu.addCommand("Mark Out","nk.setRange(1)","Shift+o")
myMenu.addCommand("New Scene","nk.nk_new_scene()","Shift+s")
myMenu.addCommand("Connect","nk.nk_connect()","Shift+c")

# Autoloads any gizmos in .nuke

dotnuke = "%s/.nuke"%os.environ["HOME"]
gizMenu = toolbar.addMenu('Gizmos')
for giz in [os.path.splitext(n)[0] for n in os.listdir(dotnuke) if re.search("gizmo",n)]:
	gizMenu.addCommand(giz,"nuke.createNode('%s')"%giz)

# In the nk.py module, autoloads any function whose name begins with nk

for func in [f for f in dir(nk) if f.startswith("nk")]:
	f = eval("nk.%s" % func)
	label = [l.strip() for l in f.__doc__.split("\n")][1]
	myMenu.addCommand(label,"nk.%s()" % func)

# Nuke 5.2 only hooks

if nuke.env["NukeVersionMajor"] >= 5 and nuke.env["NukeVersionMinor"] > 1:
	nuke.addBeforeRender(nk.createWriteDirs)
	nuke.addAfterFrameRender(nk.renderStatus2Twitter)
	nuke.addOnScriptLoad(nk.dynamicFavorites)
	nuke.addOnScriptLoad(nk.initScriptEnv)
	nuke.addOnScriptLoad(nk.initRelativePaths)
	nuke.addOnScriptSave(nk.initScriptEnv)