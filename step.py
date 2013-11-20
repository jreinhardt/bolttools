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

from common import BackendData, BackendExporter

#TODO: cleaner
FREECADPATH = '/usr/lib/freecad/lib/' # path to your FreeCAD.so or FreeCAD.dll file
import sys
sys.path.append(FREECADPATH)
import FreeCAD
import Part

from os import listdir, makedirs, remove
from os.path import join, exists, basename, splitext, isfile

class STEPData(BackendData):
	def __init__(self,path):
		BackendData.__init__(self,"step",path)

class STEPExporter(BackendExporter):
	def __init__(self):
		BackendExporter.__init__(self)
	def write_output(self,repo,version=None):
		if repo.step is None:
			raise BackendNotAvailableError("downloads")
		if repo.freecad is None:
			raise BackendNotAvailableError("freecad")

		step = repo.step

		self.clear_output_dir(step)

		path = None
		for coll in repo.collections:
			if version is None:
				path = join(step.out_root,coll.id)
			else:
				path = join(step.out_root,"BOLTS_%s" % version,coll.id)
			makedirs(path)
			for cl in coll.classes:
				if not cl.id in repo.freecad.getbase:
					#TODO: openscad fallback
					continue
				base = repo.freecad.getbase[cl.id]

				#export all common parameter combinations
				for free in cl.parameters.common:
					params = cl.parameters.collect(zip(cl.parameters.free,free))

					params['standard'] = cl.name
					name = cl.naming.get_name(params)
					params['name'] = name
					filename = name.replace(" ","_").replace("/","-") + '.step'

					#insert part with parameter combination
					FreeCAD.newDocument()
					base.add_part(params,FreeCAD.ActiveDocument)

					#TODO: add version as metadata

					#export
					objs=[FreeCAD.ActiveDocument.ActiveObject]
					Part.export(objs,join(path,filename))
					del objs

					FreeCAD.closeDocument(FreeCAD.ActiveDocument.Name)
