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

import yaml
import importlib
from os import listdir
from os.path import join, exists, basename, splitext
from shutil import copy, copytree
# pylint: disable=W0622
from codecs import open

from common import BackendData, BackendExporter, BaseBase, BOLTSParameters
from errors import *

SPEC = {
	"file-function" : (["filename","author","license","type","functions"],[]),
	"file-fcstd" : (["filename","author","license","type","objects"],[]),
	"function" : (["name","classids"],["parameters"]),
	"object" : (["objectname","classids"],["proptoparam","parameters"]),
}

class FreeCADBase(BaseBase):
	def __init__(self,basefile,collname,backend_root):
		BaseBase.__init__(self,basefile,collname)
		self.filename = join(backend_root,collname,basefile["filename"])
		self.path = join(collname,self.filename)
	def add_part(self,params,doc):
		raise NotImplementedError

class BaseFunction(FreeCADBase):
	def __init__(self,function,basefile,collname,backend_root):
		self._check_conformity(function,basefile)
		FreeCADBase.__init__(self,basefile,collname,backend_root)
		self.name = function["name"]
		self.classids = function["classids"]
		self.module_name = splitext(basename(self.filename))[0]
		if "parameters" in function:
			self.parameters = BOLTSParameters(function["parameters"])
		else:
			self.parameters = BOLTSParameters({})
	def _check_conformity(self,function, basefile):
		# pylint: disable=R0201
		check_dict(function,SPEC["function"])
		check_dict(basefile,SPEC["file-function"])
	def add_part(self,params,doc):
		module = importlib.import_module("BOLTS.freecad.%s.%s" %
			(self.collection,self.module_name))
		module.__dict__[self.name](params,doc)

class BaseFcstd(FreeCADBase):
	def __init__(self,obj,basefile, collname,backend_root):
		self._check_conformity(obj,basefile)
		FreeCADBase.__init__(self,basefile,collname,backend_root)
		self.objectname = obj["objectname"]
		self.proptoparam = {self.objectname : {"Label" : "name"}}
		if "proptoparam" in obj:
			self.proptoparam = obj["proptoparam"]
		if "parameters" in obj:
			self.parameters = BOLTSParameters(obj["parameters"])
		else:
			self.parameters = BOLTSParameters({})

	def _check_conformity(self,obj,basefile):
		# pylint: disable=R0201
		check_dict(basefile,SPEC["file-fcstd"])
		check_dict(obj,SPEC["object"])

	def _recursive_copy(self,src_obj,dst_doc,srcdstmap):
		# pylint: disable=F0401
		import FreeCADGui, Part, Sketcher

		if src_obj.Name in srcdstmap:
			return srcdstmap[src_obj.Name]
		obj_copy = dst_doc.copyObject(src_obj)
		srcdstmap[src_obj.Name] = obj_copy
		for prop_name in src_obj.PropertiesList:
			prop = src_obj.getPropertyByName(prop_name)
			if isinstance(prop,tuple) or isinstance(prop,list):
				new_prop = []
				for p_item in prop:
					if isinstance(p_item,Part.Feature):
						new_prop.append(self._recursive_copy(p_item,dst_doc,srcdstmap))
					elif isinstance(p_item,Sketcher.Sketch):
						new_prop.append(dst_doc.copyObject(p_item))
					else:
						new_prop.append(p_item)
				if isinstance(prop,tuple):
					new_prop = tuple(new_prop)
				setattr(obj_copy,prop_name,new_prop)
			elif isinstance(prop,Sketcher.Sketch):
				setattr(obj_copy,prop_name,dst_doc.copyObject(prop))
			elif isinstance(prop,Part.Feature):
				setattr(obj_copy,prop_name,self._recursive_copy(prop,dst_doc,srcdstmap))
			else:
				setattr(obj_copy,prop_name,src_obj.getPropertyByName(prop_name))
		obj_copy.touch()
		gui_doc = FreeCADGui.getDocument(dst_doc.Name)
		gui_doc.getObject(obj_copy.Name).Visibility = False
		return obj_copy

	def add_part(self,params,doc):
		# pylint: disable=F0401
		import FreeCAD, FreeCADGui
		#copy part to doc
		src_doc = FreeCAD.openDocument(self.filename)
		src_obj = src_doc.getObject(self.objectname)
		if src_obj is None:
			raise MalformedBaseError("No object %s found" % self.objectname)
		#maps source name to destination object
		srcdstmap = {}
		dst_obj = self._recursive_copy(src_obj,doc,srcdstmap)

		#set parameters
		for obj_name,proptoparam in self.proptoparam.iteritems():
			for prop,param in proptoparam.iteritems():
				setattr(srcdstmap[obj_name],prop,params[param])

		#finish presentation
		dst_obj.touch()
		doc.recompute()
		FreeCADGui.getDocument(doc.Name).getObject(dst_obj.Name).Visibility = True
		FreeCAD.setActiveDocument(doc.Name)
		FreeCAD.closeDocument(src_doc.Name)


class FreeCADData(BackendData):
	def __init__(self,path):
		BackendData.__init__(self,"freecad",path)
		self.getbase = {}

		for coll in listdir(self.backend_root):
			basefilename = join(self.backend_root,coll,"%s.base" % coll)
			if not exists(basefilename):
				#skip directory that is no collection
				continue
			base_info =  list(yaml.load_all(open(basefilename,"r","utf8")))
			if len(base_info) != 1:
				raise MalformedCollectionError(
						"Not exactly one YAML document found in file %s" % basefilename)
			base_info = base_info[0]
			for basefile in base_info:
				if basefile["type"] == "function":
					basepath = join(self.backend_root,coll,"%s.py" % coll)
					if not exists(basepath):
						raise MalformedBaseError("Python module %s does not exist" % basepath)
					for func in basefile["functions"]:
						try:
							function = BaseFunction(func,basefile,coll,self.backend_root)
							for id in func["classids"]:
								self.getbase[id] = function
						except ParsingError as e:
							e.set_base(basefile["filename"])
							e.set_collection(coll)
							raise e
				elif basefile["type"] == "fcstd":
					basepath = join(self.backend_root,coll,basefile["filename"])
					if not exists(basepath):
						raise MalformedBaseError("Fcstd file %s does not exist" % basepath)
					for obj in basefile["objects"]:
						try:
							fcstd = BaseFcstd(obj,basefile,coll,self.backend_root)
							for id in obj["classids"]:
								self.getbase[id] = fcstd
						except ParsingError as e:
							e.set_base(basefile["filename"])
							e.set_collection(coll)
							raise e

class FreeCADExporter(BackendExporter):
	def __init__(self):
		BackendExporter.__init__(self)
	def write_output(self,repo):
		if repo.freecad is None:
			raise MalformedRepositoryError(
				"Can not export: FreeCAD Backend is not active")
		freecad = repo.freecad

		repo_path = freecad.repo_root
		out_path = freecad.out_root
		bolts_path = join(out_path,"BOLTS")

		self.clear_output_dir(freecad)

		#generate macro
		start_macro = open(join(out_path,"start_bolts.FCMacro"),"w")
		start_macro.write("import BOLTS\n")
		start_macro.write("BOLTS.widget.show()\n")
		start_macro.close()

		#copy files
		copytree(join(repo_path,"data"),join(bolts_path,"data"))
		copytree(join(repo_path,"bolttools"),join(bolts_path,"bolttools"))
		copytree(join(repo_path,"drawings"),join(bolts_path,"drawings"))
		copytree(join(repo_path,"freecad"),join(bolts_path,"freecad"))
		copy(join(repo_path,"__init__.py"),bolts_path)
