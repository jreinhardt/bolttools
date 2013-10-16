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

import blt_parser
import openscad, freecad, html
import unittest
from errors import *

class TestCollectionLoad(unittest.TestCase):

	def test_empty(self):
		self.assertRaises(MalformedCollectionError, lambda:
			blt_parser.BOLTSCollection("test_collections/empty.blt")
		)

	def test_wrong_version(self):
		self.assertRaises(VersionError, lambda:
			blt_parser.BOLTSCollection("test_collections/wrong_version.blt")
		)

	def test_no_classes(self):
		self.assertRaises(MissingFieldError, lambda:
			blt_parser.BOLTSCollection("test_collections/no_classes.blt")
		)

	def test_empty_classes(self):
		self.assertRaises(MalformedCollectionError, lambda:
			blt_parser.BOLTSCollection("test_collections/empty_classes.blt")
		)

	def test_minimal_class(self):
		coll = blt_parser.BOLTSCollection("test_collections/minimal_class.blt")
		self.assertEqual(coll.author_names,["Johannes Reinhardt"])
		self.assertEqual(coll.author_mails,["jreinhardt@ist-dein-freund.de"])
		self.assertEqual(coll.license_name,"LGPL 2.1+")
		self.assertEqual(coll.license_url,
			"http://www.gnu.org/licenses/old-licenses/lgpl-2.1")

		cl = coll.classes[0]
		self.assertEqual(cl.naming.template,"Partname")
		self.assertEqual(cl.source,"Invented for testpurposes")
		self.assertEqual(cl.parameters.free,[])

	def test_parameters(self):
		coll = blt_parser.BOLTSCollection("test_collections/parameters.blt")

		cl = coll.classes[0]
		self.assertEqual(cl.parameters.free,['key','l'])
		self.assertEqual(cl.parameters.free,['key','l'])
		self.assertEqual(type(cl.parameters.tables[0].data['M2.5'][2]),float)
		params = cl.parameters.collect({'key' : 'M2.5', 'l' : 37.4})
		self.assertEqual(params['s'],12.0)

	def test_naming_error(self):
		#wrong name for substitute field
		self.assertRaises(UnknownFieldError, lambda:
			blt_parser.BOLTSCollection("test_collections/naming.blt")
		)

	def test_type_error1(self):
		#additional parameter name in types
		self.assertRaises(ValueError, lambda:
			blt_parser.BOLTSCollection("test_collections/type_error1.blt")
		)
	def test_type_error2(self):
		#unknown type in types
		self.assertRaises(ValueError, lambda:
			blt_parser.BOLTSCollection("test_collections/type_error2.blt")
		)

	def test_table_error(self):
		#negative value for parameter of type length
		self.assertRaises(ValueError, lambda:
			blt_parser.BOLTSCollection("test_collections/table_error1.blt")
		)
		#negative value for parameter of type number
		blt_parser.BOLTSCollection("test_collections/table_error2.blt")

class TestRepository(unittest.TestCase):
	def test_load(self):
		repo = blt_parser.BOLTSRepository("test_repo")

	def test_openscad(self):
		repo = blt_parser.BOLTSRepository("test_repo")
		openscad.OpenSCADExporter().write_output(repo,"LGPL 2.1+")

	def test_freecad(self):
		repo = blt_parser.BOLTSRepository("test_repo")
		freecad.FreeCADExporter().write_output(repo,"LGPL 2.1+")

	def test_html(self):
		repo = blt_parser.BOLTSRepository("test_repo")
		html.HTMLExporter().write_output(repo)

if __name__ == '__main__':
	unittest.main()


