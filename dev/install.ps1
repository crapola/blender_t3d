# Copy folder into Blender addons folder.
#
# Note: it's just a convenience script for development.
#
$blender_paths=Resolve-Path "$env:appdata/Blender Foundation/Blender/[0-9]*"
$latest=$blender_paths[-1]
$latest="$env:appdata/Blender Foundation/Blender/3.3"
$target=Join-Path $latest "/scripts/addons/"
Write-Output "Copying to $target"
Copy-Item .\blender_t3d\ $target -Recurse -Force