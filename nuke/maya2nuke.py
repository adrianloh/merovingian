import nuke
import re

#camera = nuke.createNode("Camera",knobs="rot_order XYZ",inpanel=False)
#scene = nuke.nodes.Scene()
#camera['translate'].setAnimated()
#camera['rotate'].setAnimated()
#ma = [l.strip()[:-1] for l in file("C:/Users/adrianloh/Desktop/test.ma").readlines()]
#c = {}
#c['x'] = 0
#c['y'] = 1
#c['z'] = 2

def maya2nuke_aperture(x,y):
	return x/(x/(y*25.4))

def getCurve(n):
	ff = "1"+re.findall("setAttr.+\]\" 1(.+)",ma[n])[0]
	return [float(x) for (i,x) in enumerate(ff.split(" ")) if i%2!=0]

def getLinesOfAnimation(word):
	#=> [(24, 'x'), (27, 'y'), (30, 'z')]
	return [(i+1,re.findall("%s(.)\""%word,l)[0].lower()) for (i,l) in enumerate(ma) if re.search("PFTrackCamera.+%s\w\""%word,l)]

def _animate(lines,parm):
	trans = {}
	for t in lines:
		(lineNumber,axis) = t
		trans[axis] = getCurve(lineNumber)
		for (frame,value) in enumerate(trans[axis]):
			frame = frame+1
			camera[parm].setValueAt(value,frame,c[axis])

def animateCamera(camera):
	rotations = getLinesOfAnimation("rot")
	translations = getLinesOfAnimation("trans")
	_animate(translations,"translate")
	_animate(rotations,"rotate")
	marker_lines = [i+2 for (i,l) in enumerate(ma) if re.search('Auto_\d+',l)]
	points = [nuke.createNode("Axis","translate {%s}" % " ".join(l.strip()[:-2].split(" ")[-3:]),inpanel=False) for (i,l) in enumerate(ma) if i in marker_lines]
	for point in points:
		scene.setInput(scene.inputs(),point)
	#	point.setInput(0,marker)
		scene.setInput(scene.inputs(),point)

#animateCamera(camera)

def animate(obj,parm,curve):
	"""
	Animate parameters in the form:
		nk.animate(node,parameter,[ [frame1,(x,y,z) , [frame2,(x,y,z), [frame3,(x,y,z) ])
	"""
	obj[parm].setAnimated()
	for animTuple in curve:
		[t,v] = animTuple
		try:
			for (i,vv) in enumerate(v):
				obj[parm].setValueAt(vv,t,i)
		except TypeError:
			obj[parm].setValueAt(v,t)

def group(nodes):
	[n['selected'].setValue(False) for n in nuke.allNodes()]
	[n['selected'].setValue(True) for n in nodes]
	nuke.makeGroup()

def nk_importPFTrackMaya():
	"""
	Import PFTrack Maya
	Import Maya .ma files exported from PFTrack. Will work only with
	scene files containing a single camera solve.
	"""
	path = nuke.getFilename("Select Maya Ascii file...","*.ma")
	ff = open(path).readlines()
	scene = nuke.nodes.Scene()
	input = nuke.nodes.Input()
	scene.setInput(scene.inputs(),input)

	#marker = nuke.createNode("Constant","color {0.8 1 0 0}",inpanel=False)
	marker_lines = [i+1 for (i,l) in enumerate(ff) if re.search('Auto_\d+',l)]
	#points = [nuke.createNode("Card","image_aspect false uniform_scale 0.03 translate {%s}" % " ".join(l.strip()[:-2].split(" ")[-3:]),inpanel=False) for (i,l) in enumerate(ff) if i in marker_lines]
	points = [nuke.createNode("Axis","translate {%s}" % " ".join(l.strip()[:-2].split(" ")[-3:]),inpanel=False) for (i,l) in enumerate(ff) if i in marker_lines]
	for point in points:
	#	point.setInput(0,marker)
		scene.setInput(scene.inputs(),point)

	#tt = [[float(x.split(" ")[1]) for x in re.findall("\]\" (.+)",line.strip())[0].split("  ")[:-1]] for line in ff if re.search("ktv",line)][1:]
	camera = nuke.createNode("Camera",knobs="rot_order XYZ",inpanel=False)
	#animate(camera,'focal',[[i,v] for i,v in enumerate(tt[0])])
	#animate(camera,'translate',[[i,v] for i,v in enumerate(zip(tt[1],tt[2],tt[3]))])
	#animate(camera,'rotate',[[i,v] for i,v in enumerate(zip(tt[4],tt[5],tt[6]))])

	def maya2nuke_aperture(x,y):
		return x/(x/(y*25.4))

	w = nuke.root()['format'].value().width()
	h = nuke.root()['format'].value().height()
	mh,mv = [line.strip()[:-1].split(" ")[-2:] for line in ff if re.search("cap",line)][0]
	camera['haperture'].setValue(maya2nuke_aperture(w,float(mh)))
	camera['vaperture'].setValue(maya2nuke_aperture(h,float(mv)))

	masterScene = nuke.nodes.Scene()
	render = nuke.nodes.ScanlineRender()
	render.setInput(2,camera)
	render.setInput(1,masterScene)

	points.append(scene)
	points.append(input)
	points.append(marker)
	group(points)
	[nuke.delete(n) for n in points]

nk_importPFTrackMaya()
















