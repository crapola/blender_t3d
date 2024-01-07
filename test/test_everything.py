"""
Tests ran by pytest.
"""
# pylint: skip-file
import os
import sys

sys.path.append(os.getcwd()+"/blender_t3d")
import t3d_parser

def test_everything()->None:
	t3d_parser.main()