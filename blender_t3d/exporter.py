import math

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

try:
	from .t3d import Brush, Polygon, Vertex
except:
	from t3d import Brush, Polygon, Vertex

DEBUG=1
def _print(*_):pass
if DEBUG:_print=print

TEXTURE_SIZE=256

def basis_from_points(points:list)->Matrix:
	""" 2D Basis, middle point is origin. """
	m=Matrix( ((1,0,0),(0,1,0),(0,0,1)) )
	v0,v1,v2=points
	m[0].xy=(v2-v1) #X
	m[1].xy=(v0-v1) #Y
	m[2].xy=v1 # Origin
	m.transpose()
	return m

def export(object_list,scale_multiplier:float=128.0)->tuple:
	stuff=""
	for obj in object_list:
		mesh:bpy.types.Mesh=obj.data
		bm=bmesh.new()
		bm.from_mesh(mesh)

		uv_layer_0:bmesh.types.BMLayerItem|None=None
		if bm.loops.layers.uv:
			uv_layer_0 = bm.loops.layers.uv[0]
		layer_texture=bm.faces.layers.string.get("texture")
		poly_list=[]
		for f in bm.faces:
			# Vertices.
			verts:list[Vertex]=[Vertex(v.co*scale_multiplier) for v in f.verts]
			poly=Polygon(verts,f.normal)

			# Get texture name, either from custom attribute if it exists (brush
			# was imported), or material.
			if layer_texture:
				poly.texture=f[layer_texture].decode('utf-8')
			elif len(obj.data.materials)>0:
				name=obj.data.materials[f.material_index].name
				poly.texture=name

			_print(f"---- Face {f.index} {poly.texture} ----")

			# Texture coordinates.

			# Compute floor/UV (plane where Z is 0) to surface transform, with
			# the first three verts of polygon.
			n=f.normal
			first_three=f.loops[0:3]
			v0,v1,v2=[v.vert.co for v in first_three]
			b=Matrix()
			b[2].xyz=n
			b[0].xyz=(v0-v1)
			b[1].xyz=(v2-v1)
			b[3].xyz=v0
			b.transpose() # Needed.
			b.invert()
			axis_x=Vector((1,0,0))
			axis_y=Vector((0,1,0))
			# Basic texturing.
			poly.u=b.transposed()@axis_x
			poly.v=b.transposed()@axis_y

			# Convert Blender UV Map if it exists.
			if uv_layer_0:
				v0i=(b@v0)
				v1i=(b@v1)
				v2i=(b@v2)
				# We assume UVs are a linear transform of the polygon shape.
				# Figure out that transform by using the first three verts.
				first_three_uvs=[l[uv_layer_0].uv for l in f.loops[0:3]]
				u0,u1,u2=first_three_uvs
				# mv=quad->poly, mu=poly->uv.
				mv=basis_from_points( (v0i.xy,v1i.xy,v2i.xy) )
				mu=basis_from_points( (u0,u1,u2) )
				t=mu @ mv.inverted()
				t.resize_4x4()
				t.transpose()
				b.transpose()

				poly.u=b @ (t @ axis_x*TEXTURE_SIZE/scale_multiplier)
				poly.v=b @ (t @ axis_y*TEXTURE_SIZE/scale_multiplier)

				poly.u=-poly.u
				poly.v=-poly.v

				# Pan.
				v=Vector((1,1,1))
				pan=mu.transposed()[2]*TEXTURE_SIZE
				#pan=(v-mu.transposed()[2] ) *TEXTURE_SIZE
				#pan.xy=pan.yz
				#pan+=Vector((0,128,0))
				_print(mu)
				_print(pan)

				if pan:
					poly.pan=(int(pan.x),int(pan.y))

			poly_list.append(poly)

		brush=Brush(poly_list,obj.location*scale_multiplier,obj.name)

		if obj.rotation_euler!=Euler((0,0,0)):
			brush.rotation=Vector(obj.rotation_euler)*65536/math.tau
		if obj.scale!=Vector((0,0,0)):
			brush.mainscale=obj.scale
		print(obj.keys())
		if mesh.get("csg"):
			_print("CSG=",mesh["csg"])
			brush.csg=mesh["csg"]

		stuff+=str(brush)

		bm.to_mesh(mesh)
		bm.free()

	everything=f"""Begin Map\n{stuff}End Map\n"""
	return len(object_list),everything