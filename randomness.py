from PIL import Image, ImageDraw
import random

img = Image.new("RGB", (256, 256))
instructions = [
    0x50,
    0x40,
    0xA1,
    0xA0,
    0xB0,
    0xC0,
    0xCA,
    0xD0,
    0x1A,
    0x1B,
    0xBB,
    0xEF,
    0xEE,
    0x2A,
    0x2B,
    0x2C,
    0x3A,
    0x3B,
    0x3C,
]

for x in range(256):
    for y in range(256):
        img.putpixel((x, y), tuple([random.choice(instructions),] + [random.randint(0, 255) for _ in range(2)]))

img.save("code.png")