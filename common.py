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
from os.path import join, exists, basename, isfile
from shutil import rmtree,copy
from copy import deepcopy

from errors import *

_specification = {
	"naming" : (["template"],["substitute"]),
	"parameters" : ([],["literal","free","tables","types","defaults"]),
	"table" : (["index","columns","data"],[])
}

_re_angled = re.compile("([^<]*)<([^>]*)")

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
				for t in param["tables"]:
					self.tables.append(BOLTSTable(t))
			else:
				self.tables.append(BOLTSTable(param["tables"]))

		self.types = {}
		if "types" in param:
			self.types = param["types"]

		self.parameters = []
		self.parameters += self.literal.keys()
		self.parameters += self.free
		for t in self.tables:
			self.parameters.append(t.index)
			self.parameters += t.columns
		#remove duplicates
		self.parameters = list(set(self.parameters))

		#check types
		all_types = ["Length (mm)", "Length (in)", "Number",
			"Bool", "Table Index", "String"]
		
		for k,t in self.types.iteritems():
			if not k in self.parameters:
				raise ValueError("Unknown parameter in types: %s" % k)
			if not t in all_types:
				raise ValueError("Unknown type in types: %s" % t)

		#fill in defaults for types
		for p in self.parameters:
			if not p in self.types:
				self.types[p] = "Length (mm)"

		#check and normalize tables
		for t in self.tables:
			t._normalize_and_check_types(self.types)

		#default values for free parameters
		self.defaults = {p:self.type_defaults[self.types[p]] for p in self.free}
		if "defaults" in param:
			for p in param["defaults"]:
				if p not in self.free:
					raise ValueError("Default value given for non-free parameter");
				self.defaults[p] = param["defaults"][p]

	def _check_conformity(self,param):
		spec = _specification
		check_dict(param,spec["parameters"])

	def collect(self,free):
		res = {}
		res.update(self.literal)
		res.update(free)
		for table in self.tables:
			res.update(dict(zip(table.columns,table.data[res[table.index]])))
		for p in self.parameters:
			if not p in res:
				raise KeyError("Parameter value not collected: %s" % p)
		return res

	def union(self,other):
		res = BOLTSParameters({})
		res.literal.update(self.literal)
		res.literal.update(other.literal)
		res.free = self.free + other.free
		res.tables = self.tables + other.tables
		res.parameters = list(set(self.parameters))
		for k,v in self.types.iteritems():
			res.types[k] = v
		for k,v in other.types.iteritems():
			res.types[k] = v
		for k,v in self.defaults.iteritems():
			res.defaults[k] = v
		for k,v in other.defaults.iteritems():
			res.defaults[k] = v
		return res

class BOLTSTable:
	def __init__(self,table):
		self._check_conformity(table)
		self.index = table["index"]
		self.columns = table["columns"]
		self.data = deepcopy(table["data"])

	def _check_conformity(self,table):
		spec = _specification
		check_dict(table,spec["table"])

	def _normalize_and_check_types(self,types):
		numbers = ["Length (mm)", "Length (in)", "Number"]
		positive = ["Length (mm)", "Length (in)"]
		rest = ["Bool", "Table Index", "String"]
		col_types = [types[col] for col in self.columns]
		idx = range(len(self.columns))
		for key in self.data:
			row = self.data[key]
			for i,t in zip(idx,col_types):
				if row[i] == "None":
					row[i] = None
				else:
					if t in numbers:
						row[i] = float(row[i])
					elif not t in rest:
						raise ValueError("Unknown Type in table: %s" % t)
					if t in positive and row[i] < 0:
						raise ValueError("Negative length in table: %f" % row[i])
					if t == "Bool":
						row[i] = bool(row[i])

class BOLTSNaming:
	def __init__(self,name):
		self._check_conformity(name)
		self.template = name["template"]
		self.substitute = []
		if "substitute" in name:
			self.substitute = name["substitute"]

	def _check_conformity(self,name):
		spec = _specification
		check_dict(name,spec["naming"])

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
			match = _re_angled.match(author)
			self.author_names.append(match.group(1).strip())
			self.author_mails.append(match.group(2).strip())

		self.license = basefile["license"]
		match = _re_angled.match(self.license)
		self.license_name = match.group(1).strip()
		self.license_url = match.group(2).strip()
