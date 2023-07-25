# Copy folder into Blender addons folder.
$ver="3.4"
Copy-Item .\blender_t3d\ "$env:appdata/Blender Foundation/Blender/$ver/scripts/addons/$dirname" -Recurse -Force