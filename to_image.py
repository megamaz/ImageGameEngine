from PIL import Image, ImageDraw
import random

code = open("./code.txt", "r").read().splitlines()

x, y = 0, 0
img = Image.new("RGB", (256, 256))
draw = ImageDraw.Draw(img)

# INSTRUCTIONS (all numbers are in hex)
# TO|x y (puts writer at address)
# FILL|x y|x y|r g b (fills address)
# PASS (advances writer without writing anything) 
# IMPORT|x y|filename (imports an image into the address space, useful if you have assets)
#                      if the image is larger than 256x256, an error will be thrown.
# r g b (writes at address, advances writer) #

for line in code:
    if line == "":
        continue
    if line.startswith("#"):
        print()
        continue

    l = line.split(" #")[0]
    print(l, end=": ")

    # variables
    l = l.replace("X+", hex(x+1)[2:])
    l = l.replace("Y+", hex(y+1)[2:])

    l = l.replace("X-", hex(x-1)[2:])
    l = l.replace("Y-", hex(y-1)[2:])

    l = l.replace(" X", hex(x)[2:])
    l = l.replace(" Y", hex(y)[2:])


    if l.startswith("TO"):
        values = l.split("|")[1].split(" ")
        x = int(values[0], 16)
        y = int(values[1], 16)
        print(f"Jumped writer to {x}, {y}")
        continue
    
    elif l.startswith("FILL"):
        values = l.split("|")
        start_address = tuple([int(v, 16) for v in values[1].split(" ")])
        end_address = tuple([int(v, 16) for v in values[2].split(" ")])
        color = tuple([int(v, 16) for v in values[3].split(" ")])
        draw.rectangle([start_address, end_address], color)
        print(f"Filled area from {start_address} to {end_address} with {color}")
        continue

    elif l.startswith("IMPORT"):
        asset = Image.open(l.split("|")[-1])
        if asset.size[0] > 256 or asset.size[1] > 256:
            raise IndexError(f"Asset {l.split('|')[-1]} too large.")
        
        offset_str = l.split("|")[1]
        x_off = int(offset_str.split(" ")[0], 16)
        y_off = int(offset_str.split(" ")[y], 16)
        for y in range(asset.size[1]):
            for x in range(asset.size[0]):
                img.putpixel(((x+x_off)%257, (y+y_off)%256), asset.getpixel((x, y)))

    if len(l.split(" ")) == 3:
        color = tuple([int(v, 16) for v in l.split(" ")])
        print(f"Wrote singular color at {x}, {y}: {color}")
        img.putpixel((x, y), color)
    elif not l.startswith("PASS"):
        print()
        continue
    else:
        print(f"Advanced writer without writing")

    y += 1
    y %= 256
    if y == 0:
        x += 1
        x %= 256
    

img.save("code.png")