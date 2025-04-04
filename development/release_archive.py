"""
Create release archive.
"""

import pathlib
import tomllib
import zipfile

def get_version()->str:
	""" Get version of the add-on from manifest. """
	with open("blender_t3d/blender_manifest.toml","rb") as f:
		return tomllib.load(f)["version"]

def zip_folder(folder,output_zip)->None:
	""" Zip the folder. """
	with zipfile.ZipFile(output_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as zipf:
		for p in pathlib.Path(folder).iterdir():
			if p.name!="__pycache__":
				print(f"Adding {p}.")
				zipf.write(p)

def main()->None:
	""" main() """
	version:str=get_version()
	filename:str=f"blender_t3d_v{version}.zip"
	if not pathlib.Path("bin/").exists():
		pathlib.Path("bin/").mkdir()
	zip_folder("blender_t3d","bin/"+filename)
	print(f"Created bin/{filename}")

if __name__=="__main__":
	main()
