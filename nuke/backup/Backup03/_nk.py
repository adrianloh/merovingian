import nuke
import nukescripts
import re
import os
import random
import threading
from custom import *
from subprocess import Popen,PIPE
import time
import base64

# NOTE: When naming functions, functions that begin with nk are automatically 
# loaded by menu.py and words should be dilineated with undescores. They *must*
# contain docstrings, the first line of which is used as the label of the function
# in nuke's menus. "Internal" functions (aka functions that cannot be called 
# directly from the UI) should be camelcased.

# GLOBALS

NUKE_PATH ="C:\\bin\\nukex.cmd"
os.environ['COMMON'] = "G:\\jobs\\temp"

# -------------- REACTOR INTERFACE ---------------- #

#from reactorDB import *

import datetime

from couchdb import *

db = Database("http://127.0.0.1:8080/nuke_reactor")

def reactor_newProject():
	"""
	New Project
	"""
	p = nuke.Panel("Project Registration")
	p.addSingleLineInput("Name","")
	p.addSingleLineInput("ID","")
	p.show()
	n = p.value("Name")
	pid = p.value("ID")
	pp = Projects(name=n,id=pid)
	pp.save()

def reactor_newShot(sid="",root=""):
	"""
	New Shot
	"""
	projects = Projects.get()
	opts = " ".join(["\"%s\""%i.name for i in projects])
	
	p = nuke.Panel("Shot Registration")
	p.addEnumerationPulldown("Project",opts)
	p.addSingleLineInput("Shot ID",sid)
	p.addSingleLineInput("Root name",root)
	p.show()

	proj = p.value("Project") and p.value("Project") or projects[0].name
	pid = [n.id for n in projects if n.name==proj][0]
	sid = p.value("Shot ID")
	root = p.value("Root name")

	nuke.root()['JOB'].setValue(pid)
	nuke.root()['ID'].setValue(sid)
	nuke.root()['SHOTROOT'].setValue(root)

	ss = Shots(project_id=pid,id=sid,shotroot=root)
	ss.save()

def reactor_saveToDB():
	"""
	DB Save
	"""
	
	h = {}
	h['job'] = nuke.root()['JOB'].value().upper()
	h['shot'] = nuke.root()['SHOT'].value().upper()
	h['title'] = nuke.root()['title'].value().upper()
	h['major'] = nuke.root()['versionMajor'].value().__str__()
	h['minor'] = nuke.root()['versionMinor'].value().__str__()
	h['modtime'] = time.strftime("%Y-%b-%d-%H%M%S",time.localtime())

	_id = h['job'] + "-" \
		+ h['shot'] + "__" \
		+ h['title'] + "__" \
		+ h['major'] + "." \
		+ h['minor'] + "__" \
		+ h['modtime']

	h['root'] = nuke.root()['SHOTROOT'].value()
	h['artist comments'] = nuke.root()['label'].value()
	h['dimension'] = "%ix%i" % (nuke.root().width(),nuke.root().height())
	h['fps'] = nuke.root()['fps'].value()
		
	for x in ('Read','Write'):
		y = x.lower()+"s"
		h[y] = {}
		for n in nuke.allNodes(x):
			h[y][n.name()] = nuke.filename(n)

	scriptpath = os.path.join(os.environ["TEMP"],_id+".nk")
	nuke.scriptSaveAs(scriptpath,overwrite=1)
	db[_id] = h
	h = db[_id]
	db.put_attachment(h, open(scriptpath).read(), _id+".nk", 'application/nuke-x' )

def reactor_major_Up():
	"""
	Version Major++
	"""
	version_change(0,0)

def reactor_minor_Up():
	"""
	Version Minor++
	"""
	version_change(1,0)

def version_change(i,n):
	m = (i==0) and 'versionMajor' or 'versionMinor'
	vr = nuke.root()[m].value()
	if n == 0:
		nuke.root()[m].setValue(vr+1)
	else:
		nuke.root()[m].setValue(vr-1)

# -------------- CALLBACK FUNCTIONS ---------------- #

def initRelativePaths():
	"""
	Resolve all file paths into relative paths
	"""
	def toRelativePath(p):
		for i in path_resolution_order:
			p = re.sub(os.environ[i],"[getenv %s]"%i,p,1)
		return p
	
	for n in nuke.allNodes():
		fn = nuke.filename(n)
		if fn:
			fn = toRelativePath(fn)
			n['file'].setValue(fn)

def afterRender():
	sf = "%s/notify.wav" % os.path.join(os.environ['HOME'],".nuke")
	if nuke.env["WIN32"]:
		import winsound
		winsound.PlaySound(sf, winsound.SND_FILENAME|winsound.SND_ASYNC)

def dynamicFavorites():
	def addFav(path):
		name = os.path.split(path)[-1]
		nuke.addFavoriteDir(name,path)

	addFav(os.environ["SHOTROOT"])

# -------------- KNOB CREATION ---------------- #

def all_labels(n):
	""" Return all labels of knobs"""
	return [n[i].label() for i in n.knobs()]
	
def all_names(n):
	""" Return all variable names of knobs"""
	return [n[i].name() for i in n.knobs()]

def pyScriptKnob(label,script):
	K = nuke.PyScript_Knob(randstring(10),label)
	K.setValue(script)
	return K

def attach_file_operations(n):
	if 'fileops' not in all_names(n):
		n = draw_line(n,"File Operations")
		n.addKnob(nuke.PyScript_Knob("copyBtn","Copy","nk.file(0)"))
		n.addKnob(nuke.PyScript_Knob("moveBtn","Move","nk.file(1)"))
		n.addKnob(nuke.Boolean_Knob("update_source","update_source"))
		n['update_source'].setValue(1)
	return n

def attach_range(n):
	if 'range' not in all_names(n):
		k = nuke.UV_Knob("range","render range")
		n.addKnob(k)
		n["range"].setValue([nuke.root().firstFrame(),nuke.root().lastFrame()])
	return n

def attach_switch_routing(n):
	if 'switchroute' not in all_names(n):
		n.addKnob(nuke.String_Knob("switchroute","switchroute"))
		n.addKnob(pyScriptKnob(" Get current route ","nk.setSwitchRoute()"))
	return n

def attach_write_status(n):
	# NOTE: renderStatusItems is defined in plugins/init.py
	if 'status' not in all_names(n):
		n.addKnob(nuke.Enumeration_Knob("status","status",renderStatusItems))
	return n

def draw_line(n,label):
	n.addKnob(nuke.Text_Knob(randstring(10),label))
	return n

# -------------- NUKE OVERRIDES ---------------- #

nukeOriginalSelectedNodes = nuke.selectedNodes
nukeOriginalGetClipname = nuke.getClipname
nukeOriginalGetFilename = nuke.getFilename
nukeOriginalExecuteMultiple = nuke.executeMultiple

def deprecated_toRelativePath(path,returnRange=True):
	"""
	Absolute filepaths are resolved relative to the order:
	Script -> Job -> Jobs
	"""
	jobs = os.environ['JOBS']
	job = os.environ['JOB']
	shot = os.environ['SHOTROOT']
	range = re.findall("(\d+-\d+)$",path)
	if range:
		fn = " ".join(path.split(" ")[:-1])
		range = range[0]
	else:
		fn = path
	if fn.startswith(shot):
		p = re.sub(shot,"[getenv SHOTROOT]",fn)
	elif fn.startswith(job):
		p = re.sub(job,"[getenv JOB]",fn)
	elif fn.startswith(jobs):
		p = re.sub(jobs,"[getenv JOBS]",fn)
	else:
		p = fn
	if returnRange and range:
		return "%s %s" % (p,range)
	else:
		return p

def customSelectedNodes(nodeClass=None):
	# Tricks nuke.selectedNodes() to return a list of nodes *in the order by which they were selected*
	sel = nukeOriginalSelectedNodes(nodeClass) if nodeClass else nukeOriginalSelectedNodes()
	sel.reverse()
	return sel

def customizeNodeOnUserCreate():
	n = nuke.thisNode()
	nClass = nuke.thisClass()

	if nClass == "Read":
		n = attach_file_operations(n)

	if nClass == "Write":
		n = attach_range(n)	
		n = attach_switch_routing(n)
		n = attach_write_status(n)
		n = attach_file_operations(n)
		n["label"].setValue("[knob range]\n[knob status]")
		n['file'].setValue("[file dirname [value root.name]]/[knob name].%%05d.exr")

	if nClass == "RotoPaint":
		n['output'].setValue("alpha")	

	if nClass == "Switch":
		n['label'].setValue("[knob which]")
		n['note_font'].setValue("Arial Bold")
		n['note_font_size'].setValue(20)

	if nClass == "Card2":
		n['label'].setValue("[knob translate.x] [knob translate.y] [knob translate.z]")

def deprecated_customGetClipname(message,multiple=True):
	files = nukeOriginalGetClipname(message,multiple=True)
	if nuke.root().name() == "Root":
		# If this is a new unsaved script
		return files
	else:
		# If this is a saved script, attempt to resolve relative paths
		try:
			return [toRelativePath(f) for f in files]
		except:
			pass

nuke.selectedNodes = customSelectedNodes
#nuke.getClipname = customGetClipname
#nuke.getFilename = customGetClipname

# -------------- LAZY SCRIPTING ---------------- #

def this():
	return nuke.selectedNode()
	
def these():
	return nuke.selectedNodes()

def val(obj,parm,value=None):
	if value:
		obj[parm].setValue(value)
		return obj
	else:
		return obj[parm].value()

def animate(obj,parm,curve):
	"""
	Animate parameters in the form:
		nk.animate(node,parameter,[ [frame1,(x,y,z)] , [frame2,(x,y,z)], [frame3,(x,y,z)] ])
	"""
	obj[parm].setAnimated()
	for animTuple in curve:
		[t,v] = animTuple
		try:
			for i,vv in enumerate(v):
				obj[parm].setValueAt(vv,t,i)
		except TypeError:
			obj[parm].setValueAt(v,t)

def dirr(k=None):
	"""
	Returns all callable methods of nuke that match the string k.
	If k is not given, returns everything.
	"""
	k = k if k else "."
	for nn in sorted([n for n in dir(nuke) if re.search(k,n,re.I)]):
		print nn

# -------------- NK AUTOLOADS FACELESS FUNCTIONS ---------------- #

def nk_align_horizontal():
	"""
	===
	"""
	align("horz")
	
def nk_align_vertical():
	"""
	||
	"""
	align("vert")

def nk_select_all_dependencies():
	"""
	Select all dependencies
	"""
	d = allDependencies(nuke.selectedNode())
	[n['selected'].setValue(True) for n in d]

# -------------- FACELESS FUNCTIONS ---------------- #

def nk_backburner():
	"""
	Background render
	"""
	import shutil
	nuke.scriptSave()
	op = nuke.root()['name'].value()
	name = nuke.selectedNode().name()
	np = op+"%s.bburn"%name
	shutil.copy2(op,np)
	ranges = "-".join([str(int(f)) for f in nuke.selectedNode()['range'].value()])
	cmd = "%s -m %i -F %s -X %s -ix %s" % (NUKE_PATH,int(nuke.env['numCPUs']/2),ranges,name,np)
	print cmd
	
	def render():
		print "Background rendering %s" % name
		Popen(cmd).wait()
		nuke.executeInMainThread(nuke.toNode(name)['tile_color'].setValue,552079871) #TODO: This executes but doesn't refresh in the DAG
		nuke.executeInMainThread(nuke.toNode(name)['postage_stamp'].setValue,True)
		nuke.executeInMainThread(nuke.toNode(name)['reading'].setValue,True)
		nuke.executeInMainThread(nuke.toNode(name)['status'].setValue,"Review")
		print "Background rendering done! %s" % name
		os.remove(np)

	this = nuke.toNode(name)
	this['tile_color'].setValue(943405567)
	this['postage_stamp'].setValue(False)
	this['reading'].setValue(False)
	T = threading.Thread(None,render)
	T.start()

def setSwitchRoute():
	switches = [(n.name(),int(n['which'].value())) for n in nuke.allNodes("Switch")]
	state = " ".join([n[0]+" "+str(n[1]) for n in switches])
	nuke.thisNode()['switchroute'].setValue(state)

def batchChangeSelected():
	"""
	Change parameters command-line style in GUI
	"""
	input = nuke.getInput("""Eg. translate=[0,1,3] / rotate=90.0 / label="some text" """)
	try:
		param,value = input.split("=")
		[n[param].setValue(eval(value)) for n in nuke.selectedNodes()]
	except:
		pass

def file(oper):
	"""
	Enables copying/moving source files of Read/Write nodes.
	For Writes, the nodes should have the custom parameters:
		BOOLEAN_KNOB:'source_update'
		UV_KNOB:'range'
	Dialog box enables choosing a destination directory 
	to relocate/copy files. Optionally, if a new name is entered,
	the files will be moved/copied and finally renamed.
	"""
	import shutil
	n = nuke.thisNode()
	first = last = None
	if n.Class() == "Read":
		first = n['first'].value()
		last = n['last'].value()
	elif n.Class() == "Write":
		try:
			first,last = n['range'].value()
		except NameError:
			attach_range(n)
			nuke.message("Please set range and try again")
	else:
		pass
	if first and last:
		old_path = os.path.dirname(nuke.filename(n))
		new_path = nukeOriginalGetFilename("Choose a new location...")
		rename = True if re.search(r'%0\dd',new_path) else False
		if rename:
			if not os.path.exists(os.path.dirname(new_path)):
				os.mkdir(os.path.dirname(new_path))
		else:
			if not os.path.exists(new_path):
				os.mkdir(new_path)
		if os.path.isdir(new_path) and new_path.endswith("/") is False:
			new_path += "/"
		get_path = lambda p: new_path%i if rename else new_path
		files = [(nuke.filename(n)%i,get_path(i)) for i in range(first,last+1) if os.path.exists(nuke.filename(n)%i)]
		if oper==1:
			mainMsg = "Relocating files..."
			subMsg = "Moved"
		else:
			mainMsg = "Copying files..."
			subMsg = "Copied"
		task = nuke.ProgressTask(mainMsg)
		T = len(files)
		good = 0
		for (i,f) in enumerate(files):
			op,np = f[0],f[1]
			print "%s --> %s" % (op,np)
			try:
				shutil.copy2(op,np)
				good+=1
				task.setMessage("%s:%s"%(subMsg,op))
				x = int((i/float(T)*100))
				task.setProgress(x)
			except:
				break
		if good == T:
			if oper==1:
				try:
					[os.remove(f[0]) for f in files]
					nuke.message("All files were relocated")
				except:
					nuke.message("All files were copied but originals could not be removed")
			else:
				nuke.message("All files were copied")
			if n['update_source'].value():
				filename = os.path.split(nuke.filename(n))[-1]
				set_new_path = rename and new_path or new_path+filename
				n['file'].setValue(set_new_path)
	else:
		pass

def setRange(n):
	"""
	Set In and Out points of the *selected Viewer*. Meant to be key-binded to
	achieve FCP-like functionality.
	"""
	viewer = nuke.selectedNode()
	frame = nuke.frame()
	if viewer.Class() == "Viewer":
		viewer['frame_range_lock'].setValue(True)
		i,o = re.split("\W",viewer['frame_range'].value())
		new_range = (n == 0) and (frame,o) or (i,frame)
		viewer['frame_range'].setValue("%s %s" % new_range)
	else:
		pass

def group(nodes):
	[n['selected'].setValue(False) for n in nuke.allNodes()]
	[n['selected'].setValue(True) for n in nodes]
	nuke.makeGroup()

def align(direction):
	
	def cmpX(x,y):
		return (x.xpos() > y.xpos()) and 1 or -1

	def cmpY(x,y):
		return (x.ypos() > y.ypos()) and -1 or 1

	nodes = [n for n in sorted(nuke.selectedNodes(),cmp=cmpX)]
	ypos = [n.ypos() for n in nodes]
	xpos = [n.xpos() for n in nodes]

	if direction == "horz":
		med = min(ypos)
		leftmost = min(xpos)
		[n['ypos'].setValue(med) for n in nodes]
		[n['xpos'].setValue(leftmost+(i*100)) for (i,n) in enumerate(nodes)]
	elif direction == "vert":
		med = min(xpos)
		topmost = nodes[0].ypos()
		[n['xpos'].setValue(med) for n in nodes]
		[n['ypos'].setValue(topmost+(i*125)) for (i,n) in enumerate(nodes)]

def getClips(dir,format="nuke",symbol="@"):
	"""
	Given a directory, returns a dictionary of sequence files in the form:
		dict[sequence_template] = [first_frame,last_frame]
	e.g.
		when format is "nuke":
			d[sequence_v1.%05d.exr] = [1,100]
		when format is "shake":
			d[sequence_v1.@@@@@@.exr] = [1,100]
	"""
	
	d = {}
	r = {}

	def make_pattern(filename):
		"""
		Creates a regular expression pattern from a filename, aka a "template"
		to match against other files. Assumes that leftmost consecutive digits 
		is the "index counter". E.g:
			shot01_project1234_version01.0001.exr #-> shot01_project1234_version01.\d\d\d\d.exr
		"""
		sf = re.sub('\d',"@",fn)
		rmost_counter = re.findall("@{1,}",sf)[-1]
		pat_len = len(rmost_counter)
		pat_position = sf.rindex(rmost_counter)
		bfn = re.findall(".",filename)
		for i in range(pat_len):
			pp = pat_position+i
			bfn[pp] = r"\d"
		t = "^"+"".join(bfn)+"$"
		return t
		
	os.chdir(dir)

	fff = [f for f in os.listdir(dir) if os.path.isfile(f)]
	
	if fff:

		for fn in fff:
			template = make_pattern(fn)
			if template in d:
				continue
			else:
				d.setdefault(template,[])

		for t in d.keys():
			for f in fff:
				if re.search(t,f):
					d[t].append(f)

		for dr in d.keys():
			c = dr.count("\d")
			printf = re.sub("(\\\d)+","%%0%id"%c,dr)[1:-1]
			substr = re.sub("\\\d","%s"%symbol,dr)[1:-1]
			np = re.sub("(\\\d)+","("+"\d"*c+")",dr)
			cc = sorted(d[dr])
			first = int(re.findall(np,cc[0])[0])
			last = int(re.findall(np,cc[-1])[0])
			if format == "nuke":
				r[printf] = [first,last]
			elif format == "shake":
				r[substr] = [first,last]

	return r

def allDependencies(source):
	"""
	Returns a list containing *only* and *all* ancestors of a given node 
	aka. all nodes required to produce the output of the specified node.
	"""
	d = []
	g = []
	[g.append(n) for n in nuke.dependencies(source)]
	while len(g) != 0:
		n = g.pop()
		d.append(n)
		[g.append(n) for n in nuke.dependencies(n)]
	return d

# -------------- STUFF THEY SHOULD'VE THOUGHT OF ---------------- #

def nk_new_scene(nodes=None):
	""" 
	New scene
	Creates a new 3D scene with renderer and a camera attached. If invoked with 
	nodes selected, they are fed into the 3D Scene node.
	"""
	if not nodes:
		nodes = nuke.selectedNodes()
	if nodes != [] and nodes[-1].Class() == "Scene":
		scene = nodes[-1]
		inputs = nodes[0:-1]
	else:
		scene = nuke.nodes.Scene()
		camera = nuke.nodes.Camera2()
		val(camera,"translate",[0,0,1])
		render = nuke.nodes.ScanlineRender()
		scene.setInput(scene.inputs(),camera)
		render.setInput(2,camera)
		render.setInput(1,scene)
		inputs = nodes
	for input in inputs:
		connected = scene.setInput(scene.inputs(),input)
		if not connected:
			card = nuke.nodes.Card()
			card.setInput(0,input)
			scene.setInput(scene.inputs(),card)
	return scene

def nk_autoBackdrop():
	"""
	Autobackdrop
	"""
	import operator, random
	selNodes = nuke.selectedNodes()
	if not selNodes:
		return nuke.nodes.BackdropNode()
	positions = [(i.xpos(), i.ypos()) for i in selNodes]
	xPos = sorted(positions, key = operator.itemgetter(0))
	yPos = sorted(positions, key = operator.itemgetter(1))
	xMinMaxPos = (xPos[0][0], xPos[-1:][0][0])
	yMinMaxPos = (yPos[0][1], yPos[-1:][0][1])
	n = nuke.nodes.BackdropNode(xpos = xMinMaxPos[0]-10,
				    bdwidth = xMinMaxPos[1]-xMinMaxPos[0]+110,
				    ypos = yMinMaxPos[0]-85,
				    bdheight = yMinMaxPos[1]-yMinMaxPos[0]+160,
				    tile_color = int((random.random()*(13-11)))+11,
				    note_font_size = 42)
	n['selected'].setValue(False)
	# revert to previous selection
	[i['selected'].setValue(True) for i in selNodes]
	return n

def nk_load_directory():
	"""
	Load directory
	"""
	SUPPORTED_FORMATS = "tif tiff tif16 tiff16 ftif ftiff tga targa rla xpm yuv avi cin dpx exr gif \
						hdr hdri jpg jpeg iff png png16 mov r3d raw psd sgi rgb rgba sgi16 pic".split(" ")
	loadDir = nukeOriginalGetFilename("Select a folder...")
	if os.path.isdir(loadDir):
		for f,ff,fff in os.walk(loadDir):
			clips = getClips(f)
			if clips:
				for clip in clips.keys():
					if os.path.splitext(clip)[-1][1:] in SUPPORTED_FORMATS:
						path = "%s%s" % (f,clip)
						path = toRelativePath(path,False) # Return only the path without the range range
						first = clips[clip][0]
						last =	clips[clip][1]
						nuke.createNode("Read",inpanel=False,knobs="""file "%s" first %i last %i before bounce after bounce""" % (path,first,last))

def nk_connect_to_switches():
	"""
	=> Switches
	Connect all selected nodes into all Switches
	"""
	sel = nuke.selectedNodes()
	switches = [n for n in sel if n.Class() == "Switch"]
	others = [n for n in sel if n not in switches]
	[s.setInput(s.inputs(),n) for s in switches for n in others]

def nk_randomize_selected_switches_timeOffsets(maxTime=300):
	"""
	Rand Switch + TimeOffset
	"""
	for n in nukeOriginalSelectedNodes("TimeOffset"):
		comp_dur = nuke.root().lastFrame()-nuke.root().firstFrame() # Duration of comp
		r = [nn for nn in allDependencies(n) if nn.Class() == "Read"]
		if r:
			clip_dur = r[0]['last'].value()-r[0]['first'].value()
			x = comp_dur - clip_dur
			if x == 0 or x > 0:
				maxTime = clip_dur*-1
			elif x < 0:
				maxTime = x
			else:
				maxTime = random.randrange(-1000,0)
		n['time_offset'].setValue(random.randrange(maxTime,0))

	for switch in nukeOriginalSelectedNodes("Switch"):
		max = switch.inputs()
		switch['which'].setValue(random.randrange(0,max))

def nk_new_channel_from_rgba():
	"""
	RGBA > Channels
	Copy RGBA channels from A input into *new channels* of B input. New channels
	are created globally and named after the node of A input. Useful when you
	need to merge multiple RGBA inputs into a multichannel EXR.
	"""
	for n in nuke.selectedNodes():
		cp = nuke.createNode("Copy",inpanel=False)
		nuke.inputs(cp,0)
		cp.setInput(1,n)
		chan = n.name()
		nuke.tcl("add_layer {%s %s.red %s.green %s.blue %s.alpha}" % (chan,chan,chan,chan,chan))
		cp['from0'].setValue("rgba.red")
		cp['from1'].setValue("rgba.green")
		cp['from2'].setValue("rgba.blue")
		cp['to0'].setValue("%s.red" % chan)
		cp['to1'].setValue("%s.green" % chan)
		cp['to2'].setValue("%s.blue" % chan)
		input_alpha = [c for c in nuke.channels(n) if c.split(".")[1] == "alpha"]
		if input_alpha:
			cp['from3'].setValue("rgba.alpha")
			cp['to3'].setValue("%s.alpha" % chan)

def nk_connect():
	"""
	Connect
	Connect nodes. First select source nodes in order by which
	they should be connected to target. Lastly, select target node.
	"""
	sel = nuke.selectedNodes()
	sources = sel[0:-1]
	target = sel[-1]
	for i,n in enumerate(sources):
		if target.inputs() <= i:
			target.setInput(i,n)
		else:
			target.setInput(target.inputs(),n)

def nk_color_with_tile():
	"""
	Color tiles the same
	"""
	nk_color_tiles(True)

def nk_color_tiles(src=False):
	"""
	Color tiles with swatch
	"""
	nodes = nuke.selectedNodes()
	color = nodes[0]['tile_color'].value() if src else nuke.getColor()
	dst = nodes[1:]	if src else nodes
	[n['tile_color'].setValue(color) for n in dst]
	
def nk_set_write_paths_ranges_from_reads():
	"""
	Read |=> Write
	"""
	for w in nuke.allNodes("Write"):
		r = [nn for nn in allDependencies(w) if nn.Class() == "Read"]
		if r and r[0].Class() == "Read":
			r = r[0]
			fn = nuke.filename(r)
			fn = os.path.split(fn)[-1].split(".")[0]
			w['file'].setValue("[getenv SHOTROOT]/%s.mov"%fn)
			range = [r['first'].value(),r['last'].value()]
			w['range'].setValue(range)

def nk_paste_to_selected_nodes():
	"""
	Paste into selected
	"""
	sel = nuke.selectedNodes()
	[n['selected'].setValue(False) for n in nuke.selectedNodes()]
	for n in sel:
		n['selected'].setValue(True)
		nuke.nodePaste(nukescripts.cut_paste_file())
		n['selected'].setValue(False)

def nk_expose_group_node():
	"""
	Open Group
	"""
	nuke.showDag(nuke.selectedNode())

def nk_deanimate_selected_node():
	"""
	Batch deanimate parameter
	"""
	parm = nuke.getInput("Parameter to deanimate?")
	[n[parm].clearAnimated() for n in nuke.selectedNodes()]
