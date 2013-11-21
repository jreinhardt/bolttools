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

#common elements and baseclasses

import re
from os import listdir,makedirs, remove
from os.path import join, exists, isfile
from shutil import rmtree
from copy import deepcopy

from errors import *

RE_ANGLED = re.compile("([^<]*)<([^>]*)")

class YamlParser:
	def __init__(self, yaml_dict, element_name, mandatory_fields, optional_fields):
		#check dict from YAML parsing for correct fields
		for key in array.keys():
			if key in mandatory_fields:
				man.remove(key)
			elif key in optional_fields:
				opt.remove(key)
			else:
				raise UnknownFieldError(element_name,key)
		if len(man) > 0:
			raise MissingFieldError(element_name,man)

class BOLTSParameters(YamlParser):
	type_defaults = {
		"Length (mm)" : 10,
		"Length (in)" : 1,
		"Number" : 1,
		"Bool" : False,
		"Table Index": '',
		"String" : ''
	}
	def __init__(self,param):
		YamlParser.__init__(self,param,
			[],
			["literal","free","tables","types","defaults","common"]
		)

		self.literal = {}
		if "literal" in param:
			self.literal = param["literal"]

		self.free = []
		if "free" in param:
			self.free = param["free"]

		self.tables = []
		if "tables" in param:
			if isinstance(param["tables"],list):
				for table in param["tables"]:
					self.tables.append(BOLTSTable(table))
			else:
				self.tables.append(BOLTSTable(param["tables"]))

		self.types = {}
		if "types" in param:
			self.types = param["types"]

		self.parameters = []
		self.parameters += self.literal.keys()
		self.parameters += self.free
		for table in self.tables:
			self.parameters.append(table.index)
			self.parameters += table.columns
		#remove duplicates
		self.parameters = list(set(self.parameters))

		#check types
		all_types = ["Length (mm)", "Length (in)", "Number",
			"Bool", "Table Index", "String"]
		
		for pname,tname in self.types.iteritems():
			if not pname in self.parameters:
				raise UnknownParameterError(pname)
			if not tname in all_types:
				raise UnknownTypeError(tname)

		#fill in defaults for types
		for pname in self.parameters:
			if not pname in self.types:
				self.types[pname] = "Length (mm)"

		#check and normalize tables
		for table in self.tables:
			table._normalize_and_check_types(self.types)

		#default values for free parameters
		self.defaults = dict((pname,self.type_defaults[self.types[pname]])
			for pname in self.free)
		if "defaults" in param:
			for pname in param["defaults"]:
				if pname not in self.free:
					raise NonFreeDefaultError(pname)
				self.defaults[pname] = param["defaults"][pname]

		#common parameter combinations
		discrete_types = ["Bool", "Table Index"]
		self.common = []
		if "common" in param:
			for tup in param["common"]:
				self._populate_common(tup,[],0)
		else:
			discrete = True
			for pname in self.free:
				if not self.types[pname] in discrete_types:
					discrete = False
					break
			if discrete and len(self.free) > 0:
				self._populate_common([":" for i in range(len(self.free))],[],0)

	def _populate_common(self, tup, values, idx):
		if idx == len(self.free):
			self.common.append(values)
		else:
			if tup[idx] == ":":
				if self.types[self.free[idx]] == "Bool":
					for v in [True, False]:
						self._populate_common(tup,values + [v], idx+1)
				elif self.types[self.free[idx]] == "Table Index":
					for table in self.tables:
						if self.free[idx] == table.index:
							for v in table.data:
								self._populate_common(tup,values + [v], idx+1)
							break
				else:
					print "That should not happen"
			else:
				for v in tup[idx]:
					self._populate_common(tup,values + [v], idx+1)

	def collect(self,free):
		res = {}
		res.update(self.literal)
		res.update(free)
		for table in self.tables:
			res.update(dict(zip(table.columns,table.data[res[table.index]])))
		for pname in self.parameters:
			if not pname in res:
				raise KeyError("Parameter value not collected: %s" % pname)
		return res

	def union(self,other):
		res = BOLTSParameters({})
		res.literal.update(self.literal)
		res.literal.update(other.literal)
		res.free = self.free + other.free
		res.tables = self.tables + other.tables
		res.parameters = list(set(self.parameters))
		for pname,tname in self.types.iteritems():
			res.types[pname] = tname
		for pname,tname in other.types.iteritems():
			res.types[pname] = tname
		for pname,tname in self.defaults.iteritems():
			res.defaults[pname] = tname
		for pname,tname in other.defaults.iteritems():
			res.defaults[pname] = tname
		return res

class BOLTSTable(YamlParser):
	def __init__(self,table):
		self.YamlParser.__init__(self,table,
			["index","columns","data"],
			[]
		)

		self.index = table["index"]
		self.columns = table["columns"]
		self.data = deepcopy(table["data"])

	def _normalize_and_check_types(self,types):
		numbers = ["Length (mm)", "Length (in)", "Number"]
		positive = ["Length (mm)", "Length (in)"]
		rest = ["Bool", "Table Index", "String"]
		col_types = [types[col] for col in self.columns]
		idx = range(len(self.columns))
		for key in self.data:
			row = self.data[key]
			for i,tname in zip(idx,col_types):
				if row[i] == "None":
					row[i] = None
				else:
					if tname in numbers:
						row[i] = float(row[i])
					elif not tname in rest:
						raise ValueError("Unknown Type in table: %s" % tname)
					if tname in positive and row[i] < 0:
						raise ValueError("Negative length in table: %f" % row[i])
					if tname == "Bool":
						row[i] = bool(row[i])

class BOLTSNaming(YamlParser):
	def __init__(self,name):
		YamlParser.__init__(self,name,
			["template"],
			["substitute"]
		)

		self.template = name["template"]
		self.substitute = []
		if "substitute" in name:
			self.substitute = name["substitute"]

	def get_name(self,params):
		return self.template % tuple(params[s] for s in self.substitute)


class BackendData:
	def __init__(self,name,path):
		self.repo_root = path
		self.backend_root = join(path,name)
		self.out_root = join(path,"output",name)

class BaseBase:
	def __init__(self,basefile,collname):
		self.collection = collname

		self.authors = basefile["author"]
		if isinstance(self.authors,str):
			self.authors = [self.authors]
		self.author_names = []
		self.author_mails = []
		for author in self.authors:
			match = RE_ANGLED.match(author)
			self.author_names.append(match.group(1).strip())
			self.author_mails.append(match.group(2).strip())

		self.license = basefile["license"]
		match = RE_ANGLED.match(self.license)
		self.license_name = match.group(1).strip()
		self.license_url = match.group(2).strip()

		self.source = ""
		if "source" in basefile:
			self.source = basefile["source"]
