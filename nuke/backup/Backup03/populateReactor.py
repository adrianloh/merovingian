from reactorDB import *
from random import *
from custom import *
import datetime
import base64
from couchdb import *



db = client.Database("http://127.0.0.1:8080/nuke_reactor")

import re

for i in range(1000):
    goof = nukescripts.misc.goofy_title().split(" ")[1:10]
    if len(goof) <= 5:
        continue
    else:
        try:
            _code = []
            caps = [n.capitalize() for n in goof if n.isalpha()]
            [_code.append(n[0]) for n in caps]
            _code = "".join(_code)
            _name = " ".join(caps)
            key = "proj_"+_code
            db[key] = dict(name=_name,code=_code,type="Project")
        except client.ResourceConflict:
            rev = db[key]["_rev"]
            db[key] = dict(_rev=rev,name=_name,code=_code,type="Project")

"""
c1 = base64.encodestring(open("comp1.rar","rb").read())
c2 = base64.encodestring(open("comp2.rar","rb").read())
c3 = base64.encodestring(open("comp3.rar","rb").read())

comps = [c1,c2,c3]

def getComp():
	return comps[randint(0,2)]

files = ["comp1.nk","comp2.nk","comp3.nk"]
compStatusItems = ["Setup","WIP","Review","Qrender","Rendering","Attention","Locked","Publish","Milestone","Incomplete","Abandoned"]

for shot in Shots.get():
		pid = shot.project_id
		sid = shot.id
		root = shot.shotroot
		versionCount = int(randint(1,50))
		for i in range(versionCount):
			c = Nuke_versions(	title="CompTitle_%s" % randstring(20),
							project_id=pid, shot_id=sid, shotroot=root,
							versionMajor=randint(1,10), versionMinor=randint(1,10),
							modified=datetime.datetime.now(),status=sample(compStatusItems,1)[0],
							script=getComp()
							)
			c.save()
"""