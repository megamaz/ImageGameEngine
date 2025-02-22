from PIL import Image
import pygame
import sys
import os
import numpy as np

code = Image.open("./code.png")

if code.size != (256, 256):
    print("Image size is not correct.")
    quit()

pointer = [0, 0]

forcefull = "forcefull" in sys.argv
debug = "debug" in sys.argv
showpointer = "showpointer" in sys.argv
stepping = "stepping" in sys.argv
speed = None
if "speed" in sys.argv:
    speed = int(sys.argv[sys.argv.index("speed")+1])

class Environment:
    def __init__(self):
        # using uint8 would be more optimal, but to prevent overflow / underflow issues, using a signed int16
        # just makes my life easier in the long run.
        self.space = np.zeros(shape=(256, 256, 3), dtype=np.int16)
    
    def _initalize_space(self, image:Image.Image):
        print("Initalizing space...")
        self.reserved_keycodes = {}
        for y in range(image.size[1]):
            for x in range(image.size[0]):
                self.space[x][y] = image.getpixel((x, y))[:3]

                # reserved keycodes
                if np.array_equal(self.space[x][y][:2], (0xFF, 0xAE)):
                    print(f"Reserving keycode {self.space[x][y][2]} ('{pygame.key.name(self.space[x][y][2])}') at ({x}, {y})")
                    address = [x, y]
                    self.reserved_keycodes[self.space[x][y][2]] = {
                        "address": (x, y),
                        pygame.KEYDOWN: image.getpixel(tuple(self._get_address_offset(address, 1))),
                        pygame.KEYUP: image.getpixel(tuple(self._get_address_offset(address, 2)))
                    }
                    self.space[x][y] = self.reserved_keycodes[self.space[x][y][2]][pygame.KEYUP]

    
    def _get_address_offset(self, address, offset):
        orig_address = list(address)
        orig_address[0] = (orig_address[0] + ((orig_address[1] + offset)//256)) % 256
        orig_address[1] = ((orig_address[1] + offset) % 256)
        return orig_address

    def get_pixel(self, address:list, offset:int=0) -> tuple:
        orig_address = self._get_address_offset(address, offset)
        pixel = self.space[orig_address[0]][orig_address[1]] 
        # print(f"fetched pixel at {orig_address}. pixel={pixel} As instruction: {hex(pixel[0])[2:]}")
        return pixel.copy()
    
    def set_pixel(self, address:list, value:tuple):
        # some pieces of my code don't conver oob addresses, so I have to do this here
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

def draw_bleeding_rect(tleft, size, debug_color=(255, 255, 255)):
    "size is [w, h]"
    width = 4
    def do():
        pygame.draw.rect(screen, debug_color, [tleft[0]*4 + 2, 
                                        tleft[1]*4 + 2,
                                        size[0]*4, 
                                        size[1]*4], width=width)
        
        pygame.draw.rect(screen, debug_color, [(tleft[0] - 256)*4 + 2,
                                            (tleft[1])*4 + 2,
                                            size[0]*4, 
                                            size[1]*4], width=width)
        
        pygame.draw.rect(screen, debug_color, [(tleft[0])*4 + 2,
                                            (tleft[1] - 256)*4 + 2,
                                            size[0]*4, 
                                            size[1]*4], width=width)
        
        pygame.draw.rect(screen, debug_color, [(tleft[0] - 256)*4,
                                            (tleft[1] - 256)*4,
                                            size[0]*4, 
                                            size[1]*4], width=width)

    return do

def blit(rects:list=[]):
    global screen
    if pixel[0] == 0xBB:
        print("Blit instruction ran")
    screen_tleft = env.space[255][254][1:]
    screen_size = env.space[254][254][1]

    to_pygame_screen_size = (screen_size*4 + 4, screen_size*4 + 4)
    if not forcefull and screen.get_size() != to_pygame_screen_size:
        print(f"Detected size change -> {screen.get_size()} -> {screen_size}")
        screen = pygame.display.set_mode(to_pygame_screen_size)

    if forcefull:
        screen_size = 256
        screen_tleft = [0, 0]

    # Courtesy of ChatGPT
    render = pygame.Surface((256, 256))
    pygame.surfarray.blit_array(render, env.space)
    scaled_render = pygame.transform.scale(render, (1024, 1024))
    screen.blit(scaled_render, tuple([
        screen_tleft[0]-1024, screen_tleft[1]-1024
    ]))
    screen.blit(scaled_render, tuple([
        screen_tleft[0], screen_tleft[1]-1024
    ]))
    screen.blit(scaled_render, tuple([
        screen_tleft[0]-1024, screen_tleft[1]
    ]))
    screen.blit(scaled_render, tuple(screen_tleft))

    if showpointer:
        pygame.draw.circle(screen, tuple([255 - x for x in list(env.space[pointer[0]%256][pointer[1]%256])]), [
            ((pointer[0] - screen_tleft[0])%256)*4 + 2,
            ((pointer[1] - screen_tleft[1])%256)*4 + 2], 10, width=4)

    if forcefull:
        screen_size = env.space[254][254][1]
        screen_tleft = env.space[255][254][1:]
        draw_bleeding_rect(screen_tleft, [screen_size, screen_size])()
    
    for r in rects:
        r()

pixel = [0, 0, 0]
pointer = [0, 0]

env = Environment()
env._initalize_space(code)

os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (50,50)
pygame.init()
screen = pygame.display.set_mode((256*4, 256*4))
screen.fill((0, 0, 0))
clock = pygame.time.Clock()

if not debug:
    print = lambda *x : None

blit()
pygame.display.flip()

while True:
    pointer = list(pointer)
    pixel = env.get_pixel(pointer)
    rects = []
    
    print(pointer)
    # instructions
    match pixel[0]:

        case 0x50: # OFFSET
            target = env._get_address_offset(pointer, pixel[1])
            print(f"Offset instruction by {pixel[1]}, going from {pointer} to {target}")
            pointer = env._get_address_offset(target, -1)
            # continue
        
        # VALUE / VARIABLE mode: we need to skip forward accordingly
        case 0xA0 | 0xA1:
            if pixel[0] & 0x01 == 0x00: # VALUE mode
                pointer[1] += pixel[1]
            
            elif pixel[0] & 0x01 == 0x01: # VARIABLE mode
                pointer[1] += 1

            print("Value / variable instruction, ignoring")

        case 0xBB: # BLIT
            if not forcefull: #forcefull is already rendering every frame, so this wastes time otherwise
                blit()
                
        case 0xB0: # WRITE
            target = pixel[1:]
            value = env.get_pixel(pointer, 1)
            env.set_pixel(target, value)
            print(f"Write instruction, wrote {value} at {target}")
            pointer = env._get_address_offset(pointer, 1)            

        case 0xC0: # COPY AREA
            top_left = pixel[1:]
            bottom_right = env.get_pixel(pointer, 1)[1:]
            target = env.get_pixel(pointer, 2)[1:]

            vert_offset = (256 if top_left[1] > bottom_right[1] else 0)
            horiz_offfset = (256 if top_left[0] > bottom_right[0] else 0)

            if showpointer and forcefull:
                # source rect
                rects.append(draw_bleeding_rect(top_left, [
                    (bottom_right[0] + horiz_offfset) - top_left[0],
                    (bottom_right[1] + vert_offset) - top_left[1],
                ], (0, 255, 0)))
                # target rect
                rects.append(draw_bleeding_rect(target, [
                    (bottom_right[0] + horiz_offfset) - top_left[0],
                    (bottom_right[1] + vert_offset) - top_left[1],
                ], (255, 0, 0)))

            print(f"Copy area instruction, copied from {top_left} to {bottom_right} to {target}")
            pointer = env._get_address_offset(pointer, 2)
            
            for y in range(bottom_right[1] + vert_offset - top_left[1]):
                for x in range(bottom_right[0] + horiz_offfset - top_left[0]):
                    fetch_val = env.get_pixel([(x + top_left[0])%256, (y + top_left[1])%256])
                    env.set_pixel([(x+target[0])%256, (y+target[1])%256], fetch_val)
        
        
        case 0xD0: # FILL AREA
            top_left = pixel[1:]
            bottom_right = env.get_pixel(pointer, 1)[1:]
            target = env.get_pixel(pointer, 2)

            vert_offset = (256 if top_left[1] > bottom_right[1] else 0)
            horiz_offfset = (256 if top_left[0] > bottom_right[0] else 0)

            for y in range(bottom_right[1] + vert_offset - top_left[1]):
                for x in range(bottom_right[0] + horiz_offfset - top_left[0]):
                    env.set_pixel(
                        [(x+top_left[0])%256, (y+top_left[1])%256],
                        target
                    )
        
            print(f"Fill area instruction, filled {top_left} to {bottom_right} with {target}")
            pointer = env._get_address_offset(pointer, 2)
            if showpointer and forcefull:
                rects.append(draw_bleeding_rect(top_left, [
                    (bottom_right[0] + 256 if top_left[0] > bottom_right[0] else bottom_right[0]) - top_left[0],
                    (bottom_right[1] + 256 if top_left[1] > bottom_right[1] else bottom_right[1]) - top_left[1],
                ], (0, 0, 0)))
        
        case 0xCA:
            source = pixel[1:]
            target = env.get_pixel(pointer, 1)[1:]

            print(f"Copy instruction, copied {source} at {target}")
            env.set_pixel(target, env.get_pixel(source))

        case 0x1A | 0x1B: # IF
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
                # continue

            elif pixel[0] == 0x1B: # LESS THAN
                if val1 < val2:
                    pointer = list(target_if_true)
                else:
                    pointer = list(target_if_false)
                # continue
            
            pointer = env._get_address_offset(pointer, -1)
        
        case 0xEF: # BRANCH
            target = pixel[1:]
            print(f"Branch instruction, to {target}")
            # append to stack
            for s in range(256):
                if np.array_equal(env.space[s][255], (0, 0, 0)):
                    env.set_pixel([s, 255], (0x40, pointer[0], pointer[1]))
                    break
            else:
                env.set_pixel([s, 255], (0x40, pointer[0], pointer[1]))

            pointer = list(target)
            pointer = env._get_address_offset(pointer, -1)
            # continue

        case 0x40: # GOTO
            target = pixel[1:]
            print(f"Goto instruction, to {target}")
            pointer = env._get_address_offset(target, -1)
            # continue

        case 0xEE: # RETURN
            # find where to return to
            for s in range(256):
                stack_val = env.space[255-s][255]
                if not np.array_equal(stack_val, (0, 0, 0)):
                    target = stack_val[1:]
                    pointer = list(target)
                    env.set_pixel([255-s, 255], (0, 0, 0)) 
                    break
            else:
                pointer = [0, 0]
            
            print(f"Return instruction, returned pointed to {pointer}")
            # pointer = env._get_address_offset(pointer, 1)
            # continue

        case 0x2A | 0x2B | 0x2C: # ARITHMETIC
            target = pixel[1:]
            pointer = env._get_address_offset(pointer, 1)
            val1, val2, offset = env.get_double_val(pointer)
            result = 0
            if pixel[0] == 0x2A:
                result = val1 + val2
            
            elif pixel[0] == 0x2B:
                result = val1 * val2

            # elif pixel[0] == 0x2C:
            else:
                if val2 == 0:
                    result = 0
                else:
                    result = val1 // val2

            try:
                b_result = result.to_bytes((len(hex(result)[2:])//2))
            except OverflowError:
                b_result = result.to_bytes((len(hex(result)[2:])//2)+1)
            # b_result += b'\x00\x00\x00' # padding
            for b in range(0, len(b_result), 3):
                print((int(b_result[b]), int(b_result[b+1]), int(b_result[b+2])))
                env.set_pixel(env._get_address_offset(target, b//3), (int(b_result[b]), int(b_result[b+1]), int(b_result[b+2])))
            
            pointer = env._get_address_offset(pointer, offset-1)
            print(f"Arithmetic instruction -> {hex(val1)} and {hex(val2)} result {hex(result)} stored at {target}, jumped pointer to {pointer}")
            if forcefull and showpointer:
                rects.append(draw_bleeding_rect([target[0]-2, target[1]-2], [4, len(b_result)//3+3], (0, 0, 0)))
            # continue

        case 0x3A | 0x3B | 0x3C: # BITWISE
            target = pixel[1:]
            padding, horiz_offfset = env.get_pixel(pointer, 1)[1:]
            pointer = env._get_address_offset(pointer, 2)
            val1, val2, offset = env.get_double_val(pointer)
            result = 0

            if pixel[0] == 0x3A:
                result = val1 & val2
            
            elif pixel[0] == 0x3B:
                result = val1 ^ val2
            
            # elif pixel[0] == 0x3C:
            else:
                result = val1 | val2
            
            try:
                b_result = result.to_bytes((len(hex(result)[2:])//2))
            except OverflowError:
                b_result = result.to_bytes((len(hex(result)[2:])//2)+1)
            # b_result += b'\x00\x00\x00' # padding
            for b in range(0, len(b_result), 3):
                print((int(b_result[b]), int(b_result[b+1]), int(b_result[b+2])))
                env.set_pixel(env._get_address_offset(target, b//3), (int(b_result[b]), int(b_result[b+1]), int(b_result[b+2])))
            
            pointer = env._get_address_offset(pointer, offset-1)
            print(f"Bitwise instruction -> {hex(val1)} and {hex(val2)} result {hex(result)} stored at {target}, jumped pointer to {pointer}")
            if forcefull and showpointer:
                rects.append(draw_bleeding_rect([target[0]-2, target[1]-2], [4, len(b_result)//3 + 3], (0, 0, 0)))
            # continue
            
        case _:
            print(f"Unrecognized opcode '{hex(pixel[0])}'")

    # control stuff
    if speed is not None:
        clock.tick(speed)

    if forcefull:
        blit(rects)

    pygame.display.flip()

    stop = True
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            break
        
        if event.type in [pygame.KEYDOWN, pygame.KEYUP]:
            if event.key in env.reserved_keycodes.keys():
                env.set_pixel(env.reserved_keycodes[event.key]["address"], env.reserved_keycodes[event.key][event.type])
                print("Reserved keycode event detected")
    else:
        stop = False
    
    if stop:
        break

    if stepping:
        pygame.event.clear()
        while True:
            event = pygame.event.wait()
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.key.key_code("]") or event.type == pygame.TEXTINPUT and event.text == ']':
                break
    
    # increment pointer
    pointer = env._get_address_offset(pointer, 1)

# save final state as image
state = Image.new("RGB", (256, 256))
for x in range(256):
    for y in range(256):
        state.putpixel((x, y), tuple(env.get_pixel([x, y])))

# to load, put a goto instruction as the first pixel
state.putpixel((0, 0), (0x40, pointer[0], pointer[1]))

state.save("state.png")

# ARGUMENTS
# showpointer - shows pointer
# forcefull - forces the game to show the full 256x256 area
# debug - shows debug logs
# stepping - lets you prace p to step forward one instruction at a time
# speed [x] - runs the program at [x] instructions per second