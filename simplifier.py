from PIL import Image, ImageDraw
import sys
from randomness import instructions

# takes an image and converts the red values to be instruction values

INPUT = Image.open(sys.argv[1])
OUTPUT = Image.new("RGB", (256, 256))

instruction_count = {x : 0 for x in instructions}

if INPUT.size != (256, 256):
    print("Image input size must be 256x256 pixels.")

for x in range(256):
    for y in range(256):
        col = INPUT.getpixel((x, y))
        red = col[0]
        diffs = [abs(red - x) for x in instructions]
        inst = instructions[diffs.index(min(diffs))]
        OUTPUT.putpixel((x, y), (inst, col[1], col[2]))
        instruction_count[inst] += 1

print("\n".join([f"{hex(x)}: {instruction_count[x]}" for x in instruction_count]))
OUTPUT.save(sys.argv[2])