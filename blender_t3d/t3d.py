"""
Intermediate representations of T3D types.
"""
import math
from typing import Sequence, Type
from enum import Enum

def format_float(value:float)->str:
	""" Convert value to T3D signed floating point string. """
	return f"{value:+#013.06f}"

def format_vector(values:Sequence[float])->str:
	""" Apply format_float to vector. """
	return ",".join([format_float(x) for x in values])

def round_to_grid(value:float,grid_size:float)->float:
	""" Round value to closest grid point on a grid of size grid_size. """
	return round(value/grid_size)*grid_size

class Vec3(Sequence):
	""" 3D vector/point. """
	def __init__(self,*coords)->None:
		""" Construct from a list or three floating point values. """
		self.coords:list[float]=[0.]*3
		if len(coords)==1 and isinstance(coords[0],Sequence):
			coords=coords[0]
		for i,v in enumerate(coords[:3]):
			self.coords[i]=float(v)
	def __add__(self,other:'Vec3')->'Vec3':
		return self.__class__([self.coords[i]+other.coords[i] for i in range(3)])
	def __eq__(self,other)->bool:
		return self.coords==other.coords
	def __getitem__(self,index:int|slice)->float|list[float]:
		return self.coords[index]
	def __len__(self)->int:
		return len(self.coords)
	def __mul__(self,value:float)->'Vec3':
		return self.__class__([self.coords[i]*value for i in range(3)])
	def __str__(self)->str:
		return format_vector(self.coords)
	def __sub__(self,other:'Vec3')->'Vec3':
		return self.__class__([self.coords[i]-other.coords[i] for i in range(3)])
	def __truediv__(self,value:float)->'Vec3':
		return self.__class__([self.coords[i]/value for i in range(3)])
	def distance_to(self,other:'Vec3')->float:
		""" Distance to other Vertex. """
		return (other-self).length()
	def length(self)->float:
		""" Length of this vector. """
		return math.hypot(*self.coords)
	def normalized(self)->'Vec3':
		""" Direction. """
		return self/self.length()
	def snap(self,grid_distance:float)->None:
		""" Snap to grid in place. """
		for i in range(3):
			self.coords[i]=round_to_grid(self.coords[i],grid_distance)
	def _setx(self,value:float)->None:
		self.coords[0]=value
	def _sety(self,value:float)->None:
		self.coords[1]=value
	def _setz(self,value:float)->None:
		self.coords[2]=value
	x=property(lambda self:self.coords[0],_setx,None,"X")
	y=property(lambda self:self.coords[1],_sety,None,"Y")
	z=property(lambda self:self.coords[2],_setz,None,"Z")

class Vertex(Vec3):
	""" T3D Vertex. """
	def __str__(self)->str:
		return f"Vertex\t{format_vector(self.coords)}\n"

class Polygon:
	""" T3D Polygon. """
	def __init__(self,verts:list[Vertex]|None=None)->None:
		self.origin:tuple=(0,0,0)
		self.pan:tuple[int,int]=(0,0)
		self.u:tuple[float,float,float]=(1.,0.,0.)
		self.v:tuple[float,float,float]=(0.,0.,1.)
		self.vertices:list[Vertex]=verts if verts else []
		self.texture:str=""
		self.flags:int=0
	def __str__(self)->str:
		""" T3D format text block. """
		origin:str=f"Origin\t{format_vector(self.origin)}\n" if self.origin else ""
		vertices:str="".join([str(v) for v in self.vertices])
		uv:str=f"TextureU\t{format_vector(self.u)}\nTextureV\t{format_vector(self.v)}\n"
		texture:str=f" Texture={self.texture}" if self.texture else ""
		flags:str=f" Flags={self.flags}" if self.flags else ""
		pan:str=f"Pan U={self.pan[0]} V={self.pan[1]}\n" if self.pan!=(0,0) else ""
		polygon:str=f"Begin Polygon{texture}{flags}\n{origin}{pan}{uv}{vertices}End Polygon\n"
		return polygon
	def add_vertices(self,vert_list:Sequence[Sequence[float]])->None:
		""" Append more vertices. """
		self.vertices+=[Vertex(v) for v in vert_list]

class MyEnum(Enum):
	""" Takes int or a string equal to member name. """
	@classmethod
	def _missing_(cls,value:int|str):
		if isinstance(value,str):
			try:
				return cls(list(str(x) for x in cls).index(value.lower()))
			except ValueError:
				return tuple(cls)[0]
		return tuple(cls)[0]

	def __str__(self)->str:
		return self.name.lower()

class CsgOper(MyEnum):
	""" CsgOper enum. """
	NONE=0
	CSG_ADD=1
	CSG_SUBTRACT=2

class SheerAxis(MyEnum):
	""" SheerAxis enum. """
	NONE=0
	SHEER_XY=1
	SHEER_XZ=2
	SHEER_YX=3
	SHEER_YZ=4
	SHEER_ZX=5
	SHEER_ZY=6

class Brush:
	""" T3D Brush. """
	# pylint:disable=too-many-instance-attributes
	def __init__(self,poly_list:list[Polygon]|None=None,location:list|None=None)->None:
		# Actor name can be omitted, UED will create one.
		self.actor_name:str="ActorName"
		# Brush name (Begin Brush Name=...)
		self.brush_name:str="BrushName"
		self.csg:str="csg_add"
		self.mainscale:tuple=()
		self.mainscale_sheer:float=0.0
		self.mainscale_sheer_axis:str="SHEER_ZX"
		self.postscale:tuple=()
		self.postscale_sheer:float=0.0
		self.postscale_sheer_axis:str=self.mainscale_sheer_axis
		self.group:str=""
		self.polygons:list[Polygon]=poly_list if poly_list else []
		self.location:tuple=tuple(location) if location else ()
		self.rotation:tuple=()
		self.prepivot:tuple=()
		# Solidity and other things.
		self.polyflags:int=0

	@classmethod
	def from_dictionary(cls:Type["Brush"],dictionary:dict)->"Brush":
		""" Dictionary constructor. """
		b:Brush=cls()
		b.actor_name=dictionary.get("name",b.actor_name)
		b.brush_name=dictionary.get("brush_name",b.brush_name)
		b.csg=str(CsgOper(dictionary.get("csgoper",b.csg)))
		b.mainscale=dictionary.get("mainscale",{}).get("scale",b.mainscale)
		b.mainscale_sheer_axis=dictionary.get("mainscale",{}).get("sheeraxis",b.mainscale_sheer_axis)
		b.mainscale_sheer_axis=str(SheerAxis(b.mainscale_sheer_axis))
		b.postscale=dictionary.get("postscale",{}).get("scale",b.postscale)
		b.postscale_sheer_axis=dictionary.get("postscale",{}).get("sheeraxis",b.postscale_sheer_axis)
		b.postscale_sheer_axis=str(SheerAxis(b.postscale_sheer_axis))
		b.location=dictionary.get("location",b.location)
		b.rotation=dictionary.get("rotation",b.rotation)
		b.group=dictionary.get("group",b.group)
		b.prepivot=dictionary.get("prepivot",b.prepivot)
		b.polyflags=dictionary.get("polyflags",b.polyflags)

		for polydict in dictionary.get("polylist",()):
			poly:Polygon=Polygon([Vertex(v) for v in polydict.get("vertex",[])])
			poly.texture=polydict.get("texture",poly.texture)
			poly.flags=polydict.get("flags",poly.flags)
			#poly.normal=polydict.get("normal",poly.normal)
			poly.origin=polydict.get("origin",poly.origin)
			poly.u=polydict.get("textureu",poly.u)
			poly.v=polydict.get("texturev",poly.v)
			poly.pan=polydict.get("pan",poly.pan)
			b.polygons.append(poly)

		return b

	def __str__(self)->str:
		def coords_string(coords:tuple)->str:
			location_prefixes:tuple[str,str,str]=("X","Y","Z")
			return ",".join([x[0]+'='+str(x[1]) for x in zip(location_prefixes,coords)])
		def rotation_string(values:tuple)->str:
			prefixes:tuple[str,str,str]=("Roll","Pitch","Yaw")
			return ",".join([x[0]+'='+str(int(round(x[1]))) for x in zip(prefixes,values)])

		mainscale_txt:str=""
		if self.mainscale:
			mainscale_txt=(f"MainScale=(Scale=({coords_string(self.mainscale)}"
			f"),SheerRate={self.mainscale_sheer}"
			f",SheerAxis={self.mainscale_sheer_axis})\n")

		postscale_txt:str=""
		if self.postscale:
			postscale_txt=(f"PostScale=(Scale=({coords_string(self.postscale)}"
			f"),SheerRate={self.postscale_sheer}"
			f"),SheerAxis={self.postscale_sheer_axis})\n")

		location_txt:str=""
		if self.location and self.location!=(0.0,0.0,0.0):
			location_txt=f"Location=({coords_string(self.location)})\n"

		rotation_txt:str=""
		if self.rotation:
			rotation_txt=f"Rotation=({rotation_string(self.rotation)})\n"

		prepivot_txt:str=""
		if self.prepivot:
			prepivot_txt=f"PrePivot=({coords_string(self.prepivot)})\n"

		actor_name:str=f"Name={self.actor_name}" if self.actor_name else ""
		polygons:str="".join([str(p) for p in self.polygons])
		nl="\n"
		brush:str=f"""Begin Actor Class=Brush {actor_name}
CsgOper={self.csg}
{f"PolyFlags={self.polyflags}{nl}" if self.polyflags else ""}\
bSelected=True
{mainscale_txt}\
{postscale_txt}\
{f'Group="{self.group}"{nl}' if self.group else ""}\
{location_txt}\
{rotation_txt}\
Begin Brush Name={self.brush_name}
Begin PolyList
{polygons}End PolyList
End Brush
Brush=Model'MyLevel.{self.brush_name}'
{prepivot_txt}\
{actor_name}{nl if actor_name else ""}\
End Actor
"""
		return brush

	def get_pydata(self)->tuple:
		"""
		Return data that can be passed to bpy.types.Mesh.from_pydata().
		https://docs.blender.org/api/current/bpy.types.Mesh.html#bpy.types.Mesh.from_pydata
		"""
		verts:list[list[float]]=[v.coords for p in self.polygons for v in p.vertices]
		edges:list=[]
		faces:list[list[int]]=[]
		i=0
		for p in self.polygons:
			faces.append(list(range(i,i+len(p.vertices))))
			i+=len(p.vertices)
		return verts,edges,faces

	def snap(self,grid_distance:float=1.0)->None:
		""" Snap all this Brush's vertices to a grid. """
		for p in self.polygons:
			for v in p.vertices:
				v.snap(grid_distance)
		self.location=tuple(round_to_grid(v,grid_distance) for v in self.location)
