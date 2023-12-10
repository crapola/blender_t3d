# Create release archive.
Remove-Item blender_t3d/__pycache__ -ErrorAction Ignore
Compress-Archive -Force -Path blender_t3d -DestinationPath blender_t3d.zip
Write-Output Ok
