"""
Exporter.
"""
import math

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector,geometry

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
	brush.group=o.get("group",brush.group)
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

def export_uv(verts:list[Vector],uvs:list[Vector],normal:Vector)->tuple:
	""" Return Origin,TextureU,TextureV in tuple. """
	uvs=[Vector((uv.x,1-uv.y))*TEXTURE_SIZE for uv in uvs]
	verts=rotate_triangle_towards_normal(verts,Vector((0,0,1)))
	_print("Rotated verts to XY plane:",verts)
	height=verts[0].z
	verts=[v.xy for v in verts]
	_print("Flat Verts:",verts)
	m_uvs=Matrix((*[v.to_3d()+Vector((0,0,1)) for v in uvs],))
	m_verts=Matrix((*[v.to_3d()+Vector((0,0,1)) for v in verts],))
	_print("m_uvs:",m_uvs)
	_print("m_verts:",m_verts)
	m_uvs_inverse:Matrix=m_uvs.inverted_safe()
	m_verts_inverse:Matrix=m_verts.inverted_safe()
	_print("m_verts_inverse:",m_verts_inverse)
	_print("m_uvs_inverse:",m_uvs_inverse)
	u2v:Matrix=m_verts_inverse@m_uvs
	_print("Result UVs to Verts transform:",u2v)
	rot:Matrix=normal_rotation(Vector((0,0,1)),normal)
	tu:Vector=u2v.col[0].xy
	tv:Vector=u2v.col[1].xy
	o:Vector=u2v[2].xy
	tu=rot@tu.to_3d()
	tv=rot@tv.to_3d()
	# TODO: Origin doesn't come out right.
	o=rot@o.to_3d()
	return o,tu,tv

def get_material_name(obj,material_index:int)->str:
	""" Get material name using index. """
	return obj.data.materials[material_index].name if len(obj.data.materials)>0 else ""

def normal_rotation(n1:Vector,n2:Vector)->Matrix:
	""" Rotation matrix between normals n1 to n2. """
	assert n1!=Vector((0,0,0)) and n2!=Vector((0,0,0))
	# Angle between two.
	cos_theta:float=n1.dot(n2)/(n1.length*n2.length)
	try:
		theta:float=math.acos(cos_theta)
	except ValueError:
		theta=0
	# Rotation axis.
	axis:Vector=n1.cross(n2)
	axis.normalize()
	# Calculate rotation matrix using Rodrigues' formula.
	axis_skew=Matrix((
		(0, -axis.z, axis.y),
		(axis.z, 0, -axis.x),
		(-axis.y, axis.x, 0)
	))
	i:Matrix=Matrix.Identity(3)
	r:Matrix=i+axis_skew*math.sin(theta)+axis_skew@axis_skew*(1-math.cos(theta))
	return r

def polygon_texture_transform(face:'bmesh.types.BMFace',mesh:'bmesh.types.BMesh')->tuple:
	""" Compute the Origin, TextureU, TextureV for a given face. """
	points:list[bmesh.types.BMLoop]=face.loops[0:3]
	if len(points)<2 or len(mesh.loops.layers.uv)==0:
		print("Invalid geometry or no UV map.")
		return ((0,0,0),(1,0,0),(0,1,0))
	uvmap=mesh.loops.layers.uv[0]
	verts:list[Vector]=[x.vert.co for x in points] # type: ignore
	uvs:list[Vector]=[x[uvmap].uv for x in points] # type: ignore
	return export_uv(verts,uvs,face.normal)

def rotate_triangle_towards_normal(points:list[Vector],n:Vector)->list:
	""" Return points after plane is rotated towards n. """
	assert len(points)==3,"Not a triangle."
	plane_normal:Vector=geometry.normal(points)
	rotation:Matrix=normal_rotation(plane_normal,n)
	return [rotation@p for p in points]

def transpose(matrix:Matrix)->Matrix:
	""" mathutils.Matrix.transpose only works on square. """
	return Matrix([[row[i] for row in matrix] for i in range(len(matrix[0]))])
