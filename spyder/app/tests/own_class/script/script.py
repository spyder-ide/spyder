from pathlib import Path
import sys

_file_path = Path(__file__)
_mod_path = str(_file_path.parents[1])
sys.path.append(_mod_path)

from mod import myclass

mc_instance = myclass.MyClass()
