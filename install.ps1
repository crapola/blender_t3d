# Copy folder into Blender addons folder.
Copy-Item .\blender_t3d\ "$env:appdata/Blender Foundation/Blender/3.0/scripts/addons/$dirname" -Recurse -Force