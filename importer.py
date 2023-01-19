import math

import bmesh
import bpy
import mathutils
from mathutils import Euler, Vector

try:
	from . import t3d_parser
except:
	import t3d_parser
	pass
	#t3d_parser=bpy.data.texts["t3d_parser.py"].as_module()

TEXTURE_SIZE:float=256.0

def convert_uv(mesh_vertex:Vector,texture_u:Vector,texture_v:Vector)->Vector:
	return Vector((mesh_vertex.dot(texture_u),mesh_vertex.dot(texture_v)))/TEXTURE_SIZE

# Get material index using material name in object.
# If material is not found on object, return 0.
def material_index_by_name(obj,matname:str)->int:
	mat_dict = {mat.name: i for i, mat in enumerate(obj.data.materials)}
	try:
		ret=mat_dict[matname]
		return ret
	except KeyError:
		return 0

def import_t3d_file(
	context:bpy.context,
	filepath:str,
	filename:str,
	snap_vertices:bool,
	snap_distance:float,
	flip:bool,
	):

	brushes=t3d_parser.t3d_open(filepath)
	coll=bpy.data.collections.new(filename)
	context.scene.collection.children.link(coll)
	for b in brushes:
		print(f"Importing {b.actor_name}...")
		if b.group=='"Cube"':
			# Ignore red brush.
			print(f"{b.actor_name} is the red brush.")
			continue
		data=b.get_pydata()

		# Invert Y's
		# for v in data[0]:
		#   v[1]=-v[1]
		# if b.location:
		#   b.location=(b.location[0],-b.location[1],b.location[2])
		# if b.prepivot:
		#   b.prepivot=(b.prepivot[0],-b.prepivot[1],b.prepivot[2])

		# Snap to grid.
		if snap_vertices:
			b.snap(snap_distance)

		# Create mesh.
		m=bpy.data.meshes.new(b.actor_name)
		m.from_pydata(*data)
		m.update()

		# Flip.
		if b.csg=="CSG_Subtract" and flip:
			print("FLIP!")
			m.flip_normals()

		# Create object.
		o=bpy.data.objects.new(b.actor_name,m)
		coll.objects.link(o)
		# Location.
		o.location=b.location or (0,0,0)
		# Color by CSG (for ViewPort Shading in Object mode).
		o.color=(1,0.5,0,1) if b.csg=="CSG_Subtract" else (0,0,1,1)

		# Apply transforms.

		mainscale=Vector(b.mainscale or (1,1,1))
		pivot=Vector(b.prepivot or (0,0,0))
		postscale=Vector(b.postscale or (1,1,1))
		rotation=Vector(b.rotation or (0,0,0))*math.tau/65536
		rotation.xy=-rotation.xy
		rotation=Euler(rotation)

		pivot.rotate(rotation)
		pivot*=postscale*mainscale

		print(f"{b.actor_name} PrePivot=",pivot)

		o.scale=mainscale
		o.rotation_euler=rotation
		o.location-=pivot

		bm=bmesh.new()
		bm.from_mesh(m)
		# Create UV layer.
		uv_layer=bm.loops.layers.uv.verify()
		# Polygon attributes.
		texture_names=[p.texture for p in b.polygons]
		flags=[p.flags for p in b.polygons]
		layer_texture=bm.faces.layers.string.get("texture") or bm.faces.layers.string.new("texture")
		layer_flags=bm.faces.layers.int.get("flags") or bm.faces.layers.int.new("flags")
		for i,face in enumerate(bm.faces):
			if texture_names[i]:
				face[layer_texture]=bytes(str(texture_names[i]),'utf-8')
				scene_mat=bpy.data.materials.get(texture_names[i])
				# Add material to object if it's not there yet.
				if scene_mat and not (texture_names[i] in o.data.materials):
					o.data.materials.append(scene_mat)
				# Assign the face.
				face.material_index=material_index_by_name(o,texture_names[i])
			face[layer_flags]=flags[i]
			print(face.calc_tangent_edge())

			#bm.faces.layers.tex.verify()
			# UV coordinates.
			poly=b.polygons[i]
			for j,loop in enumerate(face.loops):
				vert=loop.vert.co
				tu=Vector(poly.u)
				tv=Vector(poly.v)
				pan=Vector(poly.pan)/TEXTURE_SIZE if poly.pan else Vector((0,0))
				loop[uv_layer].uv=convert_uv(vert,tu,tv)+pan

		bm.to_mesh(m)
		bm.free()

		# PostScale requires applying previous transforms.
		if b.postscale:
			print("Postscale ",b.postscale)
			o.select_set(True)
			bpy.context.view_layer.objects.active=o
			bpy.ops.object.transform_apply(scale=True,rotation=True,location=False)
			o.scale=b.postscale

		# Keep Unreal stuff as Custom Properties.
		o["csg"]=b.csg


