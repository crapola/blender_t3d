"""
Tests ran by pytest.
"""
# pylint: skip-file
import os
import sys

sys.path.append(os.getcwd()+"/blender_t3d")
from t3d import Brush, CsgOper, SheerAxis, Vec3, Vertex
from t3d_parser import t3d_open


def test_t3d()->None:
	assert str(Vertex(1,-2.5))=="Vertex\t+00001.000000,-00002.500000,+00000.000000\n"
	assert Vec3(100).coords==[100,0,0]
	assert Vertex(1,2).coords==[1,2,0]
	assert Vertex(1,2,3,4).coords==[1,2,3]
	assert Vertex((1,2)).coords==[1,2,0]
	assert Vertex((1,-2,3,4)).coords==[1,-2,3]
	assert Vertex((1000,)).coords==[1000,0,0]
	assert Vertex(1)+Vertex(2)==Vertex(3)
	assert Vertex(0)!=Vertex(0.00001)
	assert Vertex(100,200,0)-Vertex(0,50,2)==Vertex(100,150,-2)
	v=Vertex(0,-1,2)
	v.x=10
	v.z=v.y
	assert v==Vertex(10,-1,-1)
	assert str(CsgOper(-1))=="none"
	assert str(CsgOper(0))=="none"
	assert str(CsgOper(1))=="csg_add"
	assert str(CsgOper(2))=="csg_subtract"
	assert str(CsgOper(100))=="none"
	assert CsgOper("whatever")==CsgOper.NONE
	assert CsgOper("csg_add")==CsgOper.CSG_ADD
	assert CsgOper("csg_subtract")==CsgOper.CSG_SUBTRACT
	assert CsgOper("cSG_SuBtraCt")==CsgOper.CSG_SUBTRACT
	assert str(SheerAxis(1))=="sheer_xy"
	assert str(SheerAxis(5))=="sheer_zx"
	assert SheerAxis(7)==SheerAxis.NONE

def test_parser()->None:
	""" Test. """
	samples_list:tuple[str,...]=(
		"development/samples/swat/fairfax-swat4.t3d",
		"development/samples/swat/map-ue2.t3d",
		"development/samples/swat/streets-raveshield.t3d",
		"development/samples/ut99/AS-Frigate.t3d",
		"development/samples/ut99/CTF-Coret.t3d",
		"development/samples/ut99/DM-Liandri.t3d",
		"development/samples/ut99/DOM-Cinder.t3d",
		"development/samples/ut2004/AS-FallenCity.t3d",
		"development/samples/ut2004/BR-Anubis.t3d",
		"development/samples/ut2004/DM-Deck17.t3d",
		"development/samples/xiii/DM_Amos.t3d",
		"development/samples/xiii/xiii_cubes.t3d"
	)
	for s in samples_list:
		b:list[Brush]=t3d_open(s)
		assert len(b)>0
	assert True