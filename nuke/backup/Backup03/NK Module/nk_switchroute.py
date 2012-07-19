import nuke
import nukescripts
import re

def setSwitchRoute():
	""" Used to hook into addBeforeRender of Write nodes to enable rendering different 
	paths of the DAG"""
	try:
		route = nuke.thisNode()['switchroute'].value()
		nodename = nuke.thisNode().name()
		if route:
			ss = route.split(" ")
			for s in zip(ss[0::2],ss[1::2]):
				switchname = s[0]
				which = int(s[1])
				print "%s | %s -> %i" % (nodename, switchname, which)
				if nuke.exists(switchname):
					nuke.toNode(switchname)['which'].setValue(which)
				else:
					print "%s switch does not exists!" % name
	except NameError:
		pass
		
def getSwitchRoute():
	switches = [(n.name(),int(n['which'].value())) for n in nuke.allNodes("Switch")]
	if not switches:
		nuke.message("There are no Switches in this comp!")
		return
	state = " ".join([n[0]+" "+str(n[1]) for n in switches])
	nuke.thisNode()['switchroute'].setValue(state)
	b4render = nuke.thisNode()['beforeFrameRender'].value()
	if b4render:
		if re.search("setSwitchRoute",b4render):
			pass
		else:
			b4render = b4render + ";" + "nuke.setSwitchRoute()"
	else:
		b4render = "nuke.setSwitchRoute()"
	nuke.thisNode()['beforeFrameRender'].setValue(b4render)
	render_orders = [n['render_order'].value() for n in nuke.allNodes("Write") if n.name() != nuke.thisNode().name() ]
	if nuke.thisNode()['render_order'].value() in render_orders:
		from random import randrange
		nuke.thisNode()['render_order'].setValue(randrange(10000,20000))
		
def attach_switchRoute():
	n = nuke.thisNode()
	if nuke.thisClass() == "Write" and 'switchroute' not in n.knobs().keys():
		n.addKnob(nuke.String_Knob("switchroute","switchroute"))
		n.addKnob(nuke.PyScript_Knob("pyKnob_switchroute"," Get current route ", "nuke.getSwitchRoute()"))
	return n

nukescriptsOriginalExecutePanel = nukescripts.execute_panel

def custom_execute_panel(_list, exceptOnError = True):
	first,last = nuke.root().firstFrame(),nuke.root().lastFrame()
	_list = nuke.allNodes("Write") if _list[0]	== nuke.root() else _list
	_list = sorted(_list,key=lambda x: x['render_order'].value())
	for n in _list:
		nuke.scriptSave("")
		print "Start:%s" % n.name()
		nuke.execute(n.name(),first,last)
		print "Done:%s" % n.name()

nukescripts.execute_panel = custom_execute_panel
nuke.addOnUserCreate(attach_switchRoute)
nuke.getSwitchRoute = getSwitchRoute
nuke.setSwitchRoute = setSwitchRoute














