# blender_t3d

Blender Import-Export add-on for old UnrealED .T3D files.

## Installation

Download the release .zip and install it (Preferences > Add-ons > Install...).

The importer uses [Lark](https://pypi.org/project/lark-parser/) as parser.
To install Lark, run the follow script in Blender in the Scripting window:

```
import pip
pip.main(["install","lark"])
```

Once Lark is installed you can enable the add-on.

## Usage

The add-on adds the following menu items:

`File > Import > Import Unreal .T3D (.t3d)` \
`File > Export > Export Unreal .T3D (.t3d)` \
`Object > Export T3D to clipboard` to paste directly selected mesh(es) into the clipboard.


