from PIL import Image
import custom_logger
import numpy as np
import pygame
import sys
import os

logging = custom_logger.setup_logging("_latest_interpreter.log")

code = Image.open(sys.argv[1])

if code.size != (256, 256):
    logging.error("Image size is not correct.")
    quit()

pointer = [0, 0]

forcefull = "forcefull" in sys.argv
debug = "debug" in sys.argv
showpointer = "showpointer" in sys.argv
stepping = "stepping" in sys.argv
watch = None
if "watch" in sys.argv:
    watch = []
    debug_path = sys.argv[sys.argv.index("watch")+1]
    with open(debug_path, "r", encoding="utf-8") as watch_f:
        for var in watch_f.read().splitlines():
            name = var.split(":")[0]
            address_str = var.split(":")[1].split(" ")
            address_x = int(address_str[0], 16)
            address_y = int(address_str[1], 16)
            watch.append((name, (address_x, address_y)))
    logging.info(f"Put {len(watch)} variables up for watch.")
    if not debug:
        logging.info("Log level is not debug, watch info won't be printed to console, but will be saved to file.")

speed = None
if "speed" in sys.argv:
    speed = int(sys.argv[sys.argv.index("speed")+1])

class Environment:
    def __init__(self):
        # using uint8 would be more optimal, but to prevent overflow / underflow issues, using a signed int16
        # just makes my life easier in the long run.
        self.space = np.zeros(shape=(256, 256, 3), dtype=np.int16)
    
    def _initalize_space(self, image:Image.Image):
        """Initializes the environment and returns the starting reader address."""
        logging.info("Initalizing space.")
        self.reserved_keycodes = {}
        self.mouse_pos_reserved_address = []
        self.mouse_click_reserved_address = []
        for y in range(image.size[1]):
            for x in range(image.size[0]):
                self.space[x][y] = image.getpixel((x, y))[:3]
                address = [x, y]

                # reserved keycodes
                if np.array_equal(self.space[x][y][:2], (0xFF, 0xAE)):
                    logging.debug(f"Reserving keycode {self.space[x][y][2]} ('{pygame.key.name(self.space[x][y][2])}') at ({x}, {y})")
                    self.reserved_keycodes[self.space[x][y][2]] = {
                        "address": (x, y),
                        pygame.KEYDOWN: image.getpixel(tuple(self._get_address_offset(address, 1))),
                        pygame.KEYUP: image.getpixel(tuple(self._get_address_offset(address, 2)))
                    }
                    self.space[x][y] = self.reserved_keycodes[self.space[x][y][2]][pygame.KEYUP]
                
                # reserved mouse
                if np.array_equal(self.space[x][y], (0xFF, 0x00, 0xBB)):
                    logging.debug(f"Reserving mouse position at ({x}, {y})")
                    self.mouse_pos_reserved_address.append(list(address))
                
                # mouse input
                if np.array_equal(self.space[x][y][:2], (0xFF, 0xBB)):
                    # pygame mouse input doesn't match my method
                    # 0x0A is left click, pygame button 1
                    # 0x0B is right click, pygame button 3
                    # 0x0C is middle click, pygame button 2
                    button = self.space[x][y][2]
                    if button in [0x0A, 0x0B, 0x0C]:
                        logging.debug(f"Reserving mouse click '{button}' at ({x}, {y})")
                        self.mouse_click_reserved_address.append(
                            {
                                "address":address,
                                "button":({0x0A:1, 0x0B:3, 0x0C:2})[button],
                                pygame.MOUSEBUTTONDOWN: image.getpixel(tuple(self._get_address_offset(address, 1))),
                                pygame.MOUSEBUTTONUP: image.getpixel(tuple(self._get_address_offset(address, 2)))                                
                            }
                        )
                        self.space[x][y] = self.mouse_click_reserved_address[-1][pygame.MOUSEBUTTONUP]
        
        start_value = self.space[0xFD][0xFE]
        return [start_value[1], start_value[2]]


    def _get_address_offset(self, address, offset):
        orig_address = list(address)
        orig_address[0] = (orig_address[0] + ((orig_address[1] + offset)//256)) % 256
        orig_address[1] = ((orig_address[1] + offset) % 256)
        return orig_address

    def get_pixel(self, address:list, offset:int=0) -> tuple:
        orig_address = self._get_address_offset(address, offset)
        pixel = self.space[orig_address[0]][orig_address[1]] 
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
        offset = pixel[2]
        return self.get_variable(self._get_address_offset(address, 1), length, offset)
    
    def get_variable(self, address, length, offset) -> int:
        """Returns the concatenation of the given pixel as bytes.
        Assumes that the address is the pixel pointed to by the 0xA1 pixel."""
        value = b''
        for o in range(-(length//-3)):
            value += bytes([x for x in self.get_pixel(address, o)])
        value = value[offset:offset+length]
        
        return int.from_bytes(value)
    
    def get_value_variable(self, address):
        """Returns the value, given that the address pixel is a value / variable pixel.
        If it is neither 0xA1 or 0xA0, then nothing is returned."""
        pixel = self.get_pixel(address)
        if pixel[0] == 0xA0: # VALUE mode
            return self.get_value(address)
        
        elif pixel[0] == 0xA1: # VARIABLE mode
            target = pixel[1:]
            params = self.get_pixel(address, 1)
            length = params[1]
            offset = params[2]
            return self.get_variable(target, length, offset)
        
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
    width = 1
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

def blit(rects:list=[], pause=0):
    global screen
    if pixel[0] == 0xBB:
        logging.debug("Starting blit")
    screen_tleft = env.space[255][254][1:]
    screen_size = env.space[254][254][1]

    to_pygame_screen_size = (screen_size*4, screen_size*4)
    if not forcefull and screen.get_size() != to_pygame_screen_size:
        if screen_size != 0:
            screen = pygame.display.set_mode(to_pygame_screen_size)
            logging.debug(f"Detected size change -> {screen.get_size()} -> {screen_size}")
        else:
            logging.debug("Screensize is 0, not blitting.")
            if screen.get_size() != (1, 1):
                screen = pygame.display.set_mode((1, 1))
            return

    if forcefull:
        screen_size = 256
        screen_tleft = [0, 0]

    # Courtesy of ChatGPT
    render = pygame.Surface((256, 256))
    pygame.surfarray.blit_array(render, np.clip(env.space, 0, 255).astype(np.uint8, copy=False))
    scaled_render = pygame.transform.scale(render, (1024, 1024))
    if not forcefull:
        screen.blit(scaled_render, tuple([
            screen_tleft[0]*-4 + 1024, screen_tleft[1]*-4 + 1024
        ]))
        screen.blit(scaled_render, tuple([
            screen_tleft[0]*-4, screen_tleft[1]*-4 + 1024
        ]))
        screen.blit(scaled_render, tuple([
            screen_tleft[0]*-4 + 1024, screen_tleft[1]*-4
        ]))
        screen.blit(scaled_render, tuple([n*-4 for n in screen_tleft]))
    else:
        screen.blit(scaled_render, (0, 0))

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

    # control stuff
    if speed is not None:
        clock.tick(speed)
    
    elif pause != 0:
        clock.tick(pause)
    
    pygame.display.flip()

pixel = [0, 0, 0]
pointer = [0, 0]
cycle_count = 0

env = Environment()
pointer = [int(x) for x in env._initalize_space(code)]
cycle_count = env.get_variable((0xFC, 0xFE), 3, 0)

logging.info("Setting up PyGame window info.")
os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (50,50)
pygame.init()
screen = pygame.display.set_mode((256*4, 256*4))
screen.fill((0, 0, 0))
clock = pygame.time.Clock()

if forcefull:
    blit()
    
pygame.display.flip()

logging.info("Starting main code loop.")
while True:
    pointer = list(pointer)
    pixel = env.get_pixel(pointer)
    rects = []

    if watch:
        logging.debug("Starting watch info")
        for d in watch:
            logging.debug(f"{d[0]:<15} {env.get_pixel(list(d[1]))}\n")

    # update FD,FE to current reader position
    env.set_pixel([0xFD, 0xFE], [0, *pointer])

    # instructions
    match pixel[0]:

        case 0x50: # OFFSET
            target = env._get_address_offset(pointer, pixel[1])
            logging.debug(f"Offset instruction by {pixel[1]}, going from {pointer} to {target}")
            pointer = env._get_address_offset(target, -1)
            # continue
        
        # VALUE / VARIABLE mode: we need to skip forward accordingly
        case 0xA0 | 0xA1:
            if pixel[0] & 0x01 == 0x00: # VALUE mode
                pointer[1] += -(pixel[1] // -3)
            
            elif pixel[0] & 0x01 == 0x01: # VARIABLE mode
                pointer[1] += 1
            
            pointer = env._get_address_offset(pointer, 0) # properly wrap

            logging.debug("Value / variable instruction, skipping ahead accordingly")

        case 0xBB: # BLIT
            if not forcefull: #forcefull is already rendering every frame, so this wastes time otherwise
                p_time = pixel[2]
                blit(pause=p_time)
                
        case 0xB0: # WRITE
            target = pixel[1:]
            value = env.get_pixel(pointer, 1)
            env.set_pixel(target, value)
            logging.debug(f"Write instruction, wrote {value} at {target}")
            pointer = env._get_address_offset(pointer, 1)            

        case 0xC0: # COPY AREA
            top_left = pixel[1:]
            bottom_right = env.get_pixel(pointer, 1)[1:]
            target = env.get_pixel(pointer, 2)[1:]
            mask = env.get_pixel(pointer, 3)

            vert_offset = (256 if top_left[1] > bottom_right[1] else 0)
            horiz_offset = (256 if top_left[0] > bottom_right[0] else 0)

            if showpointer and forcefull:
                # source rect
                rects.append(draw_bleeding_rect(top_left, [
                    (bottom_right[0] + horiz_offset) - top_left[0],
                    (bottom_right[1] + vert_offset) - top_left[1],
                ], (0, 255, 0)))
                # target rect
                rects.append(draw_bleeding_rect(target, [
                    (bottom_right[0] + horiz_offset) - top_left[0],
                    (bottom_right[1] + vert_offset) - top_left[1],
                ], (255, 0, 0)))

            logging.debug(f"Copy area instruction, copied from {top_left} to {bottom_right} to {target}")
            pointer = env._get_address_offset(pointer, 3)
            
            # Thank you ChatGPT for this one
            # Calculate the source area with wrapping
            src_x = np.arange(top_left[0], bottom_right[0] + horiz_offset + 1) % 256
            src_y = np.arange(top_left[1], bottom_right[1] + vert_offset + 1) % 256
            src_xx, src_yy = np.meshgrid(src_x, src_y)
            src_indices = np.stack([src_xx.ravel(), src_yy.ravel()], axis=-1)

            # Calculate the target area with wrapping
            tgt_x = (src_indices[:, 0] - top_left[0] + target[0]) % 256
            tgt_y = (src_indices[:, 1] - top_left[1] + target[1]) % 256
            tgt_indices = np.stack([tgt_x, tgt_y], axis=-1)

            # Copy the pixels
            for src, tgt in zip(src_indices, tgt_indices):
                col = env.get_pixel(src.tolist())
                if not np.array_equal(mask, col):
                    env.set_pixel(tgt.tolist(), env.get_pixel(src.tolist()))
        
        
        case 0xD0: # FILL AREA
            top_left = pixel[1:]
            bottom_right = env.get_pixel(pointer, 1)[1:]
            target = env.get_pixel(pointer, 2)

            vert_offset = (256 if top_left[1] > bottom_right[1] else 0)
            horiz_offset = (256 if top_left[0] > bottom_right[0] else 0)

            # once again, thank you ChatGPT
            # Calculate the source area with wrapping
            src_x = np.arange(top_left[0], bottom_right[0] + horiz_offset + 1) % 256
            src_y = np.arange(top_left[1], bottom_right[1] + vert_offset + 1) % 256
            src_xx, src_yy = np.meshgrid(src_x, src_y)
            src_indices = np.stack([src_xx.ravel(), src_yy.ravel()], axis=-1)

            # Fill the target area
            for src in src_indices:
                env.set_pixel(src.tolist(), target)
        
            logging.debug(f"Fill area instruction, filled {top_left} to {bottom_right} with {target}")
            pointer = env._get_address_offset(pointer, 2)
            if showpointer and forcefull:
                rects.append(draw_bleeding_rect(top_left, [
                    (bottom_right[0] + 256 if top_left[0] > bottom_right[0] else bottom_right[0]) - top_left[0],
                    (bottom_right[1] + 256 if top_left[1] > bottom_right[1] else bottom_right[1]) - top_left[1],
                ], (0, 0, 0)))
        
        case 0xCA:
            source = pixel[1:]
            target = env.get_pixel(pointer, 1)[1:]

            logging.debug(f"Copy instruction, copied {source} at {target}")
            pointer = env._get_address_offset(pointer, 1)
            env.set_pixel(target, env.get_pixel(source))

        case 0x1A | 0x1B: # IF
            target_if_false = pixel[1:]
            target_if_true = env.get_pixel(pointer, 1)[1:]
            pointer = env._get_address_offset(pointer, 2)

            val1, val2, _ = env.get_double_val(pointer)

            logging.debug(f"If instruction, mode {pixel[0]} on {val1} and {val2}")
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
            logging.debug(f"Branch instruction, to {target}")
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
            logging.debug(f"Goto instruction, to {target}")
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
            
            logging.debug(f"Return instruction, returned pointed to {pointer}")
            # pointer = env._get_address_offset(pointer, 1)
            # continue

        case 0x2A | 0x2B | 0x2C | 0x2D | 0x2E: # ARITHMETIC
            target = pixel[1:]
            padding = env.get_pixel(pointer, 1)[1]
            padding_val = env.get_pixel(pointer, 1)[2]
            pointer = env._get_address_offset(pointer, 2)
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
            elif pixel[0] == 0x2D:
                result = val1 - val2
                result = max(0, result)

            else:
                if val2 == 0:
                    result = 0
                else:
                    result = val1 % val2

            try:
                b_result = result.to_bytes((len(hex(result)[2:])//2))
            except OverflowError:
                b_result = result.to_bytes((len(hex(result)[2:])//2)+1)
            b_result += b'\x00\x00\x00' # padding
            b_result = (bytes([padding_val,]) * padding) + b_result
            for b in range(0, len(b_result)-3, 3):
                env.set_pixel(env._get_address_offset(target, b//3), (int(b_result[b]), int(b_result[b+1]), int(b_result[b+2])))
            
            pointer = env._get_address_offset(pointer, offset-1)
            logging.debug(f"Arithmetic instruction -> {hex(val1)} and {hex(val2)} result {hex(result)} stored at {target}, jumped pointer to {pointer}")
            if forcefull and showpointer:
                rects.append(draw_bleeding_rect([target[0]-2, target[1]-2], [4, len(b_result)//3+3], (0, 0, 0)))
            # continue

        case 0x3A | 0x3B | 0x3C | 0x3D | 0x3E: # BITWISE
            target = pixel[1:]
            padding = env.get_pixel(pointer, 1)[1]
            padding_val = env.get_pixel(pointer, 1)[2]
            pointer = env._get_address_offset(pointer, 2)
            val1, val2, offset = env.get_double_val(pointer)
            result = 0

            if pixel[0] == 0x3A:
                result = val1 & val2
            
            elif pixel[0] == 0x3B:
                result = val1 ^ val2
            
            elif pixel[0] == 0x3C:
                result = val1 | val2
            
            elif pixel[0] == 0x3D:
                result = val1 << val2

            else:
                result = val1 >> val2
            
            try:
                b_result = result.to_bytes((len(hex(result)[2:])//2))
            except OverflowError:
                b_result = result.to_bytes((len(hex(result)[2:])//2)+1)
            b_result += b'\x00\x00\x00' # padding
            b_result = (bytes([padding_val,]) * padding) + b_result
            for b in range(0, len(b_result)-3, 3):
                env.set_pixel(env._get_address_offset(target, b//3), (int(b_result[b]), int(b_result[b+1]), int(b_result[b+2])))
            
            pointer = env._get_address_offset(pointer, offset-1)
            logging.debug(f"Bitwise instruction -> {hex(val1)} and {hex(val2)} result {hex(result)} stored at {target}, jumped pointer to {pointer}")
            if forcefull and showpointer:
                rects.append(draw_bleeding_rect([target[0]-2, target[1]-2], [4, len(b_result)//3 + 3], (0, 0, 0)))
            # continue
            
        case 0x00:
            ...
            
        case _:
            logging.warning(f"Unrecognized opcode '{hex(pixel[0])}'")

    if forcefull:
        blit(rects)

    # pygame.display.flip()

    stop = True
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            break
        
        if event.type in [pygame.KEYDOWN, pygame.KEYUP]:
            if event.key in env.reserved_keycodes.keys():
                env.set_pixel(env.reserved_keycodes[event.key]["address"], env.reserved_keycodes[event.key][event.type])
                logging.debug("Reserved keycode event detected")
        
        if event.type == pygame.MOUSEMOTION:
            screen_tleft = env.space[255][254][1:]
            screen_size = env.space[254][254][1]
            mouse_pos = event.pos
            mouse_pos = (mouse_pos[0]//4, mouse_pos[1]//4)
            # clamp mouse pos to prevent crashes
            mouse_pos = (max(0, mouse_pos[0]), max(0, mouse_pos[1]))
            mouse_pos = (min(screen_size-1, mouse_pos[0]), min(screen_size-1, mouse_pos[1]))
            mouse_pos = (mouse_pos[0] + screen_tleft[0], mouse_pos[1] + screen_tleft[1])
            value = (0, *mouse_pos)
            for address in env.mouse_pos_reserved_address:
                env.set_pixel(address, value)
        
        if event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP]:
            logging.debug("Reserved mouse event detected")
            for button in env.mouse_click_reserved_address:
                if event.button == button['button']:
                    env.set_pixel(button['address'], button[event.type])

    else:
        stop = False
    
    if stop:
        break

    if stepping:
        pygame.event.clear()
        while True:
            event = pygame.event.wait()
            if event.type == pygame.QUIT:
                stop = True
                break
            elif event.type == pygame.KEYDOWN and event.key == pygame.key.key_code("]") or event.type == pygame.TEXTINPUT and event.text == ']':
                break
    
    if stop:
        break
    
    # increment pointer
    pointer = env._get_address_offset(pointer, 1)

    # increment cycle count
    cycle_count += 1
    cycle_bytes = cycle_count.to_bytes(3)
    env.set_pixel((0xFC, 0xFE), (cycle_bytes[0], cycle_bytes[1], cycle_bytes[2]))


# save final state as image
state = Image.new("RGB", (256, 256))
for x in range(256):
    for y in range(256):
        state.putpixel((x, y), tuple(env.get_pixel([x, y])))

state.save("state.png")

# ARGUMENTS
# showpointer - shows pointer
# forcefull - forces the game to show the full 256x256 area
# debug - shows debug logs
# stepping - lets you prace p to step forward one instruction at a time
# speed [x] - runs the program at [x] instructions per second
# watch [config] - allows you to log watch pixel information to debug