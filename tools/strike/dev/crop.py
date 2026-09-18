import sys
from PIL import Image
src, out, x, y, w, h, s = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:8])
im = Image.open(src).crop((x, y, x+w, y+h)).resize((w*s, h*s), Image.NEAREST)
im.save(out); print(out, im.size)
