"""
Intermediate representations of T3D types.
"""
import math
from collections.abc import Sequence
#from typing import Iterable


def format_float(value:float)->str:
	""" Convert value to string in T3D floating point format. """
	return f"{value:+#013.06f}"

def format_vector(values:Sequence[float])->str:
	""" Apply format_float to vector. """
	return ",".join([format_float(x) for x in values])

def round_to_grid(value:float,grid_size:float)->float:
	""" Round value to closest grid point on a grid of size grid_size. """
	return round(value/grid_size)*grid_size

class Vertex:
	""" 3D vector/point. """
	def __init__(self,coords:Sequence[float]|None=None)->None:
		""" Construct from a list of three floating point values. """
		self.coords:list[float]=list(coords) if coords else [0.,0.,0.]
	def __add__(self,other:'Vertex')->'Vertex':
		return Vertex([self.coords[i]+other.coords[i] for i in range(3)])
	def __getitem__(self,index:int)->float:
		assert 0<=index<=2
		return self.coords[index]
	def __mul__(self,value:float)->'Vertex':
		return Vertex([self.coords[i]*value for i in range(3)])
	def __str__(self)->str:
		return f"Vertex\t{format_vector(self.coords)}\n"
	def __sub__(self,other:'Vertex')->'Vertex':
		return Vertex([self.coords[i]-other.coords[i] for i in range(3)])
	def __truediv__(self,value:float)->'Vertex':
		return Vertex([self.coords[i]/value for i in range(3)])
	def distance_to(self,other:'Vertex')->float:
		""" Distance to other Vertex. """
		return (other-self).length()
	def length(self)->float:
		""" Length of this vector. """
		return math.hypot(*self.coords)
	def normalized(self)->'Vertex':
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

class Polygon:
	""" T3D Polygon. """
	def __init__(self,verts:list[Vertex]|None=None,normal=None)->None:
		self.pan:tuple[int,int]|None=None
		self.u:tuple[float,float,float]=(1.,0.,0.)
		self.v:tuple[float,float,float]=(0.,0.,1.)
		self.vertices:list[Vertex]=verts if verts else []
		self.normal:None=normal # TODO: Not used.
		self.texture:str=""
		self.flags:int=0
	def __str__(self)->str:
		""" T3D format text block. """
		vertices:str="".join([str(v) for v in self.vertices])
		uv:str=f"TextureU\t{format_vector(self.u)}\nTextureV\t{format_vector(self.v)}\n"
		texture:str=f" Texture={self.texture}" if self.texture else ""
		flags:str=f" Flags={self.flags}" if self.flags else ""
		pan:str=f"Pan U={self.pan[0]} V={self.pan[1]}\n" if self.pan else ""
		polygon:str=f"Begin Polygon{texture}{flags}\n{pan}{uv}{vertices}End Polygon\n"
		return polygon
	def add_vertices(self,vert_list:Sequence[Sequence[float]])->None:
		""" Append more vertices. """
		self.vertices+=[Vertex(v) for v in vert_list]
	def length_xy(self)->float:
		# TODO: Not used.
		l=0
		for v in self.vertices:
			for v2 in self.vertices:
				v.z=0.0
				v2.z=0.0
				curr=v.distance_to(v2)
				l=curr if curr>l else l
		return l

class Brush:
	""" T3D Brush. """
	def __init__(self,poly_list:list[Polygon]|None=None,location:list|None=None,actor_name:str|None=None):
		# Actor name can be omitted, UED will create one.
		self.actor_name:str|None=actor_name
		self.brush_name:str="Brush"
		self.csg:str="CSG_Subtract"
		self.mainscale:tuple|None=None
		self.postscale:tuple|None=None
		self.tempscale:tuple|None=None # TODO: remove tempscale
		self.group:str|None=None
		self.polygons=poly_list if poly_list else []
		self.location=location
		self.rotation:tuple|None=None
		self.prepivot:tuple[float,float,float]|None=None
	def __str__(self)->str:
		polygons="".join([str(p) for p in self.polygons])
		location_prefixes=("X","Y","Z")

		if self.mainscale:
			mainscale_txt=f"MainScale=(Scale=("+ ",".join([x[0]+'='+str(x[1]) for x in zip(location_prefixes,self.mainscale)]) +"),SheerAxis=SHEER_ZX)\n"
		else:
			mainscale_txt=""

		if self.postscale:
			postscale_txt=f"PostScale=(Scale=("+ ",".join([x[0]+'='+str(x[1]) for x in zip(location_prefixes,self.postscale)]) +"),SheerAxis=SHEER_ZX)\n"
		else:
			postscale_txt=""

		if self.tempscale:
			tempscale_txt=f"TempScale=(Scale=("+ ",".join([x[0]+'='+str(x[1]) for x in zip(location_prefixes,self.tempscale)]) +"),SheerAxis=SHEER_ZX)\n"
		else:
			tempscale_txt=""

		if self.group:
			group_txt=f"Group={self.group}\n"
		else:
			group_txt=""
		if self.location:
			location_txt="Location=("+",".join([x[0]+'='+str(x[1]) for x in zip(location_prefixes,self.location)])+")\n"
		else:
			location_txt=""

		rotation_prefixes=("Roll","Pitch","Yaw")
		if self.rotation:
			rotation_txt="Rotation=("+ ",".join([x[0]+'='+str(int(round(x[1]))) for x in zip(rotation_prefixes,self.rotation)]) +")\n"
		else:
			rotation_txt=""

		if self.prepivot:
			prepivot_txt="PrePivot=("+",".join([x[0]+'='+str(x[1]) for x in zip(location_prefixes,self.prepivot)])+")\n"
		else:
			prepivot_txt=""
		actor_name=f"Name={self.actor_name}" if self.actor_name else ""
		nl="\n"
		brush=f"""Begin Actor Class=Brush {actor_name}
CsgOper={self.csg}
bSelected=True
{mainscale_txt}\
{postscale_txt}\
{tempscale_txt}\
{group_txt}\
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
			#for i in range(len(p.vertices)):
			#	p.vertices[i].snap(grid_distance)
			for v in p.vertices:
				v.snap(grid_distance)
		if self.location:
			self.location=[round_to_grid(v,grid_distance) for v in self.location]
