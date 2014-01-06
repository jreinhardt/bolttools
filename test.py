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

import blt, openscad, freecad, drawings, solidworks
import yaml
import unittest
# pylint: disable=W0622
from codecs import open
from errors import *

def load_coll(filename):
	coll = list(yaml.load_all(open(filename,"r","utf8")))
	return coll[0]


class TestCollectionLoad(unittest.TestCase):
	def test_wrong_version(self):
		self.assertRaises(VersionError, lambda:
			blt.BOLTSCollection(load_coll("test/data/wrong_version.blt"))
		)

	def test_no_classes(self):
		self.assertRaises(MissingFieldError, lambda:
			blt.BOLTSCollection(load_coll("test/data/no_classes.blt"))
		)

	def test_empty_classes(self):
		self.assertRaises(MalformedCollectionError, lambda:
			blt.BOLTSCollection(load_coll("test/data/empty_classes.blt"))
		)

	def test_minimal_class(self):
		coll = blt.BOLTSCollection(load_coll("test/data/minimal_class.blt"))
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
		coll = blt.BOLTSCollection(load_coll("test/data/parameters.blt"))

		cl = coll.classes[0]
		self.assertEqual(cl.parameters.free,['key','l'])
		self.assertEqual(cl.parameters.free,['key','l'])
		self.assertEqual(type(cl.parameters.tables[0].data['M2.5'][2]),float)
		params = cl.parameters.collect({'key' : 'M2.5', 'l' : 37.4})
		self.assertEqual(params['s'],12.0)

	def test_naming_error(self):
		#wrong name for substitute field
		self.assertRaises(UnknownFieldError, lambda:
			blt.BOLTSCollection(load_coll("test/data/naming.blt"))
		)

	def test_type_error1(self):
		#additional parameter name in types
		self.assertRaises(UnknownParameterError, lambda:
			blt.BOLTSCollection(load_coll("test/data/type_error1.blt"))
		)
	def test_type_error2(self):
		#unknown type in types
		self.assertRaises(UnknownTypeError, lambda:
			blt.BOLTSCollection(load_coll("test/data/type_error2.blt"))
		)

	def test_table_error(self):
		#negative value for parameter of type length
		self.assertRaises(ValueError, lambda:
			blt.BOLTSCollection(load_coll("test/data/table_error1.blt"))
		)
		#negative value for parameter of type number
		blt.BOLTSCollection(load_coll("test/data/table_error2.blt"))

	def test_sort(self):
		blt.BOLTSCollection(load_coll("test/data/sort.blt"))

class TestBOLTSRepository(unittest.TestCase):
	def test_empty(self):
		self.assertRaises(MalformedCollectionError, lambda:
			blt.BOLTSRepository("test/empty")
		)

	def test_id_mismatch(self):
		self.assertRaises(MalformedCollectionError, lambda:
			blt.BOLTSRepository("test/id_mismatch")
		)

	def test_syntax(self):
		repo = blt.BOLTSRepository("test/syntax")
		self.assertEqual(len(repo.collections),1)

class TestOpenSCAD(unittest.TestCase):
	def test_syntax(self):
		os = openscad.OpenSCADData("test/syntax")
		self.assertTrue("hexscrew1" in os.getbase)
		self.assertTrue("cube1" in os.getbase)
		self.assertTrue("singlerowradialbearing" in os.getbase)

class TestFreeCAD(unittest.TestCase):
	def test_syntax(self):
		fc = freecad.FreeCADData("test/syntax")
		self.assertTrue("hexscrew1" in fc.getbase)
		self.assertFalse("lack1" in fc.getbase)
		self.assertTrue("singlerowradialbearing" in fc.getbase)

class TestDrawings(unittest.TestCase):
	def test_syntax(self):
		draw = drawings.DrawingsData("test/syntax")

class TestSolidWorks(unittest.TestCase):
	def test_syntax(self):
		draw = solidworks.SolidWorksData("test/syntax")

if __name__ == '__main__':
	unittest.main()


