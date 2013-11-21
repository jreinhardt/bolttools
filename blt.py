#bolttools - a framework for creation of part libraries
#Copyright (C) 2013 Johannes Reinhardt <jreinhardt@ist-dein-freund.de>
#
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or any later version.
#
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#Lesser General Public License for more details.
#
#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import yaml
import os
from os.path import splitext, split, exists, join
# pylint: disable=W0622
from codecs import open

from errors import *
from common import YamlParser, BOLTSParameters, BOLTSNaming, RE_ANGLED

CURRENT_VERSION = 0.2

class BOLTSRepository:
	#order is important
	standard_bodies = ["DINENISO","DINEN","DINISO","DIN","EN","ISO","ANSI","ASME"]
	def __init__(self,path):
		self.path = path
		self.collections = []

		#check for conformity
		if not exists(path):
			e = MalformedRepositoryError("Repo directory does not exist")
			e.set_repo_path(path)
			raise e
		if not exists(join(path,"data")):
			e = MalformedRepositoryError("No data directory found")
			e.set_repo_path(path)
			raise e

		#load collection data
		for filename in os.listdir(join(path,"data")):
			if splitext(filename)[1] == ".blt":

				coll = list(yaml.load_all(open(filename,"r","utf8")))
				if len(coll) == 0:
					raise MalformedCollectionError(
							"No YAML document found in file %s" % filename)
				if len(coll) > 1:
					raise MalformedCollectionError(
							"More than one YAML document found in file %s" % filename)

				try:
					self.collections.append(BOLTSCollection(coll))
				except ParsingError as e:
					e.set_repo_path(path)
					e.set_collection(filename)
					raise e

				if not self.collections[-1].id == splitext(filename)[0]:
					raise MalformedCollectionError(
						"Collection ID is not identical with file name: %s" % filename)

				if self.collections[-1].id in ["common","gui","template"]:
					raise MalformedCollectionError(
							"Forbidden collection id: %s" % id)
				return id


		self.standardized = dict((body,[]) for body in self.standard_bodies)

		#find standard parts and their respective standard bodies
		for coll in self.collections:
			for cl in coll.classes:
				#order is important
				for body in self.standard_bodies:
					if cl.name.startswith(body):
						self.standardized[body].append(cl)
						cl.standard_body = body
						break

		#fill in obsolescence data
		for coll in self.collections:
			for cl in coll.classes:
				if cl.replaces is None:
					continue
				#order in standard_bodies is important
				for body in self.standard_bodies:
					if cl.replaces.startswith(body):
						idx = [c.name for c in self.standardized[body]].index(cl.replaces)
						self.standardized[body][idx].replacedby = cl.name
						break

class BOLTSCollection(YamlParser):
	def __init__(self,coll):
		YamlParser.__init__(self,coll,
			["id","author","license","blt-version"],
			["name","description"]
		)

		version = coll["collection"]["blt-version"]
		if version != CURRENT_VERSION:
			raise VersionError(version)

		#parse header
		header = coll["collection"]

		self.id = header["id"]

		self.name = ""
		if "name" in header:
			self.name = header["name"]

		self.description = ""
		if "description" in header:
			self.description = header["description"]

		self.authors = header["author"]
		if isinstance(self.authors,str):
			self.authors = [self.authors]

		self.author_names = []
		self.author_mails = []
		for author in self.authors:
			match = RE_ANGLED.match(author)
			self.author_names.append(match.group(1).strip())
			self.author_mails.append(match.group(2).strip())

		self.license = header["license"]
		match = RE_ANGLED.match(self.license)
		self.license_name = match.group(1).strip()
		self.license_url = match.group(2).strip()

		#parse classes
		if not isinstance(coll["classes"],list):
			raise MalformedCollectionError("No class in collection %s"% self.id)

		self.classes = []
		for cl in coll["classes"]:
			names = cl["id"]
			if "standard" in cl:
				names = cl["standard"]
			if isinstance(names,str):
				names = [names]
			for name in names:
				try:
					self.classes.append(BOLTSClass(cl,name))
				except ParsingError as e:
					e.set_class(name)
					raise

#In contrast to the class-element specified in the blt, this structure has only
#one name, a blt class element gets split into several BOLTSClasses during
#parsing
class BOLTSClass(YamlParser):
	def __init__(self,cl,name):
		YamlParser.__init__(self,cl,
			["naming","source","id"],
			["drawing","description","standard","status","replaces","parameters",
				"url","notes"]
		)

		self.id = cl["id"]

		try:
			self.naming = BOLTSNaming(cl["naming"])
		except ParsingError as e:
			e.set_class(self.id)
			raise e

		self.drawing = None
		if "drawing" in cl:
			self.drawing = cl["drawing"]

		self.description = ""
		if "description" in cl:
			self.description = cl["description"]

		self.standard_body = None
		self.standard = None
		self.body = None
		self.status = "active"
		self.replaces = None
		if "standard" in cl:
			self.standard = cl["standard"]
			if isinstance(self.standard,str):
				self.standard = [self.standard]
			if "status" in cl:
				self.status = cl["status"]
				if not self.status in ["active","withdrawn"]:
					raise ValueError
			if "replaces" in cl:
				self.replaces = cl["replaces"]
		#gets updated later by the repo
		self.replacedby = None

		try:
			if "parameters" in cl:
				self.parameters = BOLTSParameters(cl["parameters"])
			else:
				self.parameters = BOLTSParameters({})
		except ParsingError as e:
			e.set_class(self.id)
			raise e

		self.url = ""
		if "url" in cl:
			self.url = cl["url"]

		self.notes = ""
		if "notes" in cl:
			self.notes = cl["notes"]

		self.source = cl["source"]

		self.name = name
		self.openscadname = name.replace("-","_").replace(" ","_").replace(".","_")
