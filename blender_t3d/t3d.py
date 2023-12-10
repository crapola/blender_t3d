import math

def format_float(value:float)->str:
	return f"{value:+#013.06f}"

def format_vector(values:tuple)->str:
	return ",".join([format_float(x) for x in values])

def round_to_grid(value:float,grid:float)->float:
	return round(value/grid)*grid

class Vertex:
	def __init__(self,coords:list[float]=None):
		self.coords=list(coords) if coords else [0.,0.,0.]
	def __add__(self,other:'Vertex'):
		return Vertex([self.coords[i]+other.coords[i] for i in range(3)])
	def __getitem__(self,index:int):
		return self.coords[index]
	def __mul__(self,value:float):
		return Vertex([self.coords[i]*value for i in range(3)])
	def __str__(self)->str:
		return f"Vertex\t{format_vector(self.coords)}\n"
	def __sub__(self,other:'Vertex'):
		return Vertex([self.coords[i]-other.coords[i] for i in range(3)])
	def __truediv__(self,value:float):
		return Vertex([self.coords[i]/value for i in range(3)])
	def distance_to(self,other:'Vertex'):
		return (other-self).length()
	def length(self)->float:
		return math.hypot(*self.coords)
	def normalized(self)->'Vertex':
		return self/self.length()
	def setx(self,value:float):
		self.coords[0]=value
	def sety(self,value:float):
		self.coords[1]=value
	def setz(self,value:float):
		self.coords[2]=value
	def snap(self,grid_distance:float):
		for i in range(3):
			self.coords[i]=round_to_grid(self.coords[i],grid_distance)
	x=property(lambda self:self.coords[0],setx,None,"X")
	y=property(lambda self:self.coords[1],sety,None,"Y")
	z=property(lambda self:self.coords[2],setz,None,"Z")

class Polygon:
	def __init__(self,verts:list[Vertex]=None,normal=None):
		self.pan:tuple[int]=None
		self.u=(1.,0.,0.)
		self.v=(0.,0.,1.)
		self.vertices=verts if verts else []
		self.normal=normal
		self.texture:str=""
		self.flags:int=0
	def __str__(self)->str:
		vertices="".join([str(v) for v in self.vertices])
		uv=f"TextureU\t{format_vector(self.u)}\nTextureV\t{format_vector(self.v)}\n"
		texture=f" Texture={self.texture}" if self.texture else ""
		flags=f" Flags={self.flags}" if self.flags else ""
		pan=f"Pan U={self.pan[0]} V={self.pan[1]}\n" if self.pan else ""
		polygon=f"Begin Polygon{texture}{flags}\n{pan}{uv}{vertices}End Polygon\n"
		return polygon
	def add_vertices(self,vert_list:list):
		self.vertices+=[Vertex(v) for v in vert_list]
	def length_xy(self)->float:
		l=0
		for v in self.vertices:
			for v2 in self.vertices:
				v.z=0.0
				v2.z=0.0
				curr=v.distance_to(v2)
				l=curr if curr>l else l
		return l

class Brush:
	def __init__(self,poly_list:list[Polygon]=None,location:list=None,actor_name=None):
		# Actor name can be omitted, UED will create one.
		self.actor_name:str=actor_name
		self.brush_name:str="Brush"
		self.csg:str="CSG_Subtract"
		self.mainscale:tuple=None
		self.postscale:tuple=None
		self.tempscale:tuple=None # TODO: remove tempscale
		self.group:str=None
		self.polygons=poly_list if poly_list else []
		self.location=location
		self.rotation:tuple=None
		self.prepivot=None
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
		verts=[v.coords for p in self.polygons for v in p.vertices]
		edges=[]
		faces=[]
		i=0
		for p in self.polygons:
			faces.append(list(range(i,i+len(p.vertices))))
			i+=len(p.vertices)
		return verts,edges,faces
	def snap(self,grid_distance:float=1.0):
		for p in self.polygons:
			#for i in range(len(p.vertices)):
			#	p.vertices[i].snap(grid_distance)
			for v in p.vertices:
				v.snap(grid_distance)
		if self.location:
			self.location=[round_to_grid(v,grid_distance) for v in self.location]