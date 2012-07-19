import nuke
import os
import sys
import re

nuke.addFormat("1280 720 0 0 1280 720 1 HD720p")
nuke.knobDefault("Root.format","HD720p")

toolbar = nuke.menu('Nodes')
NKMenu = toolbar.addMenu('NK')
GCMenu = toolbar.addMenu('Reactor')
NKMenu.addCommand("RV","rv()","Shift+f")
NKMenu.addCommand("Batch change selected nodes","nk.batchChangeSelected()","x")
NKMenu.addCommand("Mark In","nk.setRange(0)","Shift+i")
NKMenu.addCommand("Mark Out","nk.setRange(1)","Shift+o")
NKMenu.addCommand("New Scene","nk.nk_new_scene()","Shift+s")
NKMenu.addCommand("Connect","nk.nk_connect()","Shift+c")

# Autoloads any gizmos in .nuke

gizMenu = toolbar.addMenu('Gizmos')
for giz in [os.path.splitext(n)[0] for n in os.listdir(os.path.join(os.environ["HOME"],".nuke")) if re.search("gizmo",n)]:
	gizMenu.addCommand(giz,"nuke.createNode('%s')"%giz)

# In the nk.py module, autoloads any function whose name begins with nk
# and use docstring as menu label

for func in [f for f in dir(nk) if f.startswith("nk")]:
	f = eval("nk.%s" % func)
	label = [l.strip() for l in f.__doc__.split("\n")][1]
	NKMenu.addCommand(label,"nk.%s()" % func)
	
for func in [f for f in dir(nk) if f.startswith("reactor")]:
	f = eval("nk.%s" % func)
	label = [l.strip() for l in f.__doc__.split("\n")][1]
	GCMenu.addCommand(label,"nk.%s()" % func)