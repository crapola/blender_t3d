# Copy current folder into Blender addons folder.
$dirname=(Get-Item -path . | Select-Object -Property Basename).basename
$dest="$env:appdata/Blender Foundation/Blender/3.0/scripts/addons/$dirname"
if (!(Test-Path -Path $dest)) {New-Item $dest -Type Directory}
Copy-Item -Path ./*.py -Destination $dest -Recurse -Force -Exclude @('__pycache__')