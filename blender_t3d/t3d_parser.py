"""
Read T3D file.
"""
import re

try:
	import lark
except ModuleNotFoundError:
	raise ModuleNotFoundError("Dependency Lark is missing.") from None
from lark.visitors import Visitor

try:
	from . import t3d
except ImportError:
	import t3d

DEBUG=0
def _print(*_)->None:
	pass
if DEBUG:
	_print=print

def filter_brushes(text:str)->str:
	"""
	Filter T3D text to remove anything that's not a Brush block.
	Return the modified text.
	"""
	pattern:str=r"""(Begin Actor Class=Brush .*?End Actor)"""
	rx:re.Pattern=re.compile(pattern,re.S|re.I)
	matches:list=rx.findall(text)
	ret:str="\n".join(matches)
	return ret

class Vis(Visitor):
	""" Build brushes as it visits the tree."""
	# pylint: disable=C0116
	def __init__(self) -> None:
		super().__init__()
		# List of brushes created after full visit.
		self.brushes:list[t3d.Brush]=[]
		# Current brush info.
		self.context=[]

	def begin_actor(self,tree):
		actor_class=tree.children[0].value
		actor_name=tree.children[1].value
		self.context.append((actor_class,actor_name))
		if actor_class=="Brush":
			self.context.append(t3d.Brush(actor_name=actor_name))
			_print(f"<Create Actor Brush Name={actor_name}>")
		else:
			self.context.append(None)

	def block_end(self,tree):
		n=tree.children[0].children[0]
		if n=="Actor":
			if self.context and self.context[0][0]=="Brush":
				self.brushes.append(self.context[1])
				_print(f"<End Actor Brush {self.curr_brush_name()}>")
			self.context.clear()
		if n=="Polygon":
			_print(" <End Polygon>")

	def csg(self,tree):
		csg=tree.children[0]
		_print(f" <CSG={csg}>")
		self.curr_brush().csg=tree.children[0]

	def curr_brush(self)->t3d.Brush:
		return self.context[-1]
	def curr_brush_name(self)->str|None:
		return self.curr_brush().actor_name
	def curr_polygon(self)->t3d.Polygon:
		return self.curr_brush().polygons[-1]

	def group(self,tree):
		group_name=tree.children[0]
		self.curr_brush().group=group_name
		_print(f" <Group={group_name}>")

	def location(self,tree):
		if self.context[0][0]!="Brush":
			_print("Skip location for ",self.context)
			return
		curr_brush=self.curr_brush()
		coords="loc_x","loc_y","loc_z"
		x,y,z=[list(tree.find_data(c)) for c in coords]
		x,y,z=[float(c[0].children[0] if c else 0) for c in (x,y,z)]
		curr_brush.location=list((x,y,z))
		_print(f" <{self.curr_brush_name()} Location={curr_brush.location}>")

	def mainscale(self,tree):
		if not self.curr_brush():
			return
		if not tree.children:
			return
		coords="loc_x","loc_y","loc_z"
		x,y,z=[list(tree.find_data(c)) for c in coords]
		x,y,z=[float(c[0].children[0] if c else 1) for c in (x,y,z)]
		self.curr_brush().mainscale=x,y,z
		_print(f" <{self.curr_brush_name()} MainScale={x,y,z}>")

	def pan(self,tree):
		if not self.curr_brush():
			return
		u,v=[int(n.value) for n in tree.children]
		self.curr_polygon().pan=u,v
		_print(f"  <Pan U={u} V={v}>")

	def postscale(self,tree):
		if not self.curr_brush():
			return
		if not tree.children:
			return
		coords="loc_x","loc_y","loc_z"
		x,y,z=[list(tree.find_data(c)) for c in coords]
		x,y,z=[float(c[0].children[0] if c else 1) for c in (x,y,z)]
		self.curr_brush().postscale=x,y,z
		_print(f" <{self.curr_brush_name()} PostScale={x,y,z}>")

	def rotation(self,tree):
		if not self.curr_brush() or not tree.children:
			return
		coords="roll","pitch","yaw"
		x,y,z=[list(tree.find_data(c)) for c in coords]
		x,y,z=[float(c[0].children[0] if c else 0) for c in (x,y,z)]
		self.curr_brush().rotation=x,y,z
		_print(f" <{self.curr_brush_name()} Rotation={x,y,z}>")

	def tempscale(self,tree):
		if not self.curr_brush():
			return
		if not tree.children:
			return
		coords="loc_x","loc_y","loc_z"
		x,y,z=[list(tree.find_data(c)) for c in coords]
		x,y,z=[float(c[0].children[0] if c else 1) for c in (x,y,z)]
		self.curr_brush().tempscale=x,y,z
		_print(f" <{self.curr_brush_name()} TempScale={x,y,z}>")

	def prepivot(self,tree):
		if not self.curr_brush():
			return
		curr_brush=self.curr_brush()
		coords="loc_x","loc_y","loc_z"
		x,y,z=[list(tree.find_data(c)) for c in coords]
		x,y,z=[float(c[0].children[0] if c else 0) for c in (x,y,z)]
		curr_brush.prepivot=x,y,z
		_print(f" <{self.curr_brush_name()} PrePivot={x,y,z}>")

	def begin_polygon(self,tree):
		if not self.curr_brush():
			return
		texname=list(tree.find_data("texture_name"))
		flags=list(tree.find_data("flags"))
		flags=flags[0].children[0].value if flags else 0
		if texname:
			texname=texname[0].children[0]
		else:
			texname=""#None
		_print(f" <Polygon Texture={texname} Flags={flags}>")
		curr_brush=self.curr_brush()
		new_poly=t3d.Polygon()
		new_poly.texture=texname
		new_poly.flags=int(flags)
		curr_brush.polygons.append(new_poly)

	@staticmethod
	def _get_coords(tree)->list[float]:
		return [float(token.value) for token in tree.children]

	def textureu(self,tree):
		if not self.curr_brush():
			return
		x,y,z=Vis._get_coords(tree)
		_print(f"  <TextureU {x,y,z}>")
		self.curr_polygon().u=x,y,z

	def texturev(self,tree):
		if not self.curr_brush():
			return
		x,y,z=Vis._get_coords(tree)
		_print(f"  <TextureV {x,y,z}>")
		self.curr_polygon().v=x,y,z

	def vertex(self,tree):
		if not self.curr_brush():
			return
		x,y,z=[float(token.value) for token in tree.children]
		_print(f"  <Vertex {x,y,z}>")
		self.curr_polygon().add_vertices(((x,y,z),))

def t3d_open(path:str)->list[t3d.Brush]:
	"""
	Open and interpret T3D file.
	path: Path to the T3D file.
	Return a list of t3d.Brush objects.
	"""
	with open(path,encoding="utf-8") as f:
		text:str=f.read()
		text=filter_brushes(text)
		if len(text)==0:
			return []
	l=lark.Lark(r"""
start: block+
block: block_start content* block_end
block_start: begin_actor|begin_brush|begin_polygon|begin_other
block_end: "End"i block_name
block_name:WORD
?vertex:"Vertex" SIGNED_NUMBER "," SIGNED_NUMBER "," SIGNED_NUMBER
pan:"Pan" WS* "U=" SIGNED_NUMBER "V=" SIGNED_NUMBER
?textureu:"TextureU"i SIGNED_NUMBER "," SIGNED_NUMBER "," SIGNED_NUMBER
?texturev:"TextureV"i SIGNED_NUMBER "," SIGNED_NUMBER "," SIGNED_NUMBER
content:block|csg|group|mainscale|postscale|tempscale|location|rotation|prepivot|pan|textureu|texturev|vertex|IGNORED
begin_actor: "Begin Actor Class="resource_name "Name="resource_name
begin_brush: "Begin Brush Name=" WORD
begin_polygon: "Begin Polygon" ("Item="resource_name| "Texture="texture_name | "Flags="flags | "Link="NUMBER)*
begin_other.-1: "Begin" block_name
mainscale: "MainScale=(" scale? ","? "SheerAxis=SHEER_ZX"? ")"
postscale: "PostScale=(" scale? ","? "SheerAxis=SHEER_ZX"? ")"
tempscale: "TempScale=(" scale? ","? "SheerAxis=SHEER_ZX"? ")"
scale: "Scale=(" loc_x? ","? loc_y? ","? loc_z? ")"
location: "Location=(" loc_x? ","? loc_y? ","? loc_z? ")"
prepivot: "PrePivot=(" loc_x? ","? loc_y? ","? loc_z? ")"
csg:"CsgOper="resource_name
loc_x: "X=" SIGNED_NUMBER
loc_y: "Y=" SIGNED_NUMBER
loc_z: "Z=" SIGNED_NUMBER
rotation: "Rotation=(" (roll|pitch|yaw|",")* ")"
roll: "Roll=" SIGNED_NUMBER
pitch: "Pitch=" SIGNED_NUMBER
yaw: "Yaw=" SIGNED_NUMBER
group: "Group=" STRING
texture_name:resource_name
flags:SIGNED_NUMBER
?resource_name:/[\S.\d_]+/
IGNORED.-1:WS?/.+/ NL
%import common.NUMBER
%import common.SIGNED_NUMBER
%import common.DIGIT
%import common.WORD
%import common.ESCAPED_STRING -> STRING
%import common.WS
%import common.NEWLINE -> NL
%ignore WS
""",parser="lalr")
	try:
		tree:lark.ParseTree=l.parse(text)
	except lark.ParseError:
		print(f"Parse error: {path}")
		raise
	v=Vis()
	v.visit_topdown(tree)
	return v.brushes

def main()->None:
	""" Test. """
	samples_list:tuple[str,...]=(
		"test/samples/swat/fairfax-swat4.t3d",
		"test/samples/swat/map-ue2.t3d",
		"test/samples/swat/streets-raveshield.t3d",
		"test/samples/ut99/AS-Frigate.t3d",
		"test/samples/ut99/CTF-Coret.t3d",
		"test/samples/ut99/DM-Liandri.t3d",
		"test/samples/ut99/DOM-Cinder.t3d",
		"test/samples/ut99/sample.t3d",
		"test/samples/ut2004/AS-FallenCity.t3d",
		"test/samples/ut2004/BR-Anubis.t3d",
		"test/samples/ut2004/DM-Deck17.t3d",
		"test/samples/xiii/DM_Amos.t3d",
		"test/samples/xiii/xiii_cubes.t3d"
	)
	for s in samples_list:
		b:list[t3d.Brush]=t3d_open(s)
		print(f"Loaded {len(b)} brushes from {s}.")
		assert len(b)>0
	assert True

if __name__=="__main__":
	main()
