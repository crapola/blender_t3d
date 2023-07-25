# Textures

In a .t3d file, polygons may have a texture name. When the importer loads the file into Blender it will apply a material of that name to the face, if such material exists.\
Consequently, if you want to see textures on the imported .t3d geomtry inside Blender, you need to have the correct materials loaded first.

Here is how you get textures from UT to Blender.

1. First step is to export the textures. The 469 version of UnrealED has a convenient way to do so from the Texture browser: `File > Batchexport to PNG from package`.
2. The resulting folder has .png files organized in subfolders, but we'd prefer having all the files in one place. The `flatten.ps1` powershell script can help with that.
3. To import those .png as materials into Blender, activate and use Blender's default addon called "Import Image as Planes".
4. The planes generated in the scene can be deleted. The last thing to do is to fix the generated materials using this Python script:
    ~~~
    import bpy
    for m in bpy.data.materials:
        m.use_backface_culling=True
        if m.node_tree and m.node_tree.nodes.get("Image Texture"):
            m.node_tree.nodes["Image Texture"].extension="REPEAT"
    ~~~
    It will make the texture stile and backface-cullable.
5. The blend file can now be saved and used as material library.