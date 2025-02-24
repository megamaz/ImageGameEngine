from PIL import Image, ImageDraw
import randomness
import sys

print("Usage:\nargv[1] = input code plaintext\nargv[2] = ouptput png path")

code = open(sys.argv[1], "r").read().splitlines()

img = Image.new("RGB", (256, 256))
draw = ImageDraw.Draw(img)

# INSTRUCTIONS
# INIT_RANDOM (sets the entire screen to be random, for fun :) (you probably want this at the start of the file if you want to put code on top))
# TO|x y (puts writer at address)
# FILL|x y|x y|r g b (fills address)
# PASS (advances writer without writing anything) 
# IMPORT|x y|filename (imports an image into the address space, useful if you have assets)
#                      if the image is larger than 256x256, an error will be thrown.
#                      supports alpha! anything other than FULLY OPAQUE will be ignored.
# r g b (writes at address, advances writer) 
# LABEL|NAME (creates labels to reference an address earlier or later in memory) 
#             used labels will refer to where they were created. creating a label acts like a PASS command.
# To use a label, use L:NAME instead of two address bytes. #
# values starting with a $ will be treated as DECIMAL
# everything else will be treated as a HEX

def get_value(string:str):
    if string.startswith("$"):
        return int(string[1:])
    else:
        return int(string, 16)

# first pass to do labels
x, y = 0, 0
label_coords = {}
for line in code:
    l = line.split("#")[0]
    l = l.strip()
    if l == "":
        continue

    if l.startswith("#"):
        continue

    if l.startswith("TO"):
        values = l.split("|")[1].split(" ")
        x = get_value(values[0])
        y = get_value(values[1])
        continue

    elif l.startswith("LABEL"):
        name = l.split("|")[1]
        label_coords[name] = (x, y)
        print(f"created label '{name}' at {hex(x)}, {hex(y)}")
    elif len(l) != 0:
        pass
    else:
        continue

    y += 1
    y %= 256
    if y == 0:
        x += 1
        x %= 256

x, y = 0, 0
for line in code:
    l = line.split(" #")[0]
    l = l.strip()

    if l == "":
        continue

    if l.startswith("#"):
        print()
        continue

    print(l, end=": ")

    if l.startswith("INIT_RANDOM"):
        img = randomness.gen_random(sys.argv[2])
        draw = ImageDraw.Draw(img)
        continue

    elif l.startswith("TO"):
        values = l.split("|")[1].split(" ")
        x = get_value(values[0])
        y = get_value(values[1])
        print(f"Jumped writer to {x}, {y}")
        continue
    
    elif l.startswith("FILL"):
        values = l.split("|")
        start_address = tuple([get_value(v) for v in values[1].split(" ")])
        end_address = tuple([get_value(v) for v in values[2].split(" ")])
        color = tuple([get_value(v) for v in values[3].split(" ")])
        draw.rectangle([start_address, end_address], color)
        print(f"Filled area from {start_address} to {end_address} with {color}")
        continue

    elif l.startswith("IMPORT"):
        asset_name = l.split("|")[-1]
        asset = Image.open(l.split("|")[-1])
        if asset.size[0] > 256 or asset.size[1] > 256:
            raise IndexError(f"Asset {l.split('|')[-1]} too large.")
        
        offset_str = l.split("|")[1]
        x_off = get_value(offset_str.split(" ")[0])
        y_off = get_value(offset_str.split(" ")[1])
        for y in range(asset.size[1]):
            for x in range(asset.size[0]):
                pixel = asset.getpixel((x, y))
                if len(pixel) == 4 and pixel[3] != 255:
                    continue

                img.putpixel(((x+x_off)%257, (y+y_off)%256), pixel)
        print(f"Imported asset {asset_name} into {x_off}, {y_off}")

    if len(l.split(" ")) == 3: # no label on this line
        color = tuple([get_value(v) for v in l.split(" ")])
        img.putpixel((x, y), color)
        print(f"Wrote singular color at {hex(x)}, {hex(y)}: {color}")
    elif "L:" in l: # line has a label
        red = get_value(l.split(" ")[0])
        coords = label_coords[l.split("L:")[1]]
        green, blue = coords
        img.putpixel((x, y), (red, green, blue))
        print(f"Wrote singular color with label at {hex(x)}, {hex(y)}: {(hex(red), hex(green), hex(blue))}")
    elif l.startswith("PASS") or l.startswith("LABEL"):
        print(f"Advancing writer without writing from {hex(x)}, {hex(y)}")
    else:
        print()
        continue

    y += 1
    y %= 256
    if y == 0:
        x += 1
        x %= 256
    

img.save(sys.argv[2])