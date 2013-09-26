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

#common stuff for the backends

from os import listdir,makedirs, remove
from os.path import join, exists, basename, isfile
from shutil import rmtree,copy
import re

_re_angled = re.compile("([^<]*)<([^>]*)")

#inspired by html.py but avoiding the dependency
def html_table(table_data,header=None,row_classes=None):
	"generates the content of a html table without the surrounding table tags"
	res = []
	if not header is None:
		row = " ".join(["<th>%s</th>" % str(head) for head in header])
		res.append("<tr>%s<tr>" % row)
	if row_classes is None:
		row_classes = [None]*len(table_data)
	for row_data,row_class in zip(table_data,row_classes):
		row = " ".join(["<td>%s</td>" % str(datum) for datum in row_data])
		if row_class is None:
			res.append("<tr>%s</tr>" % row)
		else:
			res.append("<tr class='%s'>%s</tr>" % (row_class,row))
	return "\n".join(res)


class BackendData:
	def __init__(self,name,path):
		self.repo_root = path
		self.backend_root = join(path,name)
		self.out_root = join(path,"output",name)


class BackendExporter:
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
