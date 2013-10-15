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

import string
from os import listdir, makedirs
from os.path import join, basename, splitext, exists
from shutil import copytree
# pylint: disable=W0622
from codecs import open

import freecad,openscad
from common import BackendData, BackendExporter, html_table
from license import check_license
from errors import *

def prop_row(props,prop,value):
	props.append("<tr><th><strong>%s:</strong></th><td>%s</td></tr>" %
		(prop,value))

class HTMLData(BackendData):
	def __init__(self,path):
		BackendData.__init__(self,"html",path)
		self.template_root = join(self.backend_root,"template")

class HTMLExporter(BackendExporter):
	def __init__(self):
		BackendExporter.__init__(self)
		self.templates = {}
	def write_output(self,repo):
		if repo.html is None:
			raise MalformedRepositoryError("Can not export: HTML Backend is not active")
		html = repo.html

		#load templates
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
		data = [ [
				"<a href='collections/%s.html'>%s</a>" % (coll.id,coll.name),
				coll.description
			] for coll in repo.collections]
		header = ["Name", "Description"]
		params["collections"] = html_table(data,header)
		data = [ [
				"<a href='bodies/%s.html'>%s</a>" % (body,body),
				"Standards issued by %s" % body
			] for body in repo.standard_bodies]
		header = ["Name", "Description"]
		params["bodies"] = html_table(data,header)

		fid = open(join(html.out_root,"index.html"),'w','utf8')
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
			for base in repo.freecad.getbase.values():
				for name in base.author_names:
					if not name in contributors_names:
						contributors_names.append(name)
		if not repo.openscad is None:
			for base in repo.openscad.getbase.values():
				for name in base.author_names:
					if not name in contributors_names:
						contributors_names.append(name)

		params = {}
		params["ncontributors"] = str(len(contributors_names))
		params["table"] = html_table([[name] for name in contributors_names])

		fid = open(join(html.out_root,"contributors.html"),'w','utf8')
		fid.write(self.templates["contributors"].substitute(params))
		fid.close()

		#write statistics
		params = {}
		params["classes"] = 0
		params["collections"] = 0
		params["standards"] = 0
		for coll in repo.collections:
			params["collections"] += 1
			for cl in coll.classes:
				params["classes"] += 1
				if not cl.standard is None:
					params["standards"] += len(cl.standard)
		params["bodies"] = len(repo.standard_bodies)
		params["contributors"] = len(contributors_names)
		for key in params:
			params[key] = str(params[key])

		fid = open(join(html.out_root,"statistics.html"),'w','utf8')
		fid.write(self.templates["statistics"].substitute(params))
		fid.close()

		#write base overview
		rows = []
		status = []
		classids = []
		for coll in repo.collections:
			for cl in coll.classes:
				if cl.id in classids:
					continue
				classids.append(cl.id)
				in_freecad = "Deactivated"
				if not repo.freecad is None:
					if cl.id in repo.freecad.getbase:
						in_freecad = "Yes"
						base = repo.freecad.getbase[cl.id]
						if isinstance(base,freecad.BaseFcstd):
							in_freecad = "Yes (Fcstd)"
						elif isinstance(base,freecad.BaseFunction):
							in_freecad = "Yes (function)"
				in_openscad = "Deactivated"
				if not repo.openscad is None:
					if cl.id in repo.openscad.getbase:
						in_openscad = "Yes"
						base = repo.openscad.getbase[cl.id]
						if isinstance(base,openscad.BaseModule):
							in_openscad = "Yes (module)"
						elif isinstance(base,openscad.BaseSTL):
							in_openscad = "Yes (stl)"
				if ((cl.id in repo.freecad.getbase) and
					(cl.id in repo.openscad.getbase)):
					continue
#					status.append("complete")
				elif ((not cl.id in repo.freecad.getbase) or 
					(not cl.id in repo.openscad.getbase)):
					status.append("partial")
					rows.append([cl.id, str(cl.standard), in_freecad, in_openscad])
				else:
					status.append("none")
					rows.append([cl.id, str(cl.standard), in_freecad, in_openscad])

		header = ["Class id","Standards","FreeCAD","OpenSCAD"]
		params["basetable"] = html_table(rows,header,status)

		#find missing images
		rows = []
		classids = []
		nosvg = {}
		for coll in repo.collections:
			for cl in coll.classes:
				if cl.drawing is None:
					if cl.id in classids:
						continue
					rows.append([cl.id, str(cl.standard), coll.id])
					classids.append(cl.id)
				else:
					svg_path = join("drawings","%s.svg" % splitext(cl.drawing)[0])
					if svg_path in nosvg:
						if not (cl.id, coll.id) in nosvg[svg_path]:
							nosvg[svg_path].append((cl.id, coll.id))
					elif not exists(join(html.repo_root,svg_path)):
						nosvg[svg_path] = [(cl.id, coll.id)]


		header = ["Class id","Standards","Collection id"]
		params["missingdrawings"] = html_table(rows,header)

		header = ["Drawing name","affected classes and collections"]
		rows_svg = [[k,v] for k,v in nosvg.iteritems()]
		params["missingdrawingssvg"] = html_table(rows_svg,header)

		#find unsupported licenses
		rows = []
		for coll in repo.collections:
			if not check_license(coll.license_name,coll.license_url):
				authors = ", ".join(['<a href="mailto:%s">%s</a>' % (a,m)
					for a,m in zip(coll.author_names,coll.author_mails)])
				rows.append(["Collection", coll.id, coll.license_name, coll.license_url, authors])

		bases = []
		if not repo.freecad is None:
			for base in repo.freecad.getbase.values():
				if base in bases:
					continue
				if not check_license(base.license_name,base.license_url):
					authors = ", ".join(['<a href="mailto:%s">%s</a>' % (a,m)
						for  a,m in zip(base.author_names,base.author_mails)])
					rows.append(["FreeCAD base", base.filename, base.license_name, base.license_url, authors])
					bases.append(base)

		bases = []
		if not repo.openscad is None:
			for base in repo.openscad.getbase.values():
				if base in bases:
					continue
				if not check_license(base.license_name,base.license_url):
					authors = ", ".join(['<a href="mailto:%s">%s</a>' % (a,m)
						for  a,m in zip(base.author_names,base.author_mails)])
					rows.append(["OpenSCAD base", base.filename, base.license_name, base.license_url, authors])
					bases.append(base)

		header = ["Type","Id/Filename","License name","License url", "Authors"]
		params["unsupportedlicenses"] = html_table(rows,header)




		fid = open(join(html.out_root,"tasks.html"),'w','utf8')
		fid.write(self.templates["tasks"].substitute(params))
		fid.close()


	def _write_collection(self,repo,coll):
		html = repo.html
		params = {}
		params["title"] = coll.name
		params["description"] = coll.description or "No description available"
		params["collectionid"] = coll.id

		author_links = ["<a href='mailto:%s'>%s</a>" % (m,n)
			for m,n in zip(coll.author_mails,coll.author_names)]
		params["author"] = " and <br>".join(author_links)

		params["license"] = "<a href='%s'>%s</a>" % \
			(coll.license_url,coll.license_name)

		data = [["<a href='../classes/%s.html'>%s</a>" % (cl.name,cl.name),
				cl.description,
				cl.status] for cl in coll.classes]
		header = ["Name", "Description", "Status"]
		row_classes = [cl.status for cl in coll.classes]
		params["classes"] = html_table(data,header,row_classes)

		fid = open(join(html.out_root,"collections","%s.html" % coll.id),'w','utf8')
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

		fid = open(join(html.out_root,"bodies","%s.html" % body),'w','utf8')
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
		prop_row(props,"License","<a href='%s'>%s</a>" %
			(coll.license_url,coll.license_name))
		prop_row(props,"Collection","<a href='../collections/%s.html'>%s</a>" %
				(coll.id,coll.name))

		if not cl.standard is None:
			identical = ", ".join(["<a href='%s.html'>%s</a>" % (id,id)
				for id in cl.standard if id != cl.name])
			if identical:
				prop_row(props,"Identical to",identical)

			prop_row(props,"Status",cl.status)
			prop_row(props,"Standard body","<a href='../bodies/%s.html'>%s</a>" %
				(cl.body,cl.body))
			if not cl.replaces is None:
				prop_row(props,"Replaces","<a href='%s.html'>%s</a>" %
					(cl.replaces,cl.replaces))

			if not cl.replacedby is None:
				prop_row(props,"Replaced by","<a href='%s.html'>%s</a>" %
					(cl.replacedby,cl.replacedby))

		prop_row(props,"Class ID",cl.id)

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
				except ValueError:
					keys = sorted(table.data.keys())
			data = [[key] + table.data[key] for key in keys]

			lengths = {"Length (mm)" : "mm", "Length (in)" : "in"}

			header = [str(table.index)]
			for p in table.columns:
				if cl.parameters.types[p] in lengths:
					header.append("%s (%s)" % (str(p), lengths[cl.parameters.types[p]]))
				else:
					header.append("%s" % str(p))

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
					prop_row(freecad_props,"Author","<a href='mailto:%s'>%s</a>" % 
						(mail,name))
				prop_row(freecad_props,"License","<a href='%s'>%s</a>" %
					(base.license_url,base.license_name))
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
					prop_row(openscad_props,"Author","<a href='mailto:%s'>%s</a>" %
						(mail,name))
				prop_row(openscad_props,"License","<a href='%s'>%s</a>" %
					(base.license_url,base.license_name))
				params["openscad"] = "\n".join(openscad_props)

				params["openscadincantation"] = "<h2>Incantations</h2>\n"
				params["openscadincantation"] += "{% highlight python %}\n"
				params["openscadincantation"] += "%s(%s);\n" % (cl.openscadname,
					openscad.get_signature(cl,cl.parameters.union(base.parameters)))
				params["openscadincantation"] += "dims = %s_dims(%s);\n" % (cl.openscadname,
					openscad.get_signature(cl,cl.parameters.union(base.parameters)))
				params["openscadincantation"] += "{% endhighlight %}\n"
			else:
				params["openscad"] = "<tr><td>Class not available in OpenSCAD</td></tr>\n"
				params["openscadincantation"] = ""


		fid = open(join(html.out_root,"classes","%s.html" % cl.name),'w','utf8')
		fid.write(self.templates["class"].substitute(params))
		fid.close()
#
