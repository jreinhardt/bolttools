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
from os import listdir,makedirs
from os.path import join, exists, basename
from shutil import copy
# pylint: disable=W0622
from codecs import open
import license
from datetime import datetime

from errors import *
from common import BackendData, BackendExporter, BaseBase, BOLTSParameters

SPEC = {
	"file-module" : (["filename","author","license","type","modules"],["source"]),
	"file-stl" : (["filename","author","license","type","classids"],["source"]),
	"module" : (["name", "arguments","classids"],["parameters"]),
}

def get_signature(cl,params):
	arg_strings = []
	for pname in params.free:
		if params.types[pname] in ["String","Table Index"]:
			arg_strings.append('%s="%s"' % (pname,params.defaults[pname]))
		else:
			arg_strings.append('%s=%s' % (pname,params.defaults[pname]))
	return ', '.join(arg_strings)

def get_incantation(cl,params):
	return '%s(%s)' % (cl.openscadname, get_signature(cl,params))

class OpenSCADBase(BaseBase):
	def __init__(self,basefile,collname):
		BaseBase.__init__(self,basefile,collname)
		self.filename = basefile["filename"]
		self.path = join(collname,self.filename)
	def get_copy_files(self):
		"Returns the path of the files to copy relative to the backend_root"
		raise NotImplementedError
	def get_include_files(self):
		"Returns the path of the files to copy relative to the base folder in output"
		raise NotImplementedError
	def get_incantation(self,args):
		"Return the incantation of the base that produces the geometry"
		raise NotImplementedError

class BaseModule(OpenSCADBase):
	def __init__(self,mod,basefile,collname):
		self._check_conformity(mod,basefile)
		OpenSCADBase.__init__(self,basefile,collname)
		self.name = mod["name"]
		self.arguments = mod["arguments"]
		self.classids = mod["classids"]

		if "parameters" in mod:
			self.parameters = BOLTSParameters(mod["parameters"])
		else:
			self.parameters = BOLTSParameters({})

	def _check_conformity(self,mod,basefile):
		# pylint: disable=R0201
		check_dict(mod,SPEC["module"])
		check_dict(basefile,SPEC["file-module"])
	def get_copy_files(self):
		return [self.path]
	def get_include_files(self):
		return [self.filename]
	def get_incantation(self,args):
		return "%s(%s)" % (self.name,", ".join(args[arg] for arg in self.arguments))


class BaseSTL(OpenSCADBase):
	def __init__(self,basefile,collname):
		self._check_conformity(basefile)
		OpenSCADBase.__init__(self,basefile,collname)
		self.classids = basefile["classids"]

		if "parameters" in basefile:
			self.parameters = BOLTSParameters(basefile["parameters"])
		else:
			self.parameters = BOLTSParameters({})
	def _check_conformity(self,basefile):
		# pylint: disable=R0201
		check_dict(basefile,SPEC["file-stl"])
	def get_copy_files(self):
		return [self.path]
	def get_include_files(self):
		return []
	def get_incantation(self,args):
		return 'import("%s")' % join("base",self.filename)


class OpenSCADData(BackendData):
	def __init__(self,path):
		BackendData.__init__(self,"openscad",path)
		#maps class id to base module
		self.getbase = {}

		for coll in listdir(self.backend_root):
			basefilename = join(self.backend_root,coll,"%s.base" % coll)
			if not exists(basefilename):
				#skip directory that is no collection
				continue
			base =  list(yaml.load_all(open(basefilename,"r","utf8")))
			if len(base) != 1:
				raise MalformedCollectionError(
						"No YAML document found in file %s" % basefilename)
			base = base[0]
			for basefile in base:
				if basefile["type"] == "module":
					for mod in basefile["modules"]:
						try:
							module = BaseModule(mod,basefile,coll)
							for id in module.classids:
								if id in self.getbase:
									raise MalformedRepositoryError("Non-unique base for classid: %s" % id)
								self.getbase[id] = module
						except ParsingError as e:
							e.set_base(basefile["filename"])
							raise e
				elif basefile["type"] == "stl":
					try:
						module = BaseSTL(basefile,coll)
						for id in module.classids:
							if id in self.getbase:
								raise NonUniqueClassIdError(id)
							self.getbase[id] = module
					except ParsingError as e:
						e.set_base(basefile["filename"])
						raise e

class OpenSCADExporter(BackendExporter):
	def __init__(self):
		BackendExporter.__init__(self)
	def write_output(self,repo,target_license,version="unstable"):
		if repo.openscad is None:
			raise MalformedRepositoryError(
				"Can not export, OpenSCAD Backend is not active")
		oscad = repo.openscad
		out_path = oscad.out_root

		self.clear_output_dir(oscad)
		#copy files
		bolts_fid = open(join(out_path,"BOLTS.scad"),"w","utf8")
		standard_fids = {}
		for std in repo.standard_bodies:
			standard_fids[std] = open(join(out_path,"BOLTS_%s.scad" % std),"w","utf8")

		makedirs(join(out_path,"tables"))

		#copy common files
		if not license.is_combinable_with("LGPL 2.1+",target_license):
			raise IncompatibleLicenseError("OpenSCAD common files are licensed under LGPL 2.1+, which is not compatible with %s" % target_license)
		makedirs(join(out_path,"common"))
		for filename in listdir(join(oscad.backend_root,"common")):
			if not filename.endswith(".scad"):
				continue
			copy(join(oscad.backend_root,"common",filename),
				join(out_path,"common",filename))
			bolts_fid.write("include <common/%s>\n" % filename)
			for std in standard_fids:
				standard_fids[std].write("include <common/%s>\n" % filename)

		#create version file
		version_fid = open(join(out_path,"common","version.scad"),"w","utf8")
		if version == "unstable":
			version_fid.write('function BOLTS_version() = "%s";\n' % version)
		else:
			major, minor = str(version).split('.')
			version_fid.write('function BOLTS_version() = [%s, %s, %s];\n' %
				 (major, minor, target_license))
		date = datetime.now()
		version_fid.write('function BOLTS_date() = [%d,%d,%d];\n' %
				(date.year, date.month, date.day))
		version_fid.write('function BOLTS_license() = "%s";\n' % target_license);
		version_fid.close()
		bolts_fid.write("include <common/version.scad>\n")
		for std in standard_fids:
			standard_fids[std].write("include <common/version.scad>\n")

		#copy base files
		copied = []
		makedirs(join(out_path,"base"))
		for id in oscad.getbase:
			base = oscad.getbase[id]
			if not license.is_combinable_with(base.license_name,target_license):
				continue
			for path in base.get_copy_files():
				if path in copied:
					continue
				copy(join(oscad.backend_root,path),join(out_path,"base",basename(path)))
				copied.append(path)

		#include files
		included = []
		for id in oscad.getbase:
			base = oscad.getbase[id]
			if not license.is_combinable_with(base.license_name,target_license):
				continue
			for path in base.get_include_files():
				if path in included:
					continue
				bolts_fid.write("include <base/%s>\n" % path)
				for std in standard_fids:
					standard_fids[std].write("include <base/%s>\n" % path)
				included.append(path)

		#write tables
		table_cache = []
		for collection in repo.collections:
			if not license.is_combinable_with(collection.license_name,target_license):
				continue
			for cl in collection.classes:
				if not cl.id in repo.openscad.getbase:
					continue
				if not cl.id in table_cache:
					base = oscad.getbase[cl.id]
					if not license.is_combinable_with(base.license_name,target_license):
						continue
					table_path = join("tables","%s_table.scad" % cl.id)
					table_filename = join(out_path,table_path)
					fid = open(table_filename,"w","utf8")
					self.write_table(fid,collection,cl)
					fid.close()
					table_cache.append(cl.id)

					bolts_fid.write("include <%s>\n" % table_path)
					for std in standard_fids:
						if cl in repo.standardized[std]:
							standard_fids[std].write("include <%s>\n" % table_path)
		bolts_fid.write("\n\n")

		#write stubs
		for collection in repo.collections:
			if not license.is_combinable_with(collection.license_name,target_license):
				continue
			for cl in collection.classes:
				if not cl.id in repo.openscad.getbase:
					continue
				base = oscad.getbase[cl.id]
				if not license.is_combinable_with(base.license_name,target_license):
					continue
				self.write_stub(repo,bolts_fid,cl)
				self.write_dim_accessor(repo,bolts_fid,cl)
				for std in standard_fids:
					if cl in repo.standardized[std]:
						self.write_stub(repo,standard_fids[std],cl)
						self.write_dim_accessor(repo,standard_fids[std],cl)
		bolts_fid.close()
		for std in standard_fids:
			standard_fids[std].close()

	def write_table(self,fid,collection,cl):
		for table,i in zip(cl.parameters.tables,range(len(cl.parameters.tables))):
			fid.write("/* Generated by BOLTS, do not modify */\n")
			fid.write("/* Copyright by: %s */\n" % ",".join(collection.authors))
			fid.write("/* %s */\n" % collection.license)

			data = table.data

			fid.write("function %s_table_%d(key) = \n" % (cl.id,i))
			fid.write("//%s\n" % ", ".join(table.columns))
			for k,values in data.iteritems():
				data = ["None" if v is None else v for v in values]
				fid.write('key == "%s" ? %s : \n' % (k,str(data).replace("'",'"')))
			fid.write('"Error";\n\n')

	def write_dim_accessor(self,repo,fid,cl):
		units = {"Length (mm)" : "mm", "Length (in)" : "in"}
		#collect textual parameter representations
		args = {}
		if not cl.standard is None:
			args['standard'] = '"%s"' % cl.name
		#class parameters
		params = cl.parameters.union(repo.openscad.getbase[cl.id].parameters)
		for pname in params.free:
			args[pname] = pname
		args.update(params.literal)
		for table,i in zip(params.tables,range(len(params.tables))):
			for pname,j in zip(table.columns,range(len(table.columns))):
				if params.types[pname] in units:
					unit = units[params.types[pname]]
					args[pname] = 'convert_to_default_unit(%s_table_%d(%s)[%d],"%s")' % (cl.id,i,table.index,j,unit)
				else:
					args[pname] = '%s_table_%d(%s)[%d]' % (cl.id,i,table.index,j)
		fid.write("function %s_dims(%s) = [\n\t" % (cl.openscadname, get_signature(cl,params)))
		fid.write(",\n\t".join('["%s", %s]' % (pname,args[pname]) for pname in params.parameters))
		fid.write("];\n\n")

	def write_stub(self,repo,fid,cl):
		units = {"Length (mm)" : "mm", "Length (in)" : "in"}
		#collect textual parameter representations
		args = {}
		if not cl.standard is None:
			args['standard'] = '"%s"' % cl.name
		#class parameters
		params = cl.parameters.union(repo.openscad.getbase[cl.id].parameters)
		for pname in params.free:
			args[pname] = pname
		args.update(params.literal)
		for table,i in zip(params.tables,range(len(params.tables))):
			for pname,j in zip(table.columns,range(len(table.columns))):
				if params.types[pname] in units:
					unit = units[params.types[pname]]
					args[pname] = 'convert_to_default_unit(measures_%d[%d],"%s")' % (i,j,unit)
				else:
					args[pname] = 'measures_%d[%d]' % (i,j)

		#incantation
		fid.write("module %s{\n" % get_incantation(cl,params))

		#warnings and type checks
		if cl.status == "withdrawn":
			fid.write("""\techo("Warning: The standard %s is withdrawn.
Although withdrawn standards are often still in use,
it might be better to use its successor %s instead");\n""" %
				(cl.name,cl.replacedby))
		for pname in params.free:
			fid.write('\tcheck_parameter_type("%s","%s",%s,"%s");\n' %
				(cl.name,pname,args[pname],params.types[pname]))

		fid.write("\n")
	

		#load table data
		for table,i in zip(cl.parameters.tables,range(len(cl.parameters.tables))):
			fid.write('\tmeasures_%d = %s_table_%d(%s);\n' %
				(i,cl.id,i,table.index))
			fid.write('\tif(measures_%d == "Error"){\n' % i)
			fid.write('\t\techo("TableLookUpError in %s, table %d");\n\t}\n' %
				(cl.name,i))

		fid.write('\tif(BOLTS_MODE == "bom"){\n')

		#write part name output for bom
		argc = 0
		fid.write('\t\techo(str(" "')
		for token in cl.naming.template.split():
			if token[0] == "%":
				fid.write(",")
				fid.write(args[cl.naming.substitute[argc]])
				fid.write('," "')
				argc += 1
			else:
				fid.write(',"%s"' % token)
				fid.write('," "')
		fid.write("));\n")
		#To avoid problems with missing top level object
		fid.write("\t\tcube();\n")

		fid.write("\t} else {\n")

		#module call
		fid.write('\t\t%s;\n\t}\n}\n\n' %
			repo.openscad.getbase[cl.id].get_incantation(args))

