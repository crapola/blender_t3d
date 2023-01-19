mkdir .\blender_t3d -Force
$files="__init__.py","exporter.py","importer.py","t3d_parser.py","t3d.py"
foreach ($f in $files) {
	copy-item $f .\blender_t3d
}
compress-archive .\blender_t3d .\blender_t3d.zip -Force
del .\blender_t3d