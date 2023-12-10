
bl_info={
	"name": "Import and export old Unreal .T3D format",
	"author": "Crapola",
	"version": (1,0,1),
	"blender": (2,80,0),
	"location": "File > Import-Export ; Object",
	"description": "Import and export UnrealED .T3D files.",
	"doc_url":"https://github.com/crapola/blender_t3d",
	"tracker_url":"https://github.com/crapola/blender_t3d/issues",
	"support":"COMMUNITY",
	"category":"Import-Export", # Category in Add-ons browser.
}

if "bpy" in locals():
	import importlib
	importlib.reload(exporter)
	importlib.reload(importer)
else:
	from . import exporter, importer

import bpy


INVALID_FILENAME="Invalid file name."

class OBJECT_OT_export_t3d_clipboard(bpy.types.Operator):
	"""Export selected meshes to T3D into the clipboard."""
	bl_idname="object.export_t3d_clipboard"
	bl_label="Export T3D to clipboard"

	scale:bpy.props.FloatProperty(name="Scale Multiplier",default=128.0)

	@classmethod
	def poll(cls,context):
		return context.selected_objects

	def execute(self,context):
		sel_objs=[obj for obj in context.selected_objects if obj.type=='MESH']
		num_brushes,txt=exporter.export(sel_objs,self.scale)
		context.window_manager.clipboard=txt
		self.report({'INFO'},f"{num_brushes} brushes exported to clipboard.")
		return {'FINISHED'}

	def invoke(self, context, event):
		wm=context.window_manager
		return wm.invoke_props_dialog(self)

class BT3D_MT_file_export(bpy.types.Operator):
	"""Export T3D file."""
	bl_idname="bt3d.file_export"
	bl_label="Export Unreal T3D (.t3d)"
	filename:bpy.props.StringProperty(subtype='FILE_NAME')
	filepath:bpy.props.StringProperty(subtype='FILE_PATH')
	scale:bpy.props.FloatProperty(
		name="Scale Multiplier",
		default=1.0,
		subtype='FACTOR')
	def execute(self,context):
		if not self.filename.split(".")[0]:
			self.report({'ERROR'},INVALID_FILENAME)
			return {'CANCELLED'}
		# Get meshes in scene.
		objs=[obj for obj in context.scene.objects if obj.type=='MESH']
		if not objs:
			self.report({'WARNING'},"There are no meshes in scene to export.")
			return {'CANCELLED'}
		num_brushes,txt=exporter.export(objs,self.scale)
		self.filepath=bpy.path.ensure_ext(self.filepath,".t3d")
		if not num_brushes:
			self.report({'WARNING'},"Nothing was converted.")
			return {'CANCELLED'}
		with open(self.filepath,"w") as f:
			f.write(txt)
		self.report({'INFO'},f"{num_brushes} brushes saved to {self.filepath}.")
		return {'FINISHED'}
	def invoke(self, context, event):
		if not self.filepath:
			self.filepath=bpy.path.ensure_ext(bpy.data.filepath,".t3d")
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}

class BT3D_MT_file_import(bpy.types.Operator):
	"""Import T3D file."""
	bl_idname="bt3d.file_import"
	bl_label="Import Unreal T3D (.t3d)"

	filename:bpy.props.StringProperty(
		name="input filename",
		subtype='FILE_NAME'
		)
	filepath:bpy.props.StringProperty(
		name="input file",
		subtype='FILE_PATH'
		)
	filter_glob:bpy.props.StringProperty(
		default="*.t3d",
		options={'HIDDEN'},
		)
	# Options.
	flip:bpy.props.BoolProperty(
		name="Flip normals",
		description="Flip normals of CSG_Subtract brushes",
		default=False
	)
	snap_vertices:bpy.props.BoolProperty(
		name="Snap vertices",
		description="Snap to grid",
		default=False
	)
	snap_distance:bpy.props.FloatProperty(
		name="Snap distance",
		default=1.0
		)

	def execute(self,context):
		if not self.filename.split(".")[0]:
			self.report({'ERROR'},INVALID_FILENAME)
			return {'CANCELLED'}
		importer.import_t3d_file(
			context,
			self.filepath,
			self.filename,
			self.snap_vertices,
			self.snap_distance,
			self.flip)
		return {'FINISHED'}

	def invoke(self, context, event):
		wm=context.window_manager
		wm.fileselect_add(self)
		return {'RUNNING_MODAL'}

classes = (
	BT3D_MT_file_export,
	BT3D_MT_file_import,
	OBJECT_OT_export_t3d_clipboard,
)
register_classes, unregister_classes = bpy.utils.register_classes_factory(classes)

menus=(
	lambda x,_:x.layout.operator(OBJECT_OT_export_t3d_clipboard.bl_idname),
	lambda x,_:x.layout.operator(BT3D_MT_file_export.bl_idname),
	lambda x,_:x.layout.operator(BT3D_MT_file_import.bl_idname),
)

def register():
	print("Registering.")
	register_classes()
	# Add to menu.
	bpy.types.VIEW3D_MT_object.append(menus[0])
	bpy.types.TOPBAR_MT_file_export.append(menus[1])
	bpy.types.TOPBAR_MT_file_import.append(menus[2])

def unregister():
	print("Unregistering.")
	# Remove from menu.
	bpy.types.VIEW3D_MT_object.remove(menus[0])
	bpy.types.TOPBAR_MT_file_export.remove(menus[1])
	bpy.types.TOPBAR_MT_file_import.remove(menus[2])
	unregister_classes()