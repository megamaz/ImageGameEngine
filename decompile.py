import sys
from PIL import Image

img = Image.open(sys.argv[1])
outfile = open(sys.argv[2], "w", encoding="utf-8")


for x in range(256):
    for y in range(256):
        pixel = ' '.join([f'{n:02x}' for n in img.getpixel((x, y))[:3]])
        line = f"{x:02x} {y:02x}: {pixel}\n".upper()
        outfile.write(line)
outfile.close()