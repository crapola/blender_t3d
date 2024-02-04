"""
Importer.
"""
import math
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Euler, Vector

try:
	from . import t3d, t3d_parser
except ImportError:
	import t3d
	import t3d_parser

TEXTURE_SIZE:float=256.0

def convert_uv(vertex:Vector,
			   origin:Vector,
			   texture_u:Vector,
			   texture_v:Vector,
			   pan:Vector)->Vector:
	""" Calculate UV coordinates from T3D Vertex and Polygon attributes. """
	v:Vector=vertex-origin
	return Vector((v.dot(texture_u),v.dot(texture_v)))+pan

def material_index_by_name(obj,matname:str)->int:
	"""
	Get material index using material name in object.
	If material is not found on object, return 0.
	"""
	mat_dict = {mat.name: i for i, mat in enumerate(obj.data.materials)}
	try:
		ret=mat_dict[matname]
		return ret
	except KeyError:
		return 0

def create_object(collection:bpy.types.Collection,b:t3d.Brush)->bpy.types.Object:
	""" Create blender object from t3d.Brush. """
	m:bpy.types.Mesh=bpy.data.meshes.new(b.actor_name)
	m.from_pydata(*b.get_pydata())
	# Create object.
	o:bpy.types.Object=bpy.data.objects.new(b.actor_name,m)
	# Location.
	o.location=b.location or (0,0,0)
	# Color by CSG (for ViewPort Shading in Object mode).
	o.color=(1,0.5,0,1) if b.csg=="csg_subtract" else (0,0,1,1)
	# Apply transforms.
	mainscale=Vector(b.mainscale or (1,1,1))
	pivot=Vector(b.prepivot or (0,0,0))
	postscale=Vector(b.postscale or (1,1,1))
	rotation=Vector(b.rotation or (0,0,0))*math.tau/65536
	rotation.xy=-rotation.xy
	rotation=Euler(rotation)

	pivot.rotate(rotation)
	pivot*=postscale*mainscale

	o.scale=mainscale
	o.rotation_euler=rotation
	o.location-=pivot

	# TODO: Shear

	bm:bmesh.types.BMesh=bmesh.new()
	bm.from_mesh(m)
	# Create UV layer.
	#uv_map=o.data.uv_layers.new(name='uvmap')
	uv_layer=bm.loops.layers.uv.verify()
	# Polygon attributes.
	texture_names=[p.texture for p in b.polygons]
	flags=[p.flags for p in b.polygons]
	layer_texture=bm.faces.layers.string.get("texture") or bm.faces.layers.string.new("texture")
	layer_flags=bm.faces.layers.int.get("flags") or bm.faces.layers.int.new("flags")
	for i,face in enumerate(bm.faces):
		if texture_names[i]:
			face[layer_texture]=bytes(str(texture_names[i]),'utf-8')
			# Note: material names are case sensitive in Blender.
			scene_mat=bpy.data.materials.get(texture_names[i])
			# Add material to object if it's not there yet.
			if scene_mat and not texture_names[i] in o.data.materials:
				o.data.materials.append(scene_mat)
			# Assign the face.
			face.material_index=material_index_by_name(o,texture_names[i])
		face[layer_flags]=flags[i]
		# UV coordinates.
		poly=b.polygons[i]
		for loop in face.loops:
			vert=loop.vert.co
			tu=Vector(poly.u)
			tv=Vector(poly.v)
			origin=Vector(poly.origin)
			pan=Vector(poly.pan)
			loop[uv_layer].uv=convert_uv(vert,origin,tu,tv,pan)/TEXTURE_SIZE
			# Fix orientation.
			loop[uv_layer].uv*=Vector((1,-1))

	bm.to_mesh(m)
	bm.free()

	collection.objects.link(o)
	# PostScale requires applying previous transforms.
	if b.postscale:
		#print("Postscale ",b.postscale)
		o.select_set(True)
		bpy.context.view_layer.objects.active=o
		bpy.ops.object.transform_apply(scale=True,rotation=True,location=False)
		o.scale=b.postscale

	# Keep Unreal stuff as Object Custom Properties.
	o["csg"]=b.csg
	o["polyflags"]=b.polyflags

	return o

def import_t3d_file(
	context:bpy.types.Context,
	filepath:str,
	snap_vertices:bool,
	snap_distance:float,
	flip:bool,
	)->None:
	""" Import T3D file into scene. """

	# Parse T3D file.
	brushes:list[t3d.Brush]=t3d_parser.t3d_open(filepath)
	time_start:float=time.time()
	# Create a collection bearing the T3D file's name.
	coll:bpy.types.Collection=bpy.data.collections.new(Path(filepath).name)
	context.scene.collection.children.link(coll)
	# Turn every t3d.Brush into a Blender object.
	for b in brushes:
		#print(f"Importing {b.actor_name}...")
		if b.group=='"cube"':
			# Ignore red brush.
			print(f"blender_t3d import: {b.actor_name} is the red brush, so it won't be imported.")
			continue
		# Snap to grid.
		if snap_vertices:
			b.snap(snap_distance)
		obj=create_object(coll,b)
		# Flip.
		if b.csg.lower()=="csg_subtract" and flip:
			obj.data.flip_normals()
	# Output time to console.
	print(f"Created {len(brushes)} meshes in {time.time()-time_start} seconds.")
