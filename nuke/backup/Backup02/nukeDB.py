import os
from autumn.db.connection import autumn_db
from autumn.model import Model
from autumn.db.relations import ForeignKey, OneToMany
from bottle import route, run

autumn_db.conn.connect('sqlite3',"%s/.nuke/nuke.sqlite" % os.environ["HOME"])

class Nuke_versions(Model):
	class Meta:
		table = 'nuke_versions'

class Projects(Model):
	class Meta:
		table = 'projects'

class Shots(Model):
	class Meta:
		table = 'shots'