# Image Game Engine
Welcome to Image Game Engine (IGE) where your entire game is implemented into a single image.

## How it works
You can think of the entire image as a virtual environment for your game.

Every variable, visuals, code, and even the current scene, is contained within a 256x256 image.

The image that gets rendered to the screen will depend on the registers set by the envinronment. However, it will be a part in directly within the environment. (As a result, the top of your screen will always be #503F00, otherwise screen data could be executed as code. Since the blue value is ignored, you can still get a better color, like #503FFF)

The image that gets loaded and ran is the *initial state* of the environment.

A reader pointer will then scroll through the image, top to bottom, left to right. It starts in the top left. 

The reader will always execute the current indexed pixel as code, unless previous instructions told it to treat the pixel differently.

Every pixel is split into their RGB values:
- `R` will be the instruction type.
- `G` and `B` will be treated differently depending on the instruction.

## How to code
For actually writing the code, there is a basic `to_image.py` that converts some basic instructions into the image. Check out the [ige.md](./ige.md) for how to format a plaintext file that can be compiled into an image.

This custom-made languge supports some really basic Syntax Highlighting. If you want to install this addon for VSCode, then in your VSCode terminal, enter the following command:
```
> code --install-extension ./VSCodeSyntax/ige/ige.vsix
```
Afterwards, press F1 and do "Reload Window". `.ige` files should now have syntax highlighting.

It's unlikely that this vsix changes much. It doesn't have a language server, and the highlighting is really basic.

## Using This Project
### `main.py`
The main.py runs an image as code and renders the window.
Here's how main.py expects to be run:
```
> py main.py [path to png] [parameters]
```
The available parameters for main.py are:
- `forcefull` Forcefully renders the whole 256x256 address space.
- `showpointer` Renders some additional debug info:
    - A circle to render the current pointer position
    - The copy area instruction has a green square for the source address space, and the target address space.
    - Black squares for the fill-area instruction, BITWISE, and ARITHMETIC instructions, to show where something has been written.
- `debug` Logs to the console every instruction that gets ran, as well as some info about the instruction and pointer position when relevant.
- `stepping` Pauses execution and allows you to step instruction-per-instruction through the process. To step one instruction forward, use the `]` key.
- `speed [x]` The `[x]` parameter needs to be an integer above 1. It will force the game to run at that FPS, rather than as fast as it can run. There *needs* to be a space after the word `speed` to properly parse it.

### `get_keycode.py`
Simply run it, press the key you want, and it'll print out the hex keycode in the console for you to use in your project.

### `randomness.py`
Generates a random image containing *only* instructions and saves the result to `./code.png`.

### `to_image.py`
Takes in a plaintext file that can be interpreted as ige code and generates the correct png that can then be ran as ige code. It takes in two parameters:
```
> py to_image.py [path to plaintext] [output png path]
```
It'll log to the console every instruction that gets written, and useful writer info when relevant. For how to write in this language, check out the [ige.md](./ige.md)

### `decompile.py`
Takes in an image and outputs all the pixels as a list of triple hex codes. If you find reading a bunch of assembly-like hex codes to understand a game, this could be fun for you. It could also be helpful in debugging.

Takes two parameters:
1. path to png
2. output path

The output is formatted as `address: code`. 

# Instructions
The list of instructions. They'll be written in hex (`0x00` to `0xFF`).

Parameters will be written as `R_n`, `G_n`, and `B_n`, where `n` is a number 1 or above that refers to which pixel the Green and Blue values will be read from. `n=1` refers to the same pixel where the instruction was read from, and `n=2` refers to the next pixel (unless stated otherwise). This includes `R_n` because red may sometimes be treated as a parameter.

Pixel indexing is from `0x00` to `0xFF`. (0x00, 0x00) is the top left, and (0xFF, 0xFF) is the bottom right.

An underscore in the hex value means that value will change depending on the instruction you want.

## `0x00`: Null
Not an instruction (does nothing). Should be used whenever this pixel is meant to be part of the parameter from the previous pixel (this prevents this pixel from being accidentally ran as an instruction)

## `0x50`: Offset
Ignores the next `G_1` pixels. Jumping 0 pixels makes the pointer land on where it currently is, then re-executes the offset instruction, soft-locking the proram in an infinite loop. This is to say that, whatever the pointer lands on will be executed before the pointer continues to move.

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
- `B_2`: The amount of pixel offset to start reading the value from.
    - For example, if you read from AA AA with an offset of hex 0A, you'll instead read from AA B4 (0xAA + 0x0A = 0xB4)

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
Fills a square/rectangular area with a singular color. This wraps; it starts at the "top left", and works its way down and to the right, wrapping around the screen (if needed) until it reaches the "bottom right". 
- `G_1`, `B_1`: The top left corner of the square.
- `G_2`, `B_2`: The bottom right corner of the square.
- `R_3`, `G_3`, `B_3`: The value to fill with.

## `0x1_`: If
The `If` instruction is a little weird, in that the color of the pixel actually modifies the type of `If` that'll be executed.

One thing is consistent between all of them however, and it's the fact that the first parameters are reserved for the "target address if false".
- `G_1`, `B_1`: Target address if the condition is false.
- `G_2`, `B_2`: Target address if the condition is true.

Afterwards, the instruction will parse the next pixels as either value / variable mode pixels.

### `0x1A`: Equality
Checks if two values are equal.

### `0x1B`: Less than
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
- `G_2`: Byte padding. Will add `G_2` of `B_2` bytes at the start. Is useful if you wanna store a result into the G or B of a pixel rather than the R.

Arithmetic operators are:
- `0x2A`: Add
- `0x2B`: Multiply
- `0x2C`: Euclidean division (val1 / val2) (divisions by 0 returns 0)
- `0x2D`: Subtraction (val1 - val2) (results smaller than 0 returns 0)
- `0x2E`: Modulo operator (val1 % val2) (modulo by 0 returns 0) [DEFAULT]

## `0x3_`: Bitwise operators
Works the same as arithmetic operators, but does bitwise operations instead.
- `G_1`, `B_1`: Address of the result. Data will be written as concatenated RGB pixels.
- `G_2`: Byte padding. Will add `G_2` of `B_2` bytes at the start. Is useful if you wanna store a result into the G or B of a pixel rather than the R.

Bitwise operations are:
- `0x3A`: Logical AND
- `0x3B`: Logical XOR
- `0x3C`: Logical OR
- `0x3D`: Bitshift Left (bitshifts val1 by val2)
- `0x3E`: Bitshift Right (bitshifts val1 by val2) [DEFAULT]


# Registers
These are values in memories that are edited by the machine, or change information about the environment.

## User Input
To reserve a specific pixel for user input, your initial image state should contain the following pixel:
- `(0xFF, 0xAE, 0x??)`\
Any pixel with this exact value will be detected as a **key listener** and will be updated every frame. The B value will contain the keycode. For getting the keycode hex values, you can use the `get_keycode.py` provided.

To control what value this pixel will change to when the key is released or pressed down, two additional pixels are required for setup:
- `R_1`, `G_1`, `B_1` are the `0xFF`, `0xAE`, and keycode bytes respectively.
- `R_2`, `G_2`, `B_2` is the value for when the key is PRESSED.
- `R_3`, `G_3`, `B_3` is the value for when the key is RELEASED.

These pixels are NOT reset when initalizing the state. The pixel will default to the RELEASED state.

## Mouse Input
Much like user input, you can reserve any pixel you want to be mouse input listeners. \
For mouse position, you can reserve a specific pixel by placing down `(0xFF, 0x00, 0xBB)`. This pixel will become a mouse position listener, formatted as `(0x00, X, Y)`. \
The exact `X` and `Y` position are relative to the top left of the screen. For instance, if the top left of the screen is at hex `(0xA0, 0xA0)` and the screen size is hex `0x05`, then if the mouse is in the top left of the screen, the pixel value will be `(0x00, 0xA0, 0xA0)` and if the mouse is in the bottom right of the screen, then the pixel value will be `(0x00, 0xA5, 0xA5)`.

For clicks, the listener pixel is `(0xFF, 0xBB, 0x??)`. Only three values are accepted for the click type:
- `0x0A` is left click.
- `0x0B` is right click.
- `0x0C` is middle click.

The next two pixels work the same way as keybaord inputs:
- `R_1`, `G_1`, `B_1` are the `0xFF`, `0xBB`, and mouse bytes respectively.
- `R_2`, `G_2`, `B_2` is the value for when the mouse button is PRESSED.
- `R_3`, `G_3`, `B_3` is the value for when the mouse button is RELEASED.

## Screen position
The screen position is stored in `(0xFF, 0xFE)`. The pixel is stored in the format `(0x00, X, Y)`, with the point being the top left of the screen.

## Screen Size
The screen size is stored in `(0xFE, 0xFE)`, and is stored in the format `(0x00, S, 0x00)`, with S being the square size of the screen. The screen will always be square.

## Branch Stack
Has a maximum size of 256, and uses the entire bottom row from `(0x00, 0xFF)` to `(0xFF, 0xFF)`. Each pixel is stored in the format `(0x40, X, Y)` as goto instructions.