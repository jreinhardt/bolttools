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
from os import listdir
from os.path import join, exists, basename, splitext
# pylint: disable=W0622
from codecs import open

from common import BackendData, BackendExporter, html_table
from license import LICENSES_SHORT
from errors import *

class DownloadsData(BackendData):
	def __init__(self,path):
		BackendData.__init__(self,"downloads",path)

class DownloadsExporter(BackendExporter):
	def __init__(self):
		BackendExporter.__init__(self)

	def write_output(self,repo):
		# pylint: disable=R0201
		if repo.downloads is None:
			raise BackendNotAvailableError("downloads")
		downloads = repo.downloads
		out_path = downloads.out_root

		backends = ["freecad","openscad"]

		#find most current release
		self.release = {}
		self.development = {}

		for backend in backends:
			self.release[backend] = {}
			self.development[backend] = {}
			for filename in listdir(join(out_path,"downloads",backend)):
				basename,ext = splitext(filename)
				if ext == ".gz":
					ext = ".tar.gz"
					basename = splitext(basename)[0]
				parts = basename.split("_")
				version_string = parts[2]

				#some old development snapshots have no license in filename
				license = "none"
				if len(parts) > 3:
					license = parts[3]

				kind = self.development[backend]
				version = None
				try:
					version = int(version_string)
				except ValueError:
					version = float(version_string)
					kind = self.release[backend]

				if not license in kind:
					kind[license] = {}
				if not ext in kind[license]:
					kind[license][ext] = (version, join(backend,filename))
				elif version > kind[license][ext][0]:
					kind[license][ext] = (version, join(backend,filename))

		params = {}

		for kind,kind_name in zip([self.release, self.development],
			["release","development"]):
			for backend in backends:
				rows = []
				for license in ["lgpl2.1+","gpl3"]:
					if license in kind[backend]:
						rows.append([LICENSES_SHORT[license],
							'<a href="downloads/%s">.tar.gz</a>' % (kind[backend][license][".tar.gz"][1]),
							'<a href="downloads/%s">.zip</a>' % (kind[backend][license][".zip"][1])])
				if len(rows) == 0:
					rows = [["No %s distribution available" % kind_name]]
				params["%s%s" % (backend, kind_name)] = html_table(rows)

		#generate html page
		template_name = join(downloads.backend_root,"template","downloads.html")
		template = string.Template(open(template_name).read())
		fid = open(join(out_path,"downloads.html"),"w","utf8")
		fid.write(template.substitute(params))
		fid.close()
#
##TODO:
##		I do not like the fact that I am shipping unprocessed and unstyled html
##		here, but I do not see a nice workflow for processing and styling, so I
##		don't
##		if not repo.html is None:
##			base_name = join(out_path,downloads.template % "html")
##			root_dir = join(repo.path,"output","html")
##			print make_archive(base_name,"gztar",root_dir)
##			print make_archive(base_name,"zip",root_dir)
