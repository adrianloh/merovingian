import re,os
from subprocess import Popen,PIPE
from couchdb import *
from hashlib import sha1
from random import randrange

dbname = "test_reactor"
db = Database("http://192.168.2.10/%s"%dbname)

for shot in range(1,randrange(5,10)):
	h = {}
	h['project'] = "IRONMAN10"
	h['type'] = 'shot'
	h['shot'] = '%05d' % shot
	for major in range(1,randrange(3,10)):
		h['versionMajor'] = major
		for minor in range(0,randrange(3,10)):
			h['versionMinor'] = minor
			db.create(h)