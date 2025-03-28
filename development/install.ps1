<#
.SYNOPSIS
This script directly installs this add-on to all existing Blender installations.
.DESCRIPTION
This script is used during development to quickly update and test the add-on.
After running the script, don't forget to Reload Scripts in Blender.
Topbar ‣ Blender ‣ System ‣ Reload Scripts.
#>
$blender_paths=Resolve-Path "$env:appdata/Blender Foundation/Blender/[0-9]*"
Write-Output "Installing add-on to: $blender_paths"
$exclude=("__pycache__","*.pyc")
$blender_paths | ForEach-Object {
	Copy-Item -Path .\blender_t3d\ -Destination "$_/scripts/addons/" -Exclude $exclude -Force -Recurse -Verbose
}