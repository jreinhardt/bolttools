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

from common import BackendData, BackendExporter, html_table
import freecad,openscad
from os import listdir,makedirs
import re
from os.path import join, exists, basename,splitext
from shutil import rmtree,copytree
import string

def prop_row(props,prop,value):
	props.append("<tr><th><strong>%s:</strong></th><td>%s</td></tr>" %(prop,value))

class HTMLData(BackendData):
	def __init__(self,path):
		BackendData.__init__(self,"html",path)
		self.template_root = join(self.backend_root,"template")

class HTMLExporter(BackendExporter):
	def write_output(self,repo):
		if repo.html is None:
			raise MalformedRepositoryError("Can not export: HTML Backend is not active")
		html = repo.html

		#load templates
		self.templates = {}
		for filename in listdir(html.template_root):
			name = splitext(basename(filename))[0]
			template_path = join(html.template_root,filename)
			self.templates[name] = string.Template(open(template_path).read())

		#clear output and copy files
		self.clear_output_dir(html)

		makedirs(join(html.out_root,"classes"))
		makedirs(join(html.out_root,"collections"))
		makedirs(join(html.out_root,"bodies"))

		#copy drawings
		copytree(join(repo.path,"drawings"),join(html.out_root,"drawings"))

		#write collections and parts
		for coll in repo.collections:
			self._write_collection(repo,coll)
			for cl in coll.classes:
				self._write_class(repo,coll,cl)

		for body in repo.standard_bodies:
			self._write_body(repo,body)

		#write index
		params = {}
		params["title"] = "BOLTS Index"
		data = [["<a href='collections/%s.html'>%s</a>" % (coll.id,coll.name), coll.description]
				for coll in repo.collections]
		header = ["Name", "Description"]
		params["collections"] = html_table(data,header)
		data = [["<a href='bodies/%s.html'>%s</a>" % (body,body), "Standards issued by %s" % body]
				for body in repo.standard_bodies]
		header = ["Name", "Description"]
		params["bodies"] = html_table(data,header)

		fid = open(join(html.out_root,"index.html"),'w')
		fid.write(self.templates["index"].substitute(params))
		fid.close()


		#write contributors list
		#collect contributors
		contributors_names = []
		for coll in repo.collections:
			for name in coll.author_names:
				if not name in contributors_names:
					contributors_names.append(name)
		if not repo.freecad is None:
			for id, base in repo.freecad.getbase.iteritems():
				for name in base.author_names:
					if not name in contributors_names:
						contributors_names.append(name)
		if not repo.openscad is None:
			for id, base in repo.openscad.getbase.iteritems():
				for name in base.author_names:
					if not name in contributors_names:
						contributors_names.append(name)

		params = {}
		params["ncontributors"] = str(len(contributors_names))
		params["table"] = html_table([[name] for name in contributors_names])

		fid = open(join(html.out_root,"contributors.html"),'w')
		fid.write(self.templates["contributors"].substitute(params))
		fid.close()


	def _write_collection(self,repo,coll):
		html = repo.html
		params = {}
		params["title"] = coll.name
		params["description"] = coll.description or "No description available"

		params["author"] = " and <br>".join(["<a href='mailto:%s'>%s</a>" % (m,n) \
				for m,n in zip(coll.author_mails,coll.author_names)])

		params["license"] = "<a href='%s'>%s</a>" % (coll.license_url,coll.license_name)

		data = [["<a href='../classes/%s.html'>%s</a>" % (cl.name,cl.name),
				cl.description,
				cl.status] for cl in coll.classes]
		header = ["Name", "Description", "Status"]
		row_classes = [cl.status for cl in coll.classes]
		params["classes"] = html_table(data,header,row_classes)

		fid = open(join(html.out_root,"collections","%s.html" % coll.id),'w')
		fid.write(self.templates["collection"].substitute(params))
		fid.close()

	def _write_body(self,repo,body):
		html = repo.html
		params = {}
		params["title"] = body
		params["description"] = "Standards issued by %s" % body

		data = [["<a href='../classes/%s.html'>%s</a>" % (cl.name,cl.name),
				cl.description,
				cl.status] for cl in repo.standardized[body]]
		header = ["Name", "Description", "Status"]
		row_classes = [cl.status for cl in repo.standardized[body]]
		params["classes"] = html_table(data,header,row_classes)

		fid = open(join(html.out_root,"bodies","%s.html" % body),'w')
		fid.write(self.templates["body"].substitute(params))
		fid.close()


	def _write_class(self,repo,coll,cl):
		html = repo.html
		params = {}

		params["title"] = cl.name
		params["description"] = cl.description or "No description available"
		params["drawing"] = cl.drawing or "no_drawing.png"

		props = []

		for mail,name in zip(coll.author_mails,coll.author_names):
			prop_row(props,"Author","<a href='mailto:%s'>%s</a>" % (mail,name))
		prop_row(props,"License","<a href='%s'>%s</a>" % (coll.license_url,coll.license_name))
		prop_row(props,"Collection","<a href='../collections/%s.html'>%s</a>" % (coll.id,coll.name))

		if not cl.standard is None:
			identical = ", ".join(["<a href='%s.html'>%s</a>" % (id,id) for id in cl.standard if id != cl.name])
			prop_row(props,"Identical to",identical)

			prop_row(props,"Status",cl.status)
			prop_row(props,"Standard body","<a href='../bodies/%s.html'>%s</a>" % (cl.body,cl.body))
			if not cl.replaces is None:
				prop_row(props,"Replaces","<a href='%s.html'>%s</a>" % (cl.replaces,cl.replaces))

			if not cl.replacedby is None:
				prop_row(props,"Replaced by","<a href='%s.html'>%s</a>" % (cl.replacedby,cl.replacedby))


		if cl.url:
			prop_row(props,"Url",cl.url)
		prop_row(props,"Source",cl.source)

		params["properties"] = "\n".join(props)

		#TODO: multiple tables properly
		params["dimensions"] = ""
		for table in cl.parameters.tables:
			keys = sorted(table.data.keys())
			#try to detect metric threads
			if "M" in [str(v)[0] for v in table.data.keys()]:
				try:
					keys = sorted(table.data.keys(),key=lambda x: float(x[1:]))
				except:
					keys = sorted(table.data.keys())
			data = [[key] + table.data[key] for key in keys]
			header = [str(p) for p in [table.index] + table.columns]
			params["dimensions"] += html_table(data,header)

		#freecad information
		if repo.freecad is None:
			params["freecad"] = "<tr><td>FreeCAD Backend is not available</td></tr>\n"
		else:
			if cl.id in repo.freecad.getbase:
				base = repo.freecad.getbase[cl.id]
				freecad_props = []
				if isinstance(base,freecad.BaseFunction):
					prop_row(freecad_props,"Type","Function")
				elif isinstance(base,freecad.BaseFcstd):
					prop_row(freecad_props,"Type","FCstd file")
				for mail,name in zip(base.author_mails,base.author_names):
					prop_row(freecad_props,"Author","<a href='mailto:%s'>%s</a>" % (mail,name))
				prop_row(freecad_props,"License","<a href='%s'>%s</a>" % (base.license_url,base.license_name))
				params["freecad"] = "\n".join(freecad_props)
			else:
				params["freecad"] = "<tr><td>Class is not available in FreeCAD</td></tr>\n"

		#openscad
		if repo.openscad is None:
			params["openscad"] = "<tr><td>OpenSCAD Backend is not available</td></tr>\n"
			params["openscadincantation"] = ""
		else:
			if cl.id in repo.openscad.getbase:
				base = repo.openscad.getbase[cl.id]
				openscad_props = []
				if isinstance(base,openscad.BaseModule):
					prop_row(openscad_props,"Type","Module")
				elif isinstance(base,openscad.BaseSTL):
					prop_row(openscad_props,"Type","STL file")
				for mail,name in zip(base.author_mails,base.author_names):
					prop_row(openscad_props,"Author","<a href='mailto:%s'>%s</a>" % (mail,name))
				prop_row(openscad_props,"License","<a href='%s'>%s</a>" % (base.license_url,base.license_name))
				params["openscad"] = "\n".join(openscad_props)

				params["openscadincantation"] = "<h2>Incantation</h2>\n"
				params["openscadincantation"] += "{% highlight python %}\n"
				params["openscadincantation"] += "%s;\n" % openscad.get_incantation(cl)
				params["openscadincantation"] += "{% endhighlight %}\n"
			else:
				params["openscad"] = "<tr><td>Class is not available in OpenSCAD</td></tr>\n"
				params["openscadincantation"] = ""


		fid = open(join(html.out_root,"classes","%s.html" % cl.name),'w')
		fid.write(self.templates["class"].substitute(params))
		fid.close()

#class TasksExporter:
#	def __init__(self):
#		self.tasks_template = string.Template(open("template/tasks.html").read())
#
#		#this is super-fragile base parsing using regular expressions
#		#better approach would be a proper parser for openscad and importing the module
#		#and checking the bases dict for freecad
#		self.scad_re = re.compile('module (?P<base>[a-z_0-9]*)\((?P<params>([a-zA-Z_0-9]*[, ]{0,2})*)\){')
#		self.python_re = re.compile('def (?P<base>[a-z_0-9]*)\(params, ?document\):')
#
#		#bases referenced in the blt files and their parameters
#		self.blt_bases = []
#		self.blt_params = []
#
#		#find all bases found in the scad files and their parameters
#		self.scad_bases = []
#		self.scad_params = []
#
#		#freecad bases, there we have no possibility of finding parameters
#		self.freecad_bases = []
#
#	def add_collection(self,filename):
#
#		coll = load_collection(filename)
#		for base in coll['scad']['base-functions']:
#			self.blt_bases.append(base)
#			self.blt_params.append(coll['scad']['base-functions'][base])
#
#	def finish(self):
#
#		#find scad bases
#		for filename  in listdir('scad'):
#			if filename in ['common.scad','conf.scad','sketch.scad']:
#				continue
#			for line in open('scad/' + filename):
#				match = self.scad_re.match(line)
#				if match is None:
#					continue
#				basename = match.group(1)
#				if basename.endswith('_sketch'):
#					continue
#				self.scad_bases.append(match.group('base'))
#				self.scad_params.append(match.group('params'))
#
#		#find freecad bases
#		for filename in listdir('freecad'):
#			for line in open('freecad/' + filename):
#				match = self.python_re.match(line)
#				if match is None:
#					continue
#				self.freecad_bases.append(match.group('base'))
#
#		#write html
#		content = {}
#		content['basetable'] = enclose(
#				[enclose(['base','OpenSCAD','FreeCAD'],'th')] +
#				[enclose([base,base in self.scad_bases, base in self.freecad_bases],'td') for base in self.blt_bases],'tr')
#		with open('html/tasks.html','w') as fid:
#			fid.write(self.tasks_template.substitute(content))
#
