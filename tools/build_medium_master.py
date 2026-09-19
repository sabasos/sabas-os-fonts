"""
Medium (wght 500) master, derived from Regular with the same outline offsetting as
the other weights (see offset_master.py), so its point structure matches Regular's.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from offset_master import build_master

REG = Path("sources/sabas-ui/SabasUI-Regular.ufo")
DST = Path("sources/sabas-ui/SabasUI-Medium.ufo")

if __name__ == "__main__":
    build_master(REG, DST, "Medium", 100, 86, weight_class=500)
    print(f"Saved {DST}")
