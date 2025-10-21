from PIL import Image, ImageDraw
import randomness
import sys

print("Usage:\nargv[1] = input code plaintext\nargv[2] = ouptput png path")

code = open(sys.argv[1], "r").read().splitlines()

img = Image.new("RGB", (256, 256))
draw = ImageDraw.Draw(img)

def get_value(string:str):
    if string.startswith("$"):
        return int(string[1:])
    else:
        return int(string, 16)

# first pass to do labels
print("\n\nInitial label creation")
x, y = 0, 0
rel_x, rel_y = 0, 0
label_coords = {}
for line in code:
    l = line.split("#")[0]
    l = l.strip()
    if l == "":
        continue

    if l.startswith("#"):
        continue

    l = l.replace("X+", hex(x+1)[2:])
    l = l.replace("Y+", hex(y+1)[2:])

    l = l.replace("X-", hex(x-1)[2:])
    l = l.replace("Y-", hex(y-1)[2:])

    l = l.replace(" X", hex(x)[2:])
    l = l.replace(" Y", hex(y)[2:])

    if l.startswith("TO"):
        values = l.split("|")[1].split(" ")
        x = get_value(values[0])
        y = get_value(values[1])
        print(f"Jumped writer to {hex(x)}, {hex(y)} relative to {hex(rel_x)}, {hex(rel_y)}")
        continue

    elif l.startswith("LABEL"):
        name = l.split("|")[1]
        label_coords[name] = (x+rel_x, y+rel_y)
        print(f"Created label '{name}' at {hex(x+rel_x)}, {hex(y+rel_y)}")
    
    elif l.startswith("ATLABEL"):
        name = l.split("|")[2]
        coords = l.split("|")[1]
        xpos = get_value(coords.split(" ")[0]) + rel_x
        ypos = get_value(coords.split(" ")[1]) + rel_y
        label_coords[name] = (xpos, ypos)
        print(f"Created manual label '{name}' at {hex(xpos)}, {hex(ypos)}")
        continue

    elif l.startswith("REL"):
        values = l.split("|")[1].split(" ")
        xpos = get_value(values[0])
        ypos = get_value(values[1])
        rel_x, rel_y = xpos, ypos
        print(f"Set relative position to {hex(rel_x)}, {hex(rel_y)}")
        continue
    
    elif l.startswith("ENDREL"):
        x += rel_x
        y += rel_y
        rel_x, rel_y = 0, 0
        print(f"Ended relative mode, put pointer to {hex(x)}, {hex(y)}")
        continue

    elif l.split("|")[0] in "FILL IMPORT PATCH INIT_RANDOM INIT_GRADIENT".split(" "):
        # commands that don't advance writer, but that we don't do anything with rn
        continue

    y += 1
    y %= 256
    if y == 0:
        x += 1
        x %= 256

print("\n\nCode compilation")
x, y = 0, 0
rel_x, rel_y = 0, 0
for line in code:
    l = line.split("#")[0]
    l = l.strip()

    if l == "":
        continue

    if l.startswith("#"):
        print()
        continue

    print(l, end=": ")

    l = l.replace("X+", hex(x+1)[2:])
    l = l.replace("Y+", hex(y+1)[2:])

    l = l.replace("X-", hex(x-1)[2:])
    l = l.replace("Y-", hex(y-1)[2:])

    l = l.replace(" X", hex(x)[2:])
    l = l.replace(" Y", hex(y)[2:])

    # replace labels
    while "L:" in l:
        # get label
        try:
            contents = l.split(" ")
            label_index = [1 if k.startswith("L:") else 0 for k in contents].index(1)
            label_name = contents[label_index].split(":")[1]
            coords = label_coords[label_name]
        except ValueError:
            # label must be in between pipes
            contents = l.split("|")
            label_index = [1 if k.startswith("L:") else 0 for k in contents].index(1)
            label_name = contents[label_index].split(":")[1]
            coords = label_coords[label_name]
        # replace (label references are affected by REL)
        l = l.replace(f"L:{label_name}", f"{hex(coords[0]+rel_x)[2:]} {hex(coords[1]+rel_y)[2:]}")
        print(f"Replaced L:{label_name} with `{hex(coords[0])[2:]} {hex(coords[1])[2:]}`")


    if l.startswith("INIT_RANDOM"):
        img = randomness.gen_random(sys.argv[2])
        draw = ImageDraw.Draw(img)
        print("Replaced all pixels in image with random instructions.")
        continue

    elif l.startswith("INIT_GRADIENT"):
        for y in range(256):
            for x in range(256):
                img.putpixel((x, y), (0, x, y))
        print("Replaced all pixels in image with a UV gradient.")
        continue

    elif l.startswith("TO"):
        # we don't add the rel offset here because we're adding it everywhere else
        values = l.split("|")[1].split(" ")
        x = get_value(values[0])
        y = get_value(values[1])
        print(f"Jumped writer to {x}, {y}")
        continue
    
    elif l.startswith("FILL"):
        values = l.split("|")
        start_address = tuple([get_value(v) for v in values[1].split(" ")])
        start_address = (start_address[0]+rel_x, start_address[1]+rel_y)

        end_address = tuple([get_value(v) for v in values[2].split(" ")])
        end_address = (end_address[0]+rel_x, end_address[1]+rel_y)
        
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
        x_off = get_value(offset_str.split(" ")[0]) + rel_x
        y_off = get_value(offset_str.split(" ")[1]) + rel_y
        for y in range(asset.size[1]):
            for x in range(asset.size[0]):
                pixel = asset.getpixel((x, y))
                if len(pixel) == 4 and pixel[3] != 255:
                    continue

                img.putpixel(((x+x_off)%257, (y+y_off)%256), pixel)
        print(f"Imported asset {asset_name} into {x_off}, {y_off}")

    elif l.startswith("ATLABEL"):
        # don't advance the the writer
        # but we also don't really care about this since this was already handled
        continue

    elif l.startswith("PATCH"):
        values = l.split("|")[1].split(" ")
        x_target = get_value(values[0]) + rel_x
        y_target = get_value(values[1]) + rel_y
        color = tuple([get_value(v) for v in l.split("|")[2].split(" ")])
        img.putpixel((x_target, y_target), color)
        print(f"Replaced singular pixel at {hex(x)}, {hex(y)} with {color}")
        continue
    
    elif l.startswith("REL"):
        offsets = l.split("|")[1].split(" ")
        rel_x = get_value(offsets[0])
        rel_y = get_value(offsets[0])
        print(f"Set relative offset to {hex(rel_x)}, {hex(rel_y)}")
        continue
    
    elif l.startswith("ENDREL"):
        x += rel_x
        y += rel_y
        rel_x, rel_y = 0, 0
        print(f"Ended relative mode")

    if len(l.split(" ")) == 3: # no label on this line
        color = tuple([get_value(v) for v in l.split(" ")])
        img.putpixel((x+rel_x, y+rel_y), color)
        print(f"Wrote singular color at {hex(x)}, {hex(y)}: ({', '.join([hex(j)[2:].upper() for j in color])})")
    
    elif l.split("|")[0] in ["PASS", "LABEL"]:
        # commands that advance writer without writing
        print(f"Advancing writer without writing from {hex(x)}, {hex(y)}")
    else:
        continue

    y += 1
    y %= 256
    if y == 0:
        x += 1
        x %= 256
    

img.save(sys.argv[2])