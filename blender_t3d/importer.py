"""
Importer.
"""
import math
import time
import typing
from pathlib import Path

import bmesh
from bmesh.types import BMLayerItem
import bpy
from bpy.types import Material, Mesh
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

def find_material(name:str)->Material|None:
	"""
	Case insensitive material search in Blender file.
	It returns the first match in cases of case collisions.
	"""
	for m in bpy.data.materials:
		if name.lower()==m.name.lower():
			return m
	return None

def material_index_by_name(obj,matname:str)->int:
	"""
	Get material index using material name in object.
	If material is not found on object, return 0.
	"""
	mat_dict:dict[str,int]={mat.name: i for i, mat in enumerate(obj.data.materials)}
	try:
		ret:int=mat_dict[matname]
		return ret
	except KeyError:
		return 0

def create_object(collection:bpy.types.Collection,b:t3d.Brush)->tuple[bpy.types.Object,set[str]]:
	""" Create blender object from t3d.Brush. """
	# Keep track of missing materials for this object.
	missing_materials:set[str]=set()
	# Create mesh.
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
	rotation:Vector|Euler=Vector(b.rotation or (0,0,0))*math.tau/65536
	rotation.xy=-rotation.xy
	rotation=Euler(rotation.to_tuple())

	pivot.rotate(rotation)
	pivot*=postscale*mainscale

	o.scale=mainscale
	o.rotation_euler=rotation
	o.location-=pivot

	# TODO: Shear

	bm:bmesh.types.BMesh=bmesh.new()
	bm.from_mesh(m)
	# Create UV layer.
	uv_layer:bmesh.types.BMLayerItem=bm.loops.layers.uv.verify()
	# Polygon attributes.
	texture_names:list[str]=[p.texture for p in b.polygons]
	flags:list[int]=[p.flags for p in b.polygons]
	layer_texture:BMLayerItem[bytes]=bm.faces.layers.string.get("texture") or bm.faces.layers.string.new("texture")
	layer_flags:BMLayerItem[int]=bm.faces.layers.int.get("flags") or bm.faces.layers.int.new("flags")
	i:int
	face:bmesh.types.BMFace
	for i,face in enumerate(bm.faces):
		if texture_names[i]:
			face[layer_texture]=bytes(str(texture_names[i]),'utf-8')
			# Note: material names are case sensitive in Blender but
			# not in UnrealEd.
			scene_mat:Material|None=find_material(texture_names[i])
			if scene_mat:
				object_mesh_data:Mesh=typing.cast(Mesh,o.data)
				# Add material to object if it's not there yet.
				if not scene_mat.name in object_mesh_data.materials:
					object_mesh_data.materials.append(scene_mat)
				# Assign the face.
				face.material_index=material_index_by_name(o,scene_mat.name)
			else:
				# Missing material.
				missing_materials.add(texture_names[i])
		face[layer_flags]=flags[i]
		# UV coordinates.
		poly:t3d.Polygon=b.polygons[i]
		for loop in face.loops:
			vert:Vector=loop.vert.co
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
		o.select_set(True)
		bpy.context.view_layer.objects.active=o
		bpy.ops.object.transform_apply(scale=True,rotation=True,location=False)
		o.scale=b.postscale

	# Keep Unreal stuff as Object Custom Properties.
	o["csg"]=b.csg
	o["group"]=b.group
	o["polyflags"]=b.polyflags

	return o,missing_materials

def import_t3d_file(
	context:bpy.types.Context,
	filepath:str,
	snap_vertices:bool,
	snap_distance:float,
	flip:bool
	)->dict[str,list[str]]:
	""" Import T3D file into scene. """
	# Missing materials that will be reported.
	missing_materials:set[str]=set()
	# Parse T3D file.
	brushes:list[t3d.Brush]=t3d_parser.t3d_open(filepath)
	time_start:float=time.time()
	# Create a collection bearing the T3D file's name.
	coll:bpy.types.Collection=bpy.data.collections.new(Path(filepath).name)
	# Add it to the scene.
	context.scene.collection.children.link(coll)
	# Turn every t3d.Brush into a Blender object.
	for b in brushes:
		obj:bpy.types.Object
		if b.group=='cube':
			# Ignore red brush.
			print(f"blender_t3d: {b.actor_name} is the red brush, so it won't be imported.")
			continue
		# Snap to grid.
		if snap_vertices:
			b.snap(snap_distance)
		obj_missing_mats:set[str]
		obj,obj_missing_mats=create_object(coll,b)
		missing_materials.update(obj_missing_mats)
		# Flip.
		if b.csg.lower()=="csg_subtract" and flip:
			obj.data.flip_normals()
	# Output time to console.
	print(f"blender_t3d: Created {len(brushes)} meshes in {time.time()-time_start} seconds.")
	results:dict={"WARNING":[]}
	if missing_materials:
		results["WARNING"]=[f"{len(missing_materials)} materials missing: {', '.join(sorted(missing_materials))}"]
	return results
