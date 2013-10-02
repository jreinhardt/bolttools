# Copyright 2012-2013 Johannes Reinhardt <jreinhardt@ist-dein-freund.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

#common stuff

import re
from os import listdir,makedirs, remove
from os.path import join, exists, isfile
from shutil import rmtree
from copy import deepcopy

from errors import *

SPEC = {
	"naming" : (["template"],["substitute"]),
	"parameters" : ([],["literal","free","tables","types","defaults"]),
	"table" : (["index","columns","data"],[])
}

RE_ANGLED = re.compile("([^<]*)<([^>]*)")

#inspired by html.py but avoiding the dependency
def html_table(table_data,header=None,row_classes=None):
	"generates the content of a html table without the surrounding table tags"
	res = []
	if not header is None:
		row = " ".join([u"<th>%s</th>" % unicode(head) for head in header])
		res.append(u"<tr>%s<tr>" % row)
	if row_classes is None:
		row_classes = [None]*len(table_data)
	for row_data,row_class in zip(table_data,row_classes):
		row = " ".join([u"<td>%s</td>" % unicode(datum) for datum in row_data])
		if row_class is None:
			res.append(u"<tr>%s</tr>" % row)
		else:
			res.append(u"<tr class='%s'>%s</tr>" % (row_class,row))
	return u"\n".join(res)

class BOLTSParameters:
	type_defaults = {
		"Length (mm)" : 10,
		"Length (in)" : 1,
		"Number" : 1,
		"Bool" : False,
		"Table Index": '',
		"String" : ''
	}
	def __init__(self,param):
		self._check_conformity(param)
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
				raise ValueError("Unknown parameter in types: %s" % pname)
			if not tname in all_types:
				raise ValueError("Unknown type in types: %s" % tname)

		#fill in defaults for types
		for pname in self.parameters:
			if not pname in self.types:
				self.types[pname] = "Length (mm)"

		#check and normalize tables
		for table in self.tables:
			table._normalize_and_check_types(self.types)

		#default values for free parameters
		self.defaults = {pname : self.type_defaults[self.types[pname]]
			for pname in self.free}
		if "defaults" in param:
			for pname in param["defaults"]:
				if pname not in self.free:
					raise ValueError("Default value given for non-free parameter")
				self.defaults[pname] = param["defaults"][pname]

	def _check_conformity(self,param):
		# pylint: disable=R0201
		check_dict(param,SPEC["parameters"])

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

class BOLTSTable:
	def __init__(self,table):
		self._check_conformity(table)
		self.index = table["index"]
		self.columns = table["columns"]
		self.data = deepcopy(table["data"])

	def _check_conformity(self,table):
		# pylint: disable=R0201
		check_dict(table,SPEC["table"])

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

class BOLTSNaming:
	def __init__(self,name):
		self._check_conformity(name)
		self.template = name["template"]
		self.substitute = []
		if "substitute" in name:
			self.substitute = name["substitute"]

	def _check_conformity(self,name):
		# pylint: disable=R0201
		check_dict(name,SPEC["naming"])

	def get_name(self,params):
		return self.template % (params[s] for s in self.substitute)


class BackendData:
	def __init__(self,name,path):
		self.repo_root = path
		self.backend_root = join(path,name)
		self.out_root = join(path,"output",name)


class BackendExporter:
	def __init__(self):
		pass
	def clear_output_dir(self,backend_data):
		# pylint: disable=R0201
		if not exists(backend_data.out_root):
			makedirs(backend_data.out_root)
		for path in listdir(backend_data.out_root):
			full_path = join(backend_data.out_root,path)
			if isfile(full_path):
				remove(full_path)
			else:
				rmtree(full_path)


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
