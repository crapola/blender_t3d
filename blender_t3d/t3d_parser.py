"""
T3D parser.
"""
import ast
#import pprint
import re
from enum import IntEnum, auto

try:
	from . import t3d
except ImportError:
	import t3d

import time


class ParseError(SyntaxError):
	""" Parse error exception. """
	def __init__(self,filename:str,line:int,text:str,message:str)->None:
		self.msg=message
		self.lineno=line
		self.text=text
		self.filename=filename

def filter_brushes(text:str)->str:
	"""
	Filter T3D text to remove anything that's not a Brush actor.
	Return the modified text.
	"""
	pattern:str=r"""(Begin Actor Class=Brush .*?End Actor)"""
	rx:re.Pattern=re.compile(pattern,re.S|re.I)
	matches:list=rx.findall(text)
	ret:str="\n".join(matches)
	return ret


class Level(IntEnum):
	""" Current nesting level. """
	ROOT=0
	ACTOR=auto()
	BRUSH=auto()
	POLYLIST=auto()
	POLYGON=auto()

def name_values(words:list[str])->dict[str,str]:
	""" Extract "key=value" pairs into a dictionary. """
	d:dict[str,str]={}
	for x in words:
		nv:list[str]=x.split("=",1)
		if len(nv)==2:
			d[nv[0].strip()]=nv[1].strip()
	return d

def dict_from_t3d_property(line:str)->dict:
	"""
	Interpret a T3D Actor property as a Python nested dictionary.
	Example:
	 "TempScale=(Scale=(X=2.5,Y=4),SheerAxis=SHEER_ZX)"
	 gives:
	 {'TempScale': {'Scale': {'X': 2.5, 'Y': 4}, 'SheerAxis': 'SHEER_ZX'}}
	"""
	x:str="{"+line+"}"
	x=x.replace("(","{").replace(")","}").replace("=",":").replace("\"","")
	x=re.sub(r'([a-zA-Z_]+)',r'"\1"',x)
	d:dict={}
	try:
		d=ast.literal_eval(x)
	except (ValueError,SyntaxError):
		# Errors might happen on lines we don't care about.
		#print(line," ",x)
		pass
	return d

def coords_from_xyz_dict(d:dict,default:float=0.0)->tuple[float,float,float]:
	"""
	Turn dictionary keys "x","y","z" to a tuple (x,y,z).
	Missing coordinates are assigned the default value.
	"""
	x:float=d.get("x",d.get("X",default))
	y:float=d.get("y",d.get("Y",default))
	z:float=d.get("z",d.get("Z",default))
	return x,y,z

def rotation_from_dict(d:dict)->tuple[int,int,int]:
	"""
	Turn dictionary keys "roll","pitch","yaw" to a tuple.
	Case sensitive. Missing values are set to zero.
	"""
	x:int=d.get("roll",0)
	y:int=d.get("pitch",0)
	z:int=d.get("yaw",0)
	return x,y,z

def parse_vector(text:str)->tuple[float,...]:
	"""
	Interpret a T3D list of signed numbers to tuple of floats.
	Example:
	"+00001.000000,-00002.000000,-00008.500000" gives (1,-2,-8.5).
	"""
	return tuple(float(val) for val in text.split(","))

def parse_polygon_property(line:str)->dict[str,tuple]:
	"""
	Parse a Polygon property line.
	Those are the lines inside a Begin Polygon/End Polygon block.
	Return an empty dict if line was not valid.
	"""
	try:
		keyword:str
		data:str
		line:str=line.replace("\t"," ") # TODO: all file
		keyword,data=line.strip().split(" ",1)
		value:tuple=()
		if keyword=="pan":
			value=tuple(int(s[2:]) for s in data.split())
		else:
			value=parse_vector(data)
		return {keyword:value}
	except ValueError:
		return {}

def parse(text:str)->list[dict]:
	"""
	Parse T3D text containing only Brush actors.
	Return a list of brushes as nested dictionaries.
	"""
	text=text.lower()
	context:Level=Level.ROOT
	brushes:list[dict]=[]
	brush:dict={}
	line_number:int
	line:str
	for line_number,line in enumerate(text.splitlines()):
		# Remove whitespaces.
		line=line.strip()
		# Skip empty line.
		if not line:
			continue
		words:list[str]=line.split()
		if words[0]=="begin":
			context=Level(context+1)
			block_name:str=words[1]
			assert block_name==context.name.lower(),f"Unexpected Begin block '{block_name}'"
			match context:
				case Level.ACTOR:
					# Start a new Brush actor.
					brush:dict={"name":name_values(words)["name"]}
				case Level.BRUSH:
					# Get Brush name.
					brush_name:str=words[-1].split("=")[1]
					brush["brush_name"]=brush_name
				case Level.POLYLIST:
					# Start a new polygon list.
					brush["polylist"]=[]
				case Level.POLYGON:
					# Create a new polygon.
					p:dict=name_values(words)
					if p.get("flags",False):
						p["flags"]=int(p["flags"])
					brush["polylist"].append(p)
		elif words[0]=="end":
			context=Level(context-1)
			block_name=words[1]
			if context==Level.ROOT:
				# Brush completed.
				brushes.append(brush)
		else:
			if context==Level.ACTOR:
				d:dict=dict_from_t3d_property(line)
				brush.update(d)
			if context==Level.POLYGON:
				polyparam:dict=parse_polygon_property(line)
				if not polyparam:
					raise ParseError("filename",line_number,line,"Invalid Polygon property")
				# If it's a vertex, append to the list.
				if polyparam.get("vertex",None):
					polyparam["vertex"]=brush["polylist"][-1].get("vertex",[])+[polyparam["vertex"]]
				brush["polylist"][-1].update(polyparam)
	assert context==Level.ROOT,"Parser didn't end in root context."
	return brushes

def t3d_open(path:str)->list[t3d.Brush]:
	"""
	Open and interpret T3D file.
	path: Path to the T3D file.
	Return a list of t3d.Brush objects.
	"""
	with open(path,"rt",encoding="utf-8") as file:
		time_start:float=time.time()
		brushes_text:str=filter_brushes(file.read())
		brushes:list[dict]=parse(brushes_text)
		# Convert dictionaries to t3d.Brush.
		tbs:list[t3d.Brush]=[]
		for b in brushes:
			#pprint.pprint(b)
			# Convert values to tuples.
			if b.get("mainscale") and b.get("mainscale",{}).get("scale"):
				b["mainscale"]["scale"]=coords_from_xyz_dict(b["mainscale"]["scale"],1.0)
			if b.get("postscale") and b.get("postscale",{}).get("scale"):
				b["postscale"]["scale"]=coords_from_xyz_dict(b["postscale"]["scale"],1.0)
			if b.get("location"):
				b["location"]=coords_from_xyz_dict(b["location"])
			if b.get("prepivot"):
				b["prepivot"]=coords_from_xyz_dict(b["prepivot"])
			if b.get("rotation"):
				b["rotation"]=rotation_from_dict(b["rotation"])
			tb:t3d.Brush=t3d.Brush.from_dictionary(b)
			tbs.append(tb)
		print(f"Loaded {len(tbs)} brushes from {path} in {time.time()-time_start} seconds.")
		return tbs

def test()->None:
	""" Test. """
	samples_list:tuple[str,...]=(
		"dev/samples/swat/fairfax-swat4.t3d",
		"dev/samples/swat/map-ue2.t3d",
		"dev/samples/swat/streets-raveshield.t3d",
		"dev/samples/ut99/AS-Frigate.t3d",
		"dev/samples/ut99/CTF-Coret.t3d",
		"dev/samples/ut99/DM-Liandri.t3d",
		"dev/samples/ut99/DOM-Cinder.t3d",
		"dev/samples/ut2004/AS-FallenCity.t3d",
		"dev/samples/ut2004/BR-Anubis.t3d",
		"dev/samples/ut2004/DM-Deck17.t3d",
		"dev/samples/xiii/DM_Amos.t3d",
		"dev/samples/xiii/xiii_cubes.t3d"
	)
	for s in samples_list:
		b:list[t3d.Brush]=t3d_open(s)
		assert len(b)>0
	assert True

if __name__=="__main__":
	test()
