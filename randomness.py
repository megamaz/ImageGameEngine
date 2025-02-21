from PIL import Image, ImageDraw
import random

img = Image.new("RGB", (256, 256))

for x in range(256):
    for y in range(256):
        img.putpixel((x, y), tuple([random.randint(0, 255) for _ in range(3)]))

img.save("out.png")