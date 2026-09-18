import sys
args = sys.argv[1:]
sys.argv = ["x"]
exec(open("tools/strike/dev/render.py").read().split("LINES = [")[0])
from PIL import Image

text = args[0] if args else "aeg"
px = int(args[1]) if len(args) > 1 else 300
out = args[2] if len(args) > 2 else "/tmp/big.png"
W = int(px * 0.75 * len(text)) + 80
H = int(px * 1.9)
img = Image.new("L", (W, H), 255)
draw_line(img, text, px, 40, int(px * 1.35))
img.save(out)
print(out, img.size)
