"""
Exporter.
"""
import math

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

try:
	from .t3d import Brush, Polygon, Vertex
except ImportError:
	from t3d import Brush, Polygon, Vertex

DEBUG=0
def _print(*_):
	pass
if DEBUG:
	_print=print

TEXTURE_SIZE:float=256.0

def basis_xform(a:Matrix,b:Matrix)->Matrix:
	""" Get transform a -> b. """
	return b@a.inverted_safe() # type: ignore

def basis_from_points(o:Vector,x:Vector,y:Vector)->Matrix:
	"""
	2D Basis.
	"""
	m=Matrix( ((1,0,0),(0,1,0),(0,0,1)) )
	m[0].xy=x-o #X
	m[1].xy=y-o #Y
	m[2].xy=o # Origin
	m.transpose()
	return m

def get_material_name(obj,material_index:int)->str:
	""" Get material name using index. """
	return obj.data.materials[material_index].name if len(obj.data.materials)>0 else ""

def normal_rotation(n:Vector)->Matrix:
	""" Return the 3x3 matrix that rotates the Z=0 plane towards n. """
	#https://math.stackexchange.com/a/1957132
	l:float=math.sqrt(n.x**2+n.y**2)
	if l==0:
		return Matrix.Identity(3)
	return Matrix([[n.y/l,-n.x/l,0],[n.x*n.z/l,n.y*n.z/l,-l],[n.x,n.y,n.z]])

def flat_face(verts:list[Vector])->tuple[Vector,...]:
	"""
	Project three 3D points onto their 2D plane.
	The point are respectively, origin, x axis, y axis.
	Return list of three 2D points. First is always (0,0).
	"""
	assert len(verts)==3,"Requires three vectors."
	# Define the plane.
	po:Vector=verts[0] # Origin of the plane.
	px:Vector=verts[1]-po # First direction vector.
	py:Vector=verts[2]-po # Second direction vector.
	px.normalize()
	# Gram-Schmidt process.
	py=py-px.dot(py)*px
	py.normalize()
	return tuple(Vector((px.dot(v-po),py.dot(v-po))) for v in verts)

def transpose(matrix:Matrix)->Matrix:
	""" mathutils.Matrix.transpose only works on square. """
	return Matrix([[row[i] for row in matrix] for i in range(len(matrix[0]))])

def export_uv(verts:list[Vector],uvs:list[Vector],normal:Vector)->Matrix:
	""" Export UVs. """
	v2d=flat_face(verts)
	uv_basis=basis_from_points(*uvs)
	vert_basis=basis_from_points(*v2d)
	transform=basis_xform(vert_basis,uv_basis)
	print("verts=",verts)
	print("uvs=",uvs)
	print("verts2d=",v2d)
	print("transform=",transform)
	m=transform.transposed()
	temp:Vector=m[0].copy()
	m[0]=m[2].copy()
	m[2]=temp
	# The matrix m holds the 2D affine transform on the Z=0 plane.
	# [ ox oy oz ]
	# [ ux uy  0 ]
	# [ vx vy  0 ]
	# Now, we use the polygon normal to rotate it into 3D.
	print(f"Face's normal is {normal}.")
	r:Matrix=normal_rotation(normal)
	print(f"Plane rotation: {r}")
	m:Matrix=m@r
	print(f"3D transform:{m}")
	return m

def polygon_texture_transform(face:'bmesh.types.BMFace',mesh:'bmesh.types.BMesh')->tuple:
	""" Compute the Origin, TextureU, TextureV for a given face. """
	points:list[bmesh.types.BMLoop]=face.loops[0:3]

	if len(points)<2 or len(mesh.loops.layers.uv)==0:
		print("Invalid geometry or no UV map.")
		return ((0,0,0),(1,0,0),(0,1,0))

	uvmap=mesh.loops.layers.uv[0]
	verts:list[Vector]=[x.vert.co for x in points] # type: ignore
	uvs:list[Vector]=[x[uvmap].uv for x in points] # type: ignore

	#uvs=[Vector((x.x,x.y)) for x in uvs]

	m:Matrix=export_uv(verts,uvs,face.normal)*TEXTURE_SIZE
	print("M=",m)

	origin:tuple
	tu:tuple
	tv:tuple
	origin,tu,tv=m[0].to_tuple(),m[1].to_tuple(),m[2].to_tuple()
	return origin,tu,tv

def brush_from_object(o:'bpy.types.Object',scale_multiplier:float=1.0)->Brush|str:
	""" Turn Blender Object into t3d.Brush. """

	if o.type!="MESH":
		print(f"{o} is not a mesh.")
		return ""

	print(f"Exporting {o.name}...")

	bm:bmesh.types.BMesh=bmesh.new()
	bm.from_mesh(o.data)

	poly_list:list[Polygon]=[]
	f:bmesh.types.BMFace
	for f in bm.faces:
		vertices:list[bmesh.types.BMVert]=[v for v in f.verts if isinstance(v,bmesh.types.BMVert)]
		verts:list[Vertex]=[Vertex((Vector(v.co)*scale_multiplier).to_tuple()) for v in vertices]
		poly=Polygon(verts)
		# Texture name.
		poly.texture=get_material_name(o,f.material_index)
		# Texture coordinates.
		poly.origin,poly.u,poly.v=polygon_texture_transform(f,bm)
		# Add to the list.
		poly_list.append(poly)
	bm.to_mesh(o.data)
	bm.free()

	# Instance Brush with location and name.
	brush=Brush(poly_list,o.location*scale_multiplier)
	brush.actor_name=o.name.replace(" ","_")

	# Rotation and scaling.
	if o.rotation_euler!=Euler((0,0,0)):
		brush.rotation=Vector(o.rotation_euler)*65536/math.tau
		brush.rotation.xy=-brush.rotation.xy
	if o.scale!=Vector((0,0,0)):
		brush.mainscale=o.scale

	# Custom properties.
	#print(o.keys())
	brush.csg=o.get("csg",brush.csg)
	brush.polyflags=o.get("polyflags",brush.polyflags)

	return brush

def export(object_list,scale_multiplier:float=1.0)->str:
	"""
	Export objects to a T3D text.
	Return empty string if nothing was exported.
	"""
	# TODO: In a .T3D file, the first brush is the red brush.
	# Perhaps insert dummy red brush for file export.
	t3d_text:str="".join(str(brush_from_object(obj,scale_multiplier)) for obj in object_list)
	if t3d_text:
		t3d_text=f"""Begin Map\n{t3d_text}End Map\n"""
	return t3d_text
