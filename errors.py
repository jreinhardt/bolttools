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

def check_dict(array,spec):
	" Function to check a dictionary, as returned from YAML parsing, \
	against a specified schema "
	man = spec[0][:]
	opt = spec[1][:]
	for key in array.keys():
		if key in man:
			man.remove(key)
		elif key in opt:
			opt.remove(key)
		else:
			raise UnknownFieldError(key)
	if len(man) > 0:
		raise MissingFieldError(man)

class ParsingError(Exception):
	def __init__(self):
		Exception.__init__(self)
		self.trace_info = {}
		self.msg = "Something went wrong with parsing"
	def set_repo_path(self,path):
		self.trace_info["Repository path"] = path
	def set_collection(self,coll):
		self.trace_info["Collection"] = coll
	def set_class(self,cl):
		self.trace_info["Class"] = cl
	def set_base(self,base):
		self.trace_info["Base"] = base
	def __str__(self):
		trace = " ".join("%s: %s" % (k,str(v))
			for k,v in self.trace_info.iteritems())
		return "%s.  %s" % (self.msg, trace)

class VersionError(ParsingError):
	def __init__(self,version):
		ParsingError.__init__(self)
		self.msg = "Old or unknown version: %g" % version

class UnknownFieldError(ParsingError):
	def __init__(self,fieldname):
		ParsingError.__init__(self)
		self.msg = "Unknown Field: %s" % fieldname

class MissingFieldError(ParsingError):
	def __init__(self,fieldname):
		ParsingError.__init__(self)
		self.msg = "Missing Field: %s" % fieldname

class MalformedRepositoryError(ParsingError):
	def __init__(self,msg):
		ParsingError.__init__(self)
		self.msg = msg

class MalformedCollectionError(ParsingError):
	def __init__(self,msg):
		ParsingError.__init__(self)
		self.msg = msg

class MalformedBaseError(ParsingError):
	def __init__(self,msg):
		ParsingError.__init__(self)
		self.msg = msg

class UncommitedChangesError(Exception):
	def __str__(self):
		return "There are uncommited changes in the git repo"

class NonUniqueClassIdError(Exception):
	def __init__(self,id):
		self.id = id
	def __str__(self):
		return "Encountered more than one class with the same id: %s" % self.id
