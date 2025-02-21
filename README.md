# Image Game Engine
Welcome to Image Game Engine (IGE) where your entire game is implemented into a single image.

## How it works
You can think of the entire image as a virtual environment for your game.

Every variable, visuals, code, and even the current scene, is contained within a 256x256 image.

The image that gets rendered to the screen will depend on the registers set by the envinronment. However, it will be a part in directly within the environment. (As a result, the top of your screen will always be #503F00, otherwise screen data could be executed as code. Since the blue value is ignored, you can still get a better color, like #503FFF)

The image that gets loaded and ran is the *initial state* of the environment.

## How to code
For actually writing the code, there is a basic `to_image.py` that convers some basic instructions into the image. There is a small amount of documentation telling you exactly how that wokrs inside the comments of the file near the top.

A reader pointed will scroll through the image, top to bottom, left to right. It starts in the top left. 

The reader will always execute the current indexed pixel as code, unless previous instructions told it to treat the pixel differently.

Every pixel is split into their RGB values:
- `R` will be the instruction type.
- `G` and `B` will be treated differently depending on the instruction.

# Instructions
The list of instructions. They'll be written in hex (`0x00` to `0xFF`).

Parameters will be written as `R_n`, `G_n`, and `B_n`, where `n` is a number 1 or above that referse to which pixel the Green and Blue values will be read from. `n=1` refers to the same pixel where the instruction was read from, and `n=2` refers to the next pixel (unless stated otherwise). This includes `R_n` because red may sometimes be treated as a parameter.

Pixel indexing is from `0x00` to `0xFF`. (0x00, 0x00) is the top left, and (0xFF, 0xFF) is the bottom right.

An underscore in the hex value means that value will change depending on the instruction you want.

## `0x00`: Null
Not an instruction (does nothing). Should be used whenever this pixel is meant to be part of the parameter from the previous pixel (this prevents this pixel from being accidentally ran as an instruction)

## `0x50`: Offset
Ignores the next `G_1` pixels. Should be used at the top of your screen in order to ensure that your screen isn't executed as code.

## `0x40`: Goto
Goes to the specified address.
- `G_1`, `B_1`: The address to jump to.

## `0xA_`: Value / Variable Mode
This pixel will be treated as a value, and won't be executed as any code. This comes in handy for certain instructions.

If this pixel is `0xA0`, the pixel will be treated as a VALUE, and will be read like this:
- `G_1`: The length, in bytes, of the value.
Every pixel after that will be read as a value. So if `G_1=0x04` (hex value of 4), then the value read will be the concatenation of `R_2,G_2,B_2,R_3`. This means `B_1` is ignored.

If this pixel is `0xA1`, the pixel will be treated as a VARIABLE, and will be read like this:
- `G_1`, `B_1`: The address of the variable.
- `G_2`: The length of the variable, in bytes.

## `0xB0`: Write
Writes a singular pixel value to a specific address.
- `G_1`, `B_1`: The X and Y pixel to write to.
- The second pixel will be the pixel value to write.

## `0xC0`: Copy Area
Copies an area to another area.
- `G_1`, `B_1`: The top left corner of the data to copy.
- `G_2`, `B_2`: The bottom right corner of the data to copy.
- `G_3`, `B_3`: The top left target corner.

## `0xCA`: Copy Value
Copies a singular pixel to another.
- `G_1`, `B_1`: The source pixel.
- `G_2`, `B_2`: The target pixel.

## `0xD0`: Fill area
- `G_1`, `B_1`: The top left corner of the data to copy.
- `G_2`, `B_2`: The bottom right corner of the data to copy.
- `R_3`, `G_3`, `B_3`: The value to fill with.

## `0x1_`: If
The `If` instruction is a little weird, in that the color of the pixel actually modifies the type of `If` that'll be executed.

One thing is consistent between all of them however, and it's the fact that the first parameters are reserved for the "target address if false".
- `G_1`, `B_1`: Target address if the condition is false.
- `G_2`, `B_2`: Target address if the condition is true.

Afterwards, the instruction will parse the next pixels as either value / variable mode pixels.

### `0x1A`: Equality
Checks if two values are equal.

### `0x1B`: Less than [DEFAULT]
Check if the value in `R_2` is less than (but not equal to) the value in `R_3`

## `0xBB`: Blit
Renders the screen.

## `0xEF`: Branch to
Jumps instruction to the given address, and appends the address of this instruction to the [branch stack](#branch-stack). Or rather, it searches for the right-most null value, and replaces it with the current address. If the stack is full, the last value in the stack will be overwritten.
- `G_1`, `B_1`: The address to branch to.

## `0xEE`: Return
Returns to the last executed "branch to" instruction. Or rather, it searches for the right-most non-0 pixel in the [branch stack](#branch-stack), and jumps to that address. Also sets the last element in the stack to 0. If the stack is empty, returns to (0, 0).

## `0x2_`: Arithmetic operators
This will do arithmetic. The following pixels are treated either as value / variable mode pixels, save for the first parameters which are to know where to store the result.
- `G_1`, `B_1`: Address of the result. Data will be written as concatenated RGB pixels.

Arithmetic operators are:
- `0x2A`: Add
- `0x2B`: Multiply
- `0x2C`: Euclidean division (divisions by 0 return 0) [DEFAULT]

## `0x3_`: Bitwise operators
Works the same as arithmetic operators, but does bitwise operations instead.
- `G_1`, `B_1`: Address of the result. Data will be written as concatenated RGB pixels.

Bitwise operations are:
- `0x3A`: Logical AND
- `0x3B`: Logical XOR
- `0x3C`: Logical OR [DEFAULT]


# Registers
These are values in memories that are edited by the machine, or change information about the environment.

## User Input
To reserve a specific pixel for user input, your initial image state should contain the following pixel:
- `(0xFF, 0xAE, 0x??)`\
Any pixel with this exact value will be detected as a **key listener** and will be updated every frame. The B value will contain the keycode. For getting the keycode hex values, you can use the `get_keycode.py` provided.

Once the program is running, the pixels will change, and will be stored in the format `(A, A, A)`. When A is `0x00` it means the key is up, and `0xFF` means the key is down.

## Screen position
The screen position is stored in `(0xFF, 0xFE)`. The pixel is stored in the format `(0x00, X, Y)`, with the point being the top left of the screen.

## Screen Size
The screen size is stored in `(0xFE, 0xFE)`, and is stored in the format `(0x00, S, 0x00)`, with S being the square size of the screen. The screen will always be square.

## Branch Stack
Has a maximum size of 256, and uses the entire bottom row from `(0x00, 0xFF)` to `(0xFF, 0xFF)`. Each pixel is stored in the format `(0x40, X, Y)` as goto instructions.