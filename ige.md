# IGE Coding
This allows you to write code in text that can then be compiled into a png using the `to_image.py`. This isn't one that is meant to be official for this project, so if you want a better tool for this, feel free to create your own.

# Syntax
Comments start with `#` and are line specific. There are no block comments.

The code will go line by line and move the writer one pixel down relative to the image, writing the current line to the output png, then moving one pixel down.

If you want to draw a raw pixel color, then you should write three hex codes:
```
RR GG BB
```
They technically don't all have to be two characters long, but it makes the code more readable since it keeps everything aligned (if you're using a monospace font).

If you want to use decimal rather than hex, your number should start with a `$`. For example, if you want to say "goto 120 120", then you can write `40 $120 $120`. This works in both commands and raw instructions.

Then, for a bit more user control, there are some commands that you can insert. All of these should be in all caps. Each parameter is separated by a pipe (`|`). These commands only affect how the file is written to, and not how the file is ran.

## Relative Variables
In order to write stuff that is relative to the current position of the writer, you can write `X`, `Y`, followed by a singular `+` or `-`. In order to reference the *current* position of the pointer, you *need* to put a space before the `X` or `Y`.
For example, moving the pointer to its current position, you do:
```
TO| X  Y
```
This is to keep everything aligned with bytes, like so:
```
# these two are aligned
TO| X  Y
TO|FF FF
```
To reference the pixel directly ahead, you'd do
```
40  X Y+
B0 50 50
FF FF FF
# ...
```
This does not wrap around and can cause OOB errors.

## TO|XX YY
Teleports the writer to the specified location without writing anything. The next raw line will write *at* XX YY.

## FILL|X1 Y1|X2 Y2|RR GG BB
This command does not advance the writer.

Fills the entire area from X1 Y1 to X2 Y2 with a solid color. 

This can be useful if, for example, you want to prevent the screen from being executed as code, by placing an offset or goto instruction along the top of the entire screen.

## PASS
Doesn't take any parameters. This advances the writer without writing anything. Can be useful if the current address is being written to.

## IMPORT|XX YY|filename
This command doesn't advance the writer.

Imports an image, with the top left of the image being positioned at XX YY. This is useful if you want to import assets for your game.

The imported image supports alpha, and any pixel that isn't fully opaque will be skipped. So, if your pixel has even the slightest transparency, it will be skipped.

If you want to import code (as in, an image smaller than 256x256 that contains pixels that can be treated as code) then you should make use of the `PATCH`, `ATLABEL`, and `REL` commands in order to ensure that all the pixel references are correct. For instance, if you want to import code where one of the pixels is a `BRANCH` instruction like `EF 12 34` but you import the code at `A0 A0`, then the branch instruction won't jump to the right address, and the behaviour will be undefined.

Instead, if you want to import code, you'll need to have an import followed by a rel command and a series of patch and label commands, which might look something like this:
```
IMPORT|A0 A0|code.png
REL|A0 A0
ATLABEL|12 34|func_1
PATCH|00 05|EF L:func_1
# more label and patch commands...
ENDREL
```

## REL|XX YY and ENDREL
These commands don't advance the writer.

These commands are for relative instructions. It changes the top left position to be the position defined by the REL command. This is mainly useful for the `IMPORT` command, however this can also be useful for code organization.

The ENDREL command resets the relative position to be 00 00 without moving the writer. This means that if your last REL command was `REL|A0 A0` and the current writer position was `0x05 0x05`, then doing `ENDREL` would leave the writer at `A5 A5` (0xA0 + 0x05)

## PATCH|XX YY|RR GG BB
This command doesn't advance the writer.

Replaces a pixel at XX YY. This is useful if you want to write to a pixel without moving the writer to it.


## LABEL|name
This command advances the writer.

Creates a label at the current writer position. This is solely for image writing purposes. To reference a label, you do `L:name`.

Label creation line will act like a PASS command, advancing the writer without writing anything. If you want to use the LABEL creation line rather than leaving it blank, then you can follow the label creation line with the `TO| X Y-` command to move the writer one pixel up.

Labels allow you to reference the current line in an instruction. For example, say you want to create a function, but the position of the function will be different depending on the code that precedes it:
```
40 67 67
# some code...
FF FF FF
# we start our function definition here, assuming it's at 67 67.
3C 40 40
# ...
```
Then, instead of having to put a `40 67 67`, given that the `67 67` can change if you add or remove code, then you can create a label to jump directly to it, like this:
```
40 L:my_function
# some code...
FF FF FF
# our fuction definition, but since we're not sure where it is, we use a label
# we follow our label with a TO so that we don't have a wasted blank pixel
LABEL|my_function
TO| X Y-
3C 40 40 
# ...
```
Labels only place in for two bytes, and can be used anywhere. You can do some very silly stuff, like using them for the instruction, if you want to. Not sure how this can be useful, but it's a possibility if you want.
```
LABEL|weird

# ...
L:weird FF
```

All commands support label usage, except for the `TO` command. This is because the label position relies on the position of the writer, and if the position of the writer relies on a label, this creates a circular dependency.

Label references *are* affected by the REL command.

## ATLABEL|XX YY|NAME
This command does't advance the writer.

Creates a label that references a specific memory address. Everything about this label works the same as above.

This can be useful if you want to create variables. For instance, if you store a specific variable at a specific address, then instead of doing something like this:
```
TO|FF 00
01 00 00
```
Which simply sets the pixel, and then you have to keep track of it manually, you can do this:
```
ATLABEL|FF 00|my_var
PATCH|FF 00|01 00 00
```


## INIT_RANDOM
This command doesn't advance the writer.

Replaces all the pixels in the image with random pixels, for fun. Chances are this won't really have a use, but it's a good way to make sure that if the reader jumps out of bounds during execution, some interesting stuff can happen...

You should put this at the start of your file, because this replaces *all pixels in the active image* with random pixels. So if you put it at the end, all of your code will be replaced.

## INIT_GRADIENT
This command doesn't advance the writer.

Replaces all the pixels in the image with a UV gradient, useful for testing. Chances are you won't find much use for this, but it's good to know that it exists.

The red value of this UV will be set to 0 to prevent running random bits of gradient as instructions.