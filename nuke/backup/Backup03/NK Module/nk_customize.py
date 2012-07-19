
# -----------------------------------------------------
# This module contains primarily node customizations
# such as additional knobs that are added when 
# nodes are created, either to give nodes extra
# paramaters, or entirely new abilities, like batch file
# operations on Read and Write nodes
# ----------------------------------------------------

import nuke
import os
import re
from uuid import uuid4

# -------------- KNOB CREATION ---------------- #

def all_labels(n):
	""" Return all labels of knobs"""
	return [n[i].label() for i in n.knobs()]
	
def all_names(n):
	""" Return all variable names of knobs"""
	return [n[i].name() for i in n.knobs()]

def pyScriptKnob(label,script):
	K = nuke.PyScript_Knob(uuid4().hex,label)
	K.setValue(script)
	return K

def attach_file_operations(n):
	if 'fileops' not in all_names(n):
		n = draw_line(n,"File Operations")
		n.addKnob(nuke.PyScript_Knob("copyBtn","Copy","nuke.fileop(0)"))
		n.addKnob(nuke.PyScript_Knob("moveBtn","Move","nuke.fileop(1)"))
		n.addKnob(nuke.Boolean_Knob("update_source","update_source"))
		n['update_source'].setValue(1)
	return n

def attach_range(n):
	if 'range' not in all_names(n):
		k = nuke.UV_Knob("range","render range")
		n.addKnob(k)
		n["range"].setValue([nuke.root().firstFrame(),nuke.root().lastFrame()])
	return n

def attach_write_status(n):
	if 'status' not in all_names(n):
		n.addKnob(nuke.Enumeration_Knob("status","status",renderStatusItems))
	return n

def draw_line(n,label):
	n.addKnob(nuke.Text_Knob(uuid4().hex,label))
	return n

# ------------------- CALLBACKS ------------------- #
	
def customizeNodeOnUserCreate():
	n = nuke.thisNode()
	nClass = nuke.thisClass()

	if nClass == "Write":
		n['channels'].setValue("rgba")
		n = attach_range(n)
		n['label'].setValue("[knob range]")
		n['file'].setValue("[file dirname [value root.name]]/[knob name].%05d.exr")

	if nClass == "RotoPaint":
		n['output'].setValue("alpha")	

	if nClass == "Switch":
		n['label'].setValue("[knob which]")
		n['note_font'].setValue("Arial Bold")
		n['note_font_size'].setValue(20)

	if nClass == "Card2":
		n['label'].setValue("[knob translate.x] [knob translate.y] [knob translate.z]")

nuke.addOnUserCreate(customizeNodeOnUserCreate)
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		