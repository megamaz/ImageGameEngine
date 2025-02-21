from PIL import Image
import pygame
import sys
import os

code = Image.open("./code.png")

if code.size != (256, 256):
    print("Image size is not correct.")
    quit()

pointer = [0, 0]

class Environment:
    def __init__(self):
        self.space = [[(0, 0, 0),]*256 for _ in range(256)]
    
    def _initalize_space(self, image:Image.Image):
        print("Initalizing space...")
        self.reserved_keycodes = {}
        for y in range(image.size[1]):
            for x in range(image.size[0]):
                self.space[x][y] = image.getpixel((x, y))[:3]

                # reserved keycodes
                if self.space[x][y][:2] == (0xFF, 0xAE):
                    print(f"Reserving keycode {self.space[x][y][2]} at ({x}, {y})")
                    self.reserved_keycodes[self.space[x][y][2]] = (x, y)
                    self.space[x][y] = (0, 0, 0)

    
    def _get_address_offset(self, address, offset):
        orig_address = list(address)
        orig_address[0] = (orig_address[0] + ((orig_address[1] + offset)//256)) % 256
        orig_address[1] = ((orig_address[1] + offset) % 256)
        return orig_address

    def get_pixel(self, address:list, offset:int=0) -> tuple:
        orig_address = self._get_address_offset(address, offset)
        pixel = self.space[orig_address[0]][orig_address[1]] 
        # print(f"fetched pixel at {orig_address}. pixel={pixel} As instruction: {hex(pixel[0])[2:]}")
        return pixel
    
    def set_pixel(self, address:list, value:tuple):
        orig_address = self._get_address_offset(address, 0)
        self.space[orig_address[0]][orig_address[1]] = value
    
    def get_value(self, address:list) -> int:
        """Returns the value at the pixel, given that the pixel is a VALUE mode pixel.
        Assumes that the address is the 0xA0 pixel."""
        pixel = self.get_pixel(address)
        length = pixel[1]
        return self.get_variable(self._get_address_offset(address, 1), length)
    
    def get_variable(self, address, length) -> int:
        """Returns the concatenation of the given pixel as bytes.
        Assumes that the address is the pixel pointed to by the 0xA1 pixel."""
        value = b''
        for o in range(-(length//-3)):
            value += bytes([x for x in self.get_pixel(address, o)])
        
        return int.from_bytes(value)
    
    def get_value_variable(self, address):
        """Returns the value, given that the address pixel is a value / variable pixel.
        If it is neither 0xA1 or 0xA0, then nothing is returned."""
        pixel = self.get_pixel(address)
        if pixel[0] == 0xA0: # VALUE mode
            return self.get_value(address)
        
        elif pixel[0] == 0xA1: # VARIABLE mode
            target = pixel[1:]
            length = self.get_pixel(address, 1)[1]
            return self.get_variable(target, length)
        
        return 0

    def get_double_val(self, first_address) -> tuple[int, int, int]:
        """Returns a tuple containing two values, given that the address has two value / variable mode pixels in a row.
        The third item in the tuple is the offset that was necessary.
        Assumes the address is the first value / variable pixel."""
        val1 = 0
        val2 = 0
        offset_total = 0

        # check for val1 being value / variable
        pointer = self._get_address_offset(first_address, 0)
        val1_pixel = self.get_pixel(pointer)
        val1 = self.get_value_variable(pointer)
        if val1_pixel[0] == 0xA0:
            length = val1_pixel[1]
            pointer = self._get_address_offset(pointer, -(length // -3)+1)
            offset_total += -(length // -3)+1
        elif val1_pixel[0] == 0xA1:
            pointer = self._get_address_offset(pointer, 2)
            offset_total += 2
        
        # same for val2
        val2_pixel = self.get_pixel(pointer)
        val2 = self.get_value_variable(pointer)
        if val2_pixel[0] == 0xA0:
            length = val2_pixel[1]
            pointer = self._get_address_offset(pointer, -(length // -3)+1)
            offset_total += -(length // -3)+1
        elif val2_pixel[0] == 0xA1:
            pointer = self._get_address_offset(pointer, 2)
            offset_total += 2
        
        return (val1, val2, offset_total)

env = Environment()
env._initalize_space(code)

os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (50,50)
pygame.init()
screen = pygame.display.set_mode((256*4, 256*4))
screen.fill((0, 0, 0))
clock = pygame.time.Clock()

while True:
    # update the display
    # get registers

    stop = True
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            break
        
        if event.type in [pygame.KEYDOWN, pygame.KEYUP]:
            if event.key in env.reserved_keycodes.keys():
                env.set_pixel(env.reserved_keycodes[event.key], (0, 0, 0) if event.type == pygame.KEYUP else (0xFF, 0xFF, 0xFF))
                print("Reserved keycode event detected")
    else:
        stop = False
    
    if stop:
        break

    pygame.display.flip()
    # clock.tick(60)

    # instructions
    pixel = env.get_pixel(pointer)
    pointer = list(pointer)

    # NULL does nothing, no need to check for it
    # OFFSET
    if pixel[0] == 0x50:
        target = env._get_address_offset(pointer, pixel[1])
        print(f"Offset instruction by {pixel[1]}, going from {pointer} to {target}")
        pointer = target
    
    # VALUE / VARIABLE mode: we need to skip forward accordingly
    elif pixel[0] & 0xF0 == 0xA0:
        if pixel[0] & 0x01 == 0x00: # VALUE mode
            pointer[1] += pixel[1]
        
        elif pixel[0] & 0x01 == 0x01: # VARIABLE mode
            pointer[1] += 1

        print("Value / variable instruction, ignoring")

    elif pixel[0] == 0xBB or "forcefull" in sys.argv: # BLIT
        if "forcefull" not in sys.argv:
            print("Blit instruction ran")
        screen_tleft = env.space[255][254][1:]
        screen_size = env.space[254][254][1]
        debug_color = (255, 255, 255)

        to_pygame_screen_size = (screen_size*4 + 4, screen_size*4 + 4)
        if "forcefull" not in sys.argv and screen.get_size() != to_pygame_screen_size:
            print(f"Detected size change -> {screen.get_size()} -> {screen_size}")
            screen = pygame.display.set_mode(to_pygame_screen_size)

        if "forcefull" in sys.argv:
            screen_size = 256
            screen_tleft = [0, 0]

        for y in range(screen_size+1):
            for x in range(screen_size+1):
                x_coord = (x + screen_tleft[0]) % 256
                y_coord = (y + screen_tleft[1]) % 256
                screen.fill((env.space[x_coord][y_coord]), [x*4, y*4, 4, 4])
        

        if "showpointer" in sys.argv:
            pygame.draw.circle(screen, tuple([255 - x for x in env.space[pointer[0]][pointer[1]]]), [
                ((pointer[0] - screen_tleft[0])%256)*4 + 2,
                ((pointer[1] - screen_tleft[1])%256)*4 + 2], 6, width=2)

        if "forcefull" in sys.argv:
            screen_size = env.space[254][254][1]
            screen_tleft = env.space[255][254][1:]
            pygame.draw.rect(screen, debug_color, [screen_tleft[0]*4 + 2, 
                                                screen_tleft[1]*4 + 2,
                                                screen_size*4, 
                                                screen_size*4], width=2)
            
            pygame.draw.rect(screen, debug_color, [(screen_tleft[0] - 256)*4 + 2,
                                                (screen_tleft[1])*4 + 2,
                                                screen_size*4, 
                                                screen_size*4], width=2)
            
            pygame.draw.rect(screen, debug_color, [(screen_tleft[0])*4 + 2,
                                                (screen_tleft[1] - 256)*4 + 2,
                                                screen_size*4, 
                                                screen_size*4], width=2)
            
            pygame.draw.rect(screen, debug_color, [(screen_tleft[0] - 256)*4,
                                                (screen_tleft[1] - 256)*4,
                                                screen_size*4, 
                                                screen_size*4], width=2)
    elif pixel[0] == 0xB0: # WRITE
        target = pixel[1:]
        value = env.get_pixel(pointer, 1)
        env.set_pixel(target, value)
        pointer = env._get_address_offset(pointer, 1)        
        print(f"Write instruction, wrote {value} at {target}")
        

    elif pixel[0] == 0xC0: # COPY AREA
        top_left = pixel[1:]
        bottom_right = env.get_pixel(pointer, 1)[1:]
        target = env.get_pixel(pointer, 2)[1:]

        for x in range(top_left[0], bottom_right[0]):
            for y in range(top_left[1], bottom_right[1]):
                env.set_pixel(
                    (x - top_left[0] + target[0], y - top_left[1] + target[0]),
                    env.get_pixel((x - top_left[0], y - top_left[1]))
                )
    
        print(f"Copy area instruction, copied from {top_left} to {bottom_right} to {target}")
        pointer = env._get_address_offset(pointer, 2)
    
    elif pixel[0] == 0xD0: # FILL AREA
        top_left = pixel[1:]
        bottom_right = env.get_pixel(pointer, 1)[1:]
        target = env.get_pixel(pointer, 2)

        for x in range(top_left[0], bottom_right[0]):
            for y in range(top_left[1], bottom_right[1]):
                env.set_pixel(
                    (x - top_left[0] + target[0], y - top_left[1] + target[0]),
                    target
                )
    
        print(f"Fill area instruction, copied from {top_left} to {bottom_right} with {target}")
        pointer = env._get_address_offset(pointer, 2)
    
    elif pixel[0] == 0xCA:
        source = pixel[1:]
        target = env.get_pixel(pointer, 1)[1:]

        print(f"Copy instruction, copied {source} at {target}")
        env.set_pixel(target, env.get_pixel(source))

    elif pixel[0] & 0xF0 == 0x10: # IF
        target_if_false = pixel[1:]
        target_if_true = env.get_pixel(pointer, 1)[1:]
        pointer = env._get_address_offset(pointer, 2)

        val1, val2, _ = env.get_double_val(pointer)

        print(f"If instruction, mode {pixel[0]} on {val1} and {val2}")
        # different operators
        if pixel[0] == 0x1A: # EQUAL
            if val1 == val2:
                pointer = list(target_if_true)
            else:
                pointer = list(target_if_false)
            continue

        elif pixel[0] == 0x1B: # LESS THAN
            if val1 < val2:
                pointer = list(target_if_true)
            else:
                pointer = list(target_if_false)
            continue
    
    elif pixel[0] == 0xEF: # BRANCH
        target = pixel[1:]
        print(f"Branch instruction, to {target}")
        # append to stack
        for s in range(256):
            if env.space[s][255] == (0, 0, 0):
                env.set_pixel([s, 255], (0x40, pointer[0], pointer[1]))
                break
        else:
            env.set_pixel([s, 255], (0x40, pointer[0], pointer[1]))

        pointer = list(target)
        continue

    elif pixel[0] == 0x40: # GOTO
        target = pixel[1:]
        print(f"Goto instruction, to {target}")
        pointer = target
        continue

    elif pixel[0] == 0xEE: # RETURN
        # find where to return to
        for s in range(256):
            stack_val = env.space[255-s][255]
            if stack_val != (0, 0, 0):
                target = stack_val[1:]
                env.set_pixel([255-s, 255], (0, 0, 0)) 
                pointer = list(target)
                break
        else:
            pointer = [0, 0]
        
        print(f"Return instruction, returned pointed to {pointer}")
        pointer = env._get_address_offset(pointer, 1)
        continue

    elif pixel[0] & 0xF0 == 0x20: # ARITHMETIC
        target = pixel[1:]
        pointer = env._get_address_offset(pointer, 1)
        val1, val2, offset = env.get_double_val(pointer)
        result = 0
        if pixel[0] == 0x2A:
            result = val1 + val2
        
        elif pixel[0] == 0x2B:
            result = val1 * val2

        elif pixel[0] == 0x2C:
            if val2 == 0:
                result = 0
            else:
                result = val1 // val2

        b_result = result.to_bytes((len(hex(result)[2:])//2))
        b_result += b'\x00\x00\x00' # padding
        for b in range(0, len(b_result)-3, 3):
            env.set_pixel(env._get_address_offset(target, b//3), (int(b_result[b]), int(b_result[b+1]), int(b_result[b+2])))
        
        pointer = env._get_address_offset(pointer, offset)
        print(f"Arithmetic instruction -> {hex(val1)} and {hex(val2)} result {hex(result)} stored at {target}, jumped pointer to {pointer}")
        continue

    elif pixel[0] & 0xF0 == 0x30: # BITWISE
        target = pixel[1:]
        padding, horiz_offfset = env.get_pixel(pointer, 1)[1:]
        pointer = env._get_address_offset(pointer, 2)
        val1, val2, offset = env.get_double_val(pointer)
        result = 0

        if pixel[0] == 0x3A:
            result = val1 & val2
        
        elif pixel[0] == 0x3B:
            result = val1 ^ val2
        
        elif pixel[0] == 0x3C:
            result = val1 | val2
        
        b_result = result.to_bytes((len(hex(result)[2:])//2))
        b_result += b'\x00\x00\x00' # padding
        for b in range(0, len(b_result)-3, 3):
            env.set_pixel(env._get_address_offset(target, b//3), (int(b_result[b]), int(b_result[b+1]), int(b_result[b+2])))
        
        pointer = env._get_address_offset(pointer, offset)
        print(f"Bitwise instruction -> {hex(val1)} and {hex(val2)} result {hex(result)} stored at {target}, jumped pointer to {pointer}")
        continue

    # increment pointer
    pointer = env._get_address_offset(pointer, 1)

# save final state as image
state = Image.new("RGB", (256, 256))
for x in range(256):
    for y in range(256):
        state.putpixel((x, y), env.get_pixel([x, y]))

# to load, put a goto instruction as the first pixel
state.putpixel((0, 0), (0x40, pointer[0], pointer[1]))

state.save("state.png")

# ARGUMENTS
# showpointer - shows pointer
# forcefull - forces the game to show the full 256x256 area