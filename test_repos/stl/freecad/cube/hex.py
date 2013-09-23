from FreeCAD import Vector
from Part import makeBox
import Part
import math

def hex1(params,document):
	key = params['key']
	d1 = params['d1']
	k = params['k']
	s = params['s']
	h = params['h']
	if h is None:
		h = 0.
	l = params['l']
	name = params['name']

	part = document.addObject("Part::Feature",name)

	#head
	a = s/math.tan(math.pi/3.)
	box1 = makeBox(a,s,k)
	box1.translate(Vector(-0.5*a,-0.5*s,0))
	box1.rotate(Vector(0,0,0),Vector(0,0,1),30)
	box2 = makeBox(a,s,k)
	box2.translate(Vector(-0.5*a,-0.5*s,0))
	box2.rotate(Vector(0,0,0),Vector(0,0,1),150)
	box3 = makeBox(a,s,k)
	box3.translate(Vector(-0.5*a,-0.5*s,0))
	box3.rotate(Vector(0,0,0),Vector(0,0,1),270)
	head = box1.fuse(box2).fuse(box3)

	shaft_unthreaded = Part.makeCylinder(0.5*d1,h+k)
	shaft_threaded = Part.makeCylinder(0.5*d1,l-h)
	shaft_threaded.translate(Vector(0,0,h+k))
	part.Shape = head.fuse(shaft_unthreaded).fuse(shaft_threaded)

def hex2(params,document):
	key = params['key']
	d1 = params['d1']
	k = params['k']
	s = params['s']
	b1 = params['b1']
	b2 = params['b2']
	b3 = params['b3']
	l = params['l']
	b = b3;
	if l < 125:
		b = b1
	elif l < 200:
		b = b2
	name = params['name']

	part = document.addObject("Part::Feature",name)

	#head
	a = s/math.tan(math.pi/3.)
	box1 = makeBox(a,s,k)
	box1.translate(Vector(-0.5*a,-0.5*s,0))
	box1.rotate(Vector(0,0,0),Vector(0,0,1),30)
	box2 = makeBox(a,s,k)
	box2.translate(Vector(-0.5*a,-0.5*s,0))
	box2.rotate(Vector(0,0,0),Vector(0,0,1),150)
	box3 = makeBox(a,s,k)
	box3.translate(Vector(-0.5*a,-0.5*s,0))
	box3.rotate(Vector(0,0,0),Vector(0,0,1),270)
	head = box1.fuse(box2).fuse(box3)

	shaft_unthreaded = Part.makeCylinder(0.5*d1,l-b+k)
	shaft_threaded = Part.makeCylinder(0.5*d1,b)
	shaft_threaded.translate(Vector(0,0,l-b+k))
	part.Shape = head.fuse(shaft_unthreaded).fuse(shaft_threaded)

bases = {'hex1' : hex1,'hex2' : hex2}
