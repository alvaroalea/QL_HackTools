
# QL SuperBASIC — Knowledge & Programming Techniques Extracted from QBITSProgs_v1

## Purpose

This document is a **knowledge base for an LLM that must program in Sinclair QL SuperBASIC/SBASIC**.

It condenses the programming practices, idioms, algorithms, compatibility notes, graphics techniques, file handling, memory tricks, keyboard handling, font manipulation, timing, sound, 3D graphics and program-structure patterns demonstrated in **QBITSProgs_v1.pdf — *QL Retro Computing: A Collection of Progs written in QL SuperBASIC***.

The source collection consists of many real SuperBASIC programs, revised over several years and tested primarily with QPC/QPC2-era environments. It explicitly notes that some programs require Toolkit II or later/extended environments, while the original QL has much tighter memory and performance limits.

### Important interpretation rule

When generating code:

1. Prefer **real QL SuperBASIC syntax** over modern BASIC dialects.
2. Distinguish **original QL/SuperBASIC** features from **Toolkit II, SMSQ/E, QPC or other extensions**.
3. Do not assume that a keyword exists on an unexpanded original QL merely because it appears in QBITS programs.
4. When portability matters, use the source's pattern of defensive coding with `WHEN ERRor`, defaults, and capability detection.
5. Preserve QL idioms such as `DEFine PROCedure`, `REPeat`, `SELect ON`, `DATA`, `READ`, `RESTORE`, channels, `WINDOW`, `CURSOR`, `BLOCK`, `LINE`, `PEEK`/`POKE`, etc.
6. Do not silently translate QL concepts into Sinclair ZX Spectrum, BBC BASIC, Commodore BASIC or modern BASIC syntax.

---

# 1. QL SuperBASIC mental model

SuperBASIC is an interpreted language closely integrated with the QL operating system.

The most useful conceptual groups are:

- **Sequencing** — statements execute in order.
- **Variables** — numeric and string values.
- **Input/output** — keyboard, screen, files and channels.
- **Conditions** — `IF`, `ELSE`, `SELect ON`.
- **Iteration** — `FOR`, `REPeat`.
- **Procedures/functions** — reusable named blocks.
- **Data tables** — `DATA`, `READ`, `RESTORE`.
- **Graphics** — windows, cursor positioning, blocks and vector drawing.
- **Direct memory** — `PEEK`, `POKE`, word operations and allocated memory.
- **QL device I/O** — files are normally accessed through named channels and QL device names.

A useful LLM should think of SuperBASIC as a small operating-system-aware language rather than merely a generic BASIC.

---

# 2. Program structure

A robust QBITS-style program normally begins with:

1. A `REMark` identifying the program/version.
2. Default device and display settings.
3. Global configuration variables.
4. Arrays and constants.
5. Optional error handling.
6. Initialization procedures.
7. Main program call.
8. Procedure/function definitions.

Typical pattern:

```basic
100 REMark PROGRAM_NAME_bas
110 MODE 4
120 WINDOW 512,256,0,0
130 PAPER 0:BORDER 1,3:INK 7:CLS
140 WHEN ERRor :CONTINUE:END WHEN
150 Init_Win
160 Main
```

The exact order can vary, but the important idea is to make initialization explicit and keep the main program easy to find.

QBITS frequently uses line-number ranges to group related functionality, although SuperBASIC procedure structure is more important than the actual numbers.

---

# 3. Naming conventions

QBITS uses short, descriptive names adapted to the constraints and style of QL programming.

Typical meanings:

- `x,y` — coordinates.
- `gx,gy` — global screen/window offsets.
- `i,j,k` — loop/index variables.
- `%` suffix — integer-oriented variable.
- `$` suffix — string.
- `dev$` — current device.
- `Drv$()` — array of device names.
- `DD$` — device/directory path.
- `SD$` — subdirectory.
- `Fn$` / `df$` — filename/data file.
- `ic%`, `icol` — ink colour.
- `bcol` — background/paper colour.
- `pcol` — pixel/print colour.
- `old`/`ocol` — previous colour.

Good practice demonstrated in the source:

- Define important variables near the beginning.
- Put default settings together.
- Use `REMark` to explain non-obvious variables.
- Keep names short enough to remain readable on a QL program listing.
- Avoid relying on implicit/uninitialized values.

---

# 4. Arrays and DATA tables

Arrays are heavily used for:

- lookup tables;
- game boards;
- coordinates;
- fonts;
- calendars;
- sounds;
- menus;
- records;
- 3D nodes;
- resource tables.

Prefer defining array dimensions near initialization:

```basic
DIM Grid(3,3)
DIM x(8),y(8),z(8)
DIM vx(8),vy(8)
DIM Name$(20)
```

`DATA` is an important SuperBASIC technique. It is effectively a compact embedded data store.

Pattern:

```basic
RESTORE 1000
FOR i=1 TO 12
    READ Month$(i),Days(i)
END FOR i

1000 DATA 'JAN',31,'FEB',28,'MAR',31
```

This is particularly useful for fixed tables because it avoids complicated initialization code.

The source uses `RESTORE` to switch between different DATA tables in the same program.

### Important idiom

A `FOR` loop plus `READ`/`DATA` can act as a compact table loader:

```basic
RESTORE table_start
FOR i=1 TO n
    READ a(i),b(i),c(i)
END FOR i
```

It is also useful for geometry: a list of coordinates can describe nodes, edges or frames.

---

# 5. Strings and formatting

Useful source-derived idioms:

### Fixed-width strings

```basic
PRINT FILL$(' ',width-LEN(str$))&str$
```

This right-aligns a string in a fixed field.

### Zero-padded numbers

```basic
PRINT FILL$('0',4-LEN(n%))&n%
```

Useful for counters such as `0001`, `0042`, etc.

### Extracting part of a string

Use substring notation:

```basic
s$(a TO b)
```

This is frequently combined with `LEN`, `INSTR`, `CHR$` and `CODE`.

### Searching strings

```basic
IF 'pattern' INSTR filename$ > 0 THEN ...
```

The QBITS programs also use `INSTR` to detect suffixes, decimal points, filenames and device strings.

### Character conversion

Use:

```basic
CODE(char$)
CHR$(code)
```

This is especially important for keyboard input and font handling.

---

# 6. Screen architecture: WINDOWS and channels

A major SuperBASIC technique is to treat the screen as several independent **WINDOWs/channels**.

Instead of drawing everything in one area, QBITS commonly creates:

- a background channel;
- a main application channel;
- a menu/status channel;
- an information or input channel.

Example pattern:

```basic
OPEN#2,scr_
WINDOW#2,512,224,gx,gy
PAPER#2,0
BORDER#2,1,3
CLS#2

OPEN#1,scr_
WINDOW#1,274,200,gx+224,gy+12
PAPER#1,0
BORDER#1,1,3
CLS#1

WINDOW#0,512,32,gx,gy+224
```

The exact dimensions depend on the application.

### Why this is powerful

It lets the program:

- keep a permanent background;
- redraw only the active area;
- isolate menus;
- place status information at the bottom;
- use different colours/settings per channel;
- clear a local area without destroying the entire interface.

Whenever appropriate, code should use `#channel` versions of graphics/output commands:

```basic
PRINT#ch,...
CURSOR#ch,...
INK#ch,...
PAPER#ch,...
LINE#ch,...
CIRCLE#ch,...
BLOCK#ch,...
```

---

# 7. WINDOW, SCALE and graphic coordinates

`WINDOW` defines the drawable region.

`SCALE` defines the graphics coordinate system used by vector graphics.

Common pattern:

```basic
WINDOW 512,200,0,0
SCALE 100,0,0
```

QBITS often uses a logical coordinate system instead of depending on raw physical pixel positions.

This makes procedures reusable:

```basic
DEFine PROCedure Shape(ch,x,y)
    ...
END DEFine
```

where `x,y` are the logical centre/anchor point.

### Coordinate discipline

For reusable graphics:

- choose an anchor point;
- express all shape components as offsets from it;
- use `SCALE` to fit the design;
- keep screen/window offsets separate from object coordinates.

This is much easier to maintain than hard-coding every screen position independently.

---

# 8. Text rendering tricks

`CURSOR` is more flexible than simple line/column positioning.

It can position output in the graphics coordinate system.

Useful pattern:

```basic
CURSOR x,y
PRINT str$
```

The source also demonstrates that `OVER` can create simple shadows/bold/3D effects.

### Simple string shadow/bold

```basic
INK col
CURSOR x,y
PRINT str$

OVER 1
CURSOR x,y+1
PRINT str$
OVER 0
```

Another technique is printing a string twice with a small horizontal offset.

For more elaborate title text, the source prints character-by-character with progressively offset `CURSOR` positions.

### `CSIZE`

`CSIZE` changes character dimensions.

Be careful with very tall character sizes near the bottom of a window: the source explicitly notes that large character heights can interfere with subsequent output.

---

# 9. OVER

`OVER` is useful for:

- shadows;
- bold text;
- highlighting;
- XOR-like graphical effects;
- temporarily drawing selection boxes.

Example:

```basic
OVER 1
LINE x1,y1 TO x2,y2 TO x3,y3 TO x1,y1
OVER 0
```

A useful menu highlight pattern is:

1. draw a rectangle;
2. toggle it with `OVER`;
3. redraw when selection moves.

---

# 10. BLOCK as a UI primitive

`BLOCK` is one of the most useful QL-specific drawing operations.

Use it for:

- clearing an area;
- drawing solid rectangular panels;
- menu highlights;
- button backgrounds;
- simulating missing printable characters;
- erasing an old object before redrawing.

Example:

```basic
BLOCK#ch,w,h,x,y,col
```

The source uses `BLOCK` extensively for UI construction.

A common pattern is:

```basic
BLOCK x,y,w,h,background
```

followed by text or graphics.

---

# 11. LINE, FILL, CIRCLE and ARC

The source uses vector graphics heavily.

### LINE

Polylines are useful for:

- boxes;
- icons;
- wireframes;
- stylized characters;
- decorative borders;
- game pieces.

Pattern:

```basic
LINE x1,y1 TO x2,y2 TO x3,y3 TO x1,y1
```

### FILL

The source warns that filling a complex shape is not necessarily equivalent to filling an arbitrary polygon in a modern graphics library.

For reliable solid shapes, split complicated objects into simpler closed regions.

Example:

```basic
FILL 1
LINE x1,y1 TO x2,y2 TO x3,y3 TO x1,y1
FILL 0
```

The source specifically notes that the fill behaviour associated with `LINE` works through horizontal pixel spans between line limits, so complicated forms may need to be constructed from multiple shapes.

### CIRCLE

Useful for:

- counters;
- game pieces;
- eyes;
- interface controls.

### ARC

Useful for:

- curved objects;
- stylized animals/characters;
- rounded interface elements;
- complex illustrations.

A good reusable-graphics technique is to combine several `ARC`, `LINE`, `CIRCLE` and `FILL` operations around one `(x,y)` anchor.

---

# 12. Keyboard input

The QBITS menu architecture is highly reusable.

A typical event loop:

```basic
REPeat loop
    k=CODE(INKEY$(-1))

    SELect ON k
        =192: ...
        =200: ...
        =208: ...
        =216: ...
        =10: ...
        =27: ...
    END SELect
END REPeat loop
```

The source commonly maps QL cursor keys to numeric key codes:

- left: `192`
- right: `200`
- up: `208`
- down: `216`

Other commonly used values include:

- Enter: `10`
- Escape: `27`
- Space: `32`

Letter actions are often handled by testing several ASCII values:

```basic
=81,113: ...
```

This allows uppercase/lowercase `Q` to perform the same action.

### Important UI idiom

Use cursor keys for navigation and:

- Space = select/action;
- Enter = alternative action;
- Esc = exit;
- letter keys = shortcuts.

This pattern appears throughout the collection.

---

# 13. INKEY$ and timed polling

`INKEY$` can be used for event loops and polling.

The source demonstrates both:

```basic
k=CODE(INKEY$(-1))
```

and timed input:

```basic
k=CODE(INKEY$(FDelay))
```

This is useful for:

- games;
- menus;
- animation;
- timers;
- random generators;
- keyboard-controlled simulations.

A timed input loop avoids blocking forever waiting for a key.

---

# 14. REPeat loops

`REPeat` is a central SuperBASIC construct for application/game loops.

Pattern:

```basic
REPeat main_loop

    ...

    IF done
        EXIT main_loop
    END IF

END REPeat main_loop
```

Naming the loop makes it possible to leave a specific nested loop:

```basic
EXIT Menu_lp
```

The source notes compatibility issues around nested `REPeat`/`END REPeAT` structures on some environments, so clear naming and disciplined nesting are preferable.

---

# 15. FOR loops

Use `FOR` for deterministic iteration and array/table traversal.

```basic
FOR i=1 TO n
    ...
END FOR i
```

Nested loops are common:

```basic
FOR r=1 TO rows
    FOR c=1 TO cols
        ...
    END FOR c
END FOR r
```

The source uses this extensively for:

- game grids;
- DATA loading;
- fonts;
- files;
- geometry;
- screen rendering.

The PDF also mentions historical compatibility problems with integer variables in `FOR` loops on some QL environments. When maximum compatibility is required, test code on the intended interpreter/emulator rather than assuming every implementation behaves identically.

---

# 16. SELect ON

`SELect ON` is one of the best ways to implement keyboard dispatch.

Pattern:

```basic
SELect ON k
    =192: ...
    =200: ...
    =208: ...
    =216: ...
    =32: ...
    =27: ...
END SELect
```

Multiple values can be grouped:

```basic
=27,69,101: ...
```

The source uses this to support Escape plus alternative exit keys and uppercase/lowercase letters.

---

# 17. Procedures

Use procedures to isolate UI, drawing and logic.

Pattern:

```basic
DEFine PROCedure DrawBox(ch,x,y,w,h,col)
    ...
END DEFine
```

Local variables should be declared when needed:

```basic
DEFine PROCedure Something
    LOCal x1,y1,x2,y2
    ...
END DEFine
```

A strong QBITS-style architecture is:

```text
Initialisation
    |
    +-- Init_Win
    +-- Init_Data
    +-- Init_Fonts
    |
Main loop
    |
    +-- Input
    +-- Update
    +-- Draw
    |
Exit
    |
    +-- Close channels
    +-- Release memory
    +-- LRUN return program
```

---

# 18. RETURN and early exits

Procedures frequently use:

```basic
RETurn
```

to abandon the current operation after a failed condition.

Example pattern:

```basic
IF error_flag
    RETurn
END IF
```

This is useful for keeping deeply nested UI/file code manageable.

---

# 19. Error handling and compatibility

One of the most important compatibility techniques in the source is:

```basic
WHEN ERRor
    CONTINUE
END WHEN
```

This is used to allow programs to continue when optional environment-dependent keywords are unavailable.

A typical compatibility strategy is:

```basic
scrbase=131072
llen=128
scrmode=4

WHEN ERRor
    CONTINUE
END WHEN

scrbase=SCR_BASE
llen=SCR_LLEN
xlim=SCR_XLIM
scrmode=llen/xlim*16
```

The idea is:

- establish safe original-QL defaults first;
- attempt to obtain enhanced-platform information;
- if the keywords do not exist, retain the defaults.

Do not use this indiscriminately. Error trapping can hide genuine programming errors. Use it mainly around optional platform features.

---

# 20. Original QL memory/screen assumptions

The source uses the original QL defaults:

- screen base: `131072`;
- screen line length: `128` bytes;
- screen width: `512` pixels;
- screen height: approximately `256` pixels;
- Mode 4 as the classic default.

The original QL is described as having 128K RAM, with about 32K occupied by the screen, leaving much less memory for the interpreter and application.

This is why direct memory manipulation and careful data structures matter.

---

# 21. Detecting extended screen modes

For platforms exposing:

```basic
SCR_BASE
SCR_LLEN
SCR_XLIM
SCR_YLIM
```

the source derives a mode value using:

```basic
scrmode=SCR_LLEN/SCR_XLIM*16
```

The intended results in the documented scheme are:

- 4
- 16
- 32

A portable routine therefore follows this principle:

```basic
DEFine PROCedure QLScrMode
    scrbase=131072
    llen=128
    xlim=512
    ylim=256
    scrmode=4

    scrbase=SCR_BASE
    llen=SCR_LLEN
    xlim=SCR_XLIM
    ylim=SCR_YLIM
    scrmode=llen/xlim*16
END DEFine
```

with suitable error trapping if those keywords may be absent.

---

# 22. Screen MODE 4 / MODE 8 concept

The source describes the classic QL display representation:

- Mode 4: four colours, 512-pixel horizontal resolution.
- Mode 8: eight colours, 256-pixel horizontal resolution.

It also discusses later QL-compatible platforms with 16- and 32-bit colour formats.

For a program intended for a real original QL, do not assume the later high-colour modes.

The original QL palette is described as:

1. black
2. blue
3. red
4. magenta
5. green
6. cyan
7. yellow
8. white

---

# 23. Direct screen-memory access

The source uses allocated memory plus `PEEK`, `POKE`, `PEEK_W` and `POKE_W` for fast data manipulation.

Example pattern:

```basic
base=ALCHP(size)
...
POKE base+offset,value
...
RECHP base
```

Word operations are particularly useful for QL screen data.

The source's screen saver copies screen memory with a structure equivalent to:

```basic
FOR y=0 TO h-1
    FOR b=0 TO bw-1 STEP 2
        POKE_W dest+10+y*bw+b,PEEK_W(scrbase+llen*(y+screen_y)+screen_x+b)
    END FOR b
END FOR y
```

The important technique is:

**calculate a base address once, then use offsets rather than repeatedly calculating complete addresses.**

---

# 24. Memory allocation

The source uses:

```basic
ALCHP(n)
```

to allocate memory from the common heap.

After use:

```basic
RECHP address
```

releases it.

For binary data, allocate enough space before `LBYTES`:

```basic
addr=ALCHP(size)
LBYTES filename$,addr
```

Then release:

```basic
RECHP addr
```

### Important discipline

Every temporary `ALCHP` allocation should have a clearly defined lifetime and matching `RECHP`.

Do not keep large allocations around unnecessarily on a real 128K QL.

---

# 25. SBYTES and LBYTES

The source uses:

- `LBYTES` to load binary data into memory.
- `SBYTES` to save memory contents as a binary file.

Typical load:

```basic
addr=ALCHP(size)
LBYTES dev$&filename$,addr
```

Typical save:

```basic
SBYTES dev$&filename$,addr,size
RECHP addr
```

This is much more appropriate for binary resources than using text `INPUT#`/`PRINT#`.

The source explicitly notes that direct allocated memory combined with `PEEK`/`POKE` can speed up storage operations.

---

# 26. Font memory manipulation

The source gives a particularly useful model of QL fonts.

With Toolkit II-style font handling:

```basic
FBase1=ALCHP(876)
LBYTES device$&fontfile$,FBase1

FBase2=ALCHP(588)
LBYTES device$&fontfile$,FBase2

CHAR_USE#ch,FBase1,FBase2
```

The font structures contain:

- initial ASCII character code;
- number/count information;
- repeated 9-byte character blocks.

Each character is represented as a 9-byte block corresponding to a 9×8 bitmap structure.

The actual bitmap can then be manipulated with `PEEK` and `POKE`.

This is a key technique for:

- custom fonts;
- arcade-style graphics;
- bitmap character editors;
- modifying characters at runtime.

The source stresses that font allocation sizes should be rounded to even values so `LBYTES` can be used properly.

---

# 27. 8×8 bitmap font conversion

The source also demonstrates handling external 8×8 bitmap fonts.

The important conversion strategy is:

1. Load the raw 8-byte-per-character bitmap.
2. Allocate QL font memory.
3. Copy each group of 8 bytes into the QL font structure.
4. Add the ninth byte required by the QL font layout.
5. Assign the result using `CHAR_USE`.
6. Save/repackage as a QL font file if required.

Conceptual loop:

```basic
FOR char=0 TO count-1
    qlbase=fontbase+2+(offset+char)*9
    bitmapbase=rawbase+char*8

    FOR row=0 TO 7
        POKE qlbase+row,PEEK(bitmapbase+row)
    END FOR row

    POKE qlbase+8,0
END FOR char
```

This is one of the most reusable pieces of knowledge in the collection.

---

# 28. File/device naming

QL file paths are device-prefixed.

Examples used in the source include:

```text
mdv1_
mdv2_
flp1_
flp2_
win1_
win2_
dos1_
dos2_
```

A program can keep the device separate from the filename:

```basic
dev$='win1_'
filename$='MyFile_bas'
full$=dev$&filename$
```

This makes it much easier to redirect a program to another storage device.

---

# 29. Configuration files

QBITS uses a simple configuration-file technique.

Write several values with:

```basic
OPEN_NEW#9,dev$&'QBITSConfig'
PRINT#9,gx\gy\dn$\dev$\dn%\dm%
...
CLOSE#9
```

Read them with:

```basic
OPEN_IN#9,dev$&'QBITSConfig'
INPUT#9,gx\gy\dn$\dev$
CLOSE#9
```

Backslash-separated values are therefore a useful QBITS idiom for compact structured text files.

---

# 30. OPEN / OPEN_NEW / OPEN_IN

Typical meanings:

```basic
OPEN#ch,file$
OPEN_NEW#ch,file$
OPEN_IN#ch,file$
```

Use `OPEN_NEW` when creating/overwriting a new output file.

Use `OPEN_IN` for reading.

Always close the channel:

```basic
CLOSE#ch
```

The source often uses channel `#99` for temporary file operations.

---

# 31. EOF and sequential file reading

The source demonstrates a useful directory/file scan pattern:

```basic
OPEN_IN#99,tempfile$

REPeat read_loop
    IF EOF(#99)
        CLOSE#99
        EXIT read_loop
    END IF

    INPUT#99,line$
    ...
END REPeat read_loop
```

This is a good general model for sequential text-file processing.

---

# 32. Directory handling

The QBITS file manager demonstrates:

```basic
DIR#channel,device$
```

combined with temporary files to obtain directory information.

The general technique is:

1. create a temporary listing file;
2. run `DIR#` into it;
3. open it for input;
4. read entries;
5. process/sort them;
6. delete the temporary file.

The source also uses directory/subdirectory naming conventions ending in `_`.

---

# 33. Sorting file lists

The file manager builds a filename array and uses loops to reorder entries alphabetically.

A general SuperBASIC approach is:

- read all names into an array;
- compare two names;
- swap them;
- repeat until ordered.

This is deliberately simple and appropriate for small QL-era datasets.

Do not assume modern library sorting functions exist.

---

# 34. Wildcard/file-manager strategy

The source's file manager supports wildcard searching.

A reusable design is:

```text
select device
    ↓
select directory/subdirectory
    ↓
obtain directory listing
    ↓
filter filenames
    ↓
sort results
    ↓
display selectable list
    ↓
perform operation on selected filename
```

This architecture is useful for any QL utility requiring file selection.

---

# 35. Screen saver / PIC format technique

The source defines a compact screen-image format with a **10-byte header** followed by image data.

The documented header contains:

- magic/header identifier;
- pixel width;
- pixel height;
- bytes per row;
- screen mode.

The source writes the header with `POKE_W` and `POKE`.

Conceptual layout:

```text
offset +0  : header ID
offset +2  : width
offset +4  : height
offset +6  : bytes per row
offset +8  : screen mode
offset +10 : image data
```

This is a good example of designing a compact binary file format in SuperBASIC.

---

# 36. Screen-image size calculation

For the documented modes:

```text
classic 4/8 representation:
    bytes_per_row = ((width + 7) DIV 8) * 2

mode 16:
    bytes_per_row = width

mode 32:
    bytes_per_row = width * 2
```

The source also uses a horizontal scaling factor so a logical pixel coordinate can be translated into the storage representation.

This is useful when writing screen grabbers/viewers.

---

# 37. Graphics design methodology

The source recommends designing graphics on a grid first.

For a reusable object:

1. sketch the object;
2. identify its horizontal/vertical dimensions;
3. select an anchor point;
4. express every component as an offset;
5. implement with `LINE`, `ARC`, `CIRCLE`;
6. use `FILL` for enclosed regions;
7. tune `SCALE`;
8. test at the intended screen size.

This leads naturally to procedures such as:

```basic
DEFine PROCedure Bear(ch,x,y)
...
END DEFine
```

or:

```basic
DEFine PROCedure Bull(ch,x,y)
...
END DEFine
```

The source contains many examples of this style.

---

# 38. Games: separate state from display

The game programs demonstrate a useful architecture:

```text
Game state arrays
      ↓
Input handling
      ↓
State update
      ↓
Collision/win/check logic
      ↓
Graphics update
      ↓
Score/status update
```

For example, Tic-Tac-Toe stores board state separately from the graphics.

This is preferable to using the screen itself as the program's database.

---

# 39. Grid games

A grid can be represented as:

```basic
DIM Grid(rows,cols)
```

with a simple state convention, for example:

```text
0 = empty
79 = O
88 = X
```

The exact values are application-dependent.

Selection is represented by row/column variables:

```basic
c=...
r=...
```

and screen position calculated from them:

```basic
x=base_x+c*cell_width
y=r*cell_height
```

This is a general and efficient QL game technique.

---

# 40. Win-condition tables

The Tic-Tac-Toe program avoids complicated nested conditionals by putting the eight winning combinations into `DATA`.

Then:

```basic
FOR i=1 TO 8
    READ a,b,c,r,d,e
    IF Grid(a,b)=n AND Grid(c,r)=n AND Grid(d,e)=n
        ...
    END IF
END FOR i
```

This is an important general trick:

**Represent combinations/rules as DATA instead of hard-coding each case.**

The same approach works for:

- board games;
- card games;
- maze connections;
- 3D wireframe edges;
- animation frames;
- lookup tables.

---

# 41. Random selection

The source uses:

```basic
RND(1 TO n)
```

for random integer selection.

A useful pattern is repeatedly choosing until a constraint is satisfied:

```basic
REPeat choose_loop
    n=RND(1 TO max)

    IF condition_is_valid
        EXIT choose_loop
    END IF
END REPeat choose_loop
```

This is used in the Galaxy program for selecting a star system based on game state.

---

# 42. Timers and DATE

The source uses `DATE` as a timing source.

One documented technique calibrates the number of loop iterations corresponding to a 20 ms timer interval:

```basic
sd=DATE
REPeat Chk_lp
    IF sd<>DATE
        sd=DATE
        EXIT Chk_lp
    END IF
END REPeat Chk_lp

FOR tc=1 TO 1E15
    IF sd<>DATE
        EXIT tc
    END IF
END FOR tc

ms=tc/50
```

Then a delay procedure can use a calibrated loop count.

The exact calibration depends on the environment and should not be treated as a universal CPU-independent timer.

---

# 43. Sound and BEEP

The source explores QL `BEEP` attributes for:

- duration;
- pitch;
- harmonics;
- timing;
- articulation;
- effects.

A musical program can represent notes as records/arrays instead of hard-coding every `BEEP`.

The QLSounds section uses arrays such as:

```text
Bkey(kn%,kp%)
```

where fields represent properties including:

- duration;
- pitch;
- harmonic;
- time interval;
- step;
- warp;
- fuzzy;
- random.

This demonstrates a general data-driven approach to sound programming.

---

# 44. Sound timing

The source warns that `PAUSE` and some timer approaches can be tied to system timing characteristics.

For more controlled musical timing, it uses the QL clock `DATE` and a calibrated delay procedure.

General principle:

**Separate note data from the timing engine.**

For example:

```text
note data → duration/pitch/etc.
timing engine → waits correct interval
player → sends BEEP
```

This makes the player easier to modify.

---

# 45. QPC/SMSQ/E compatibility

The source was primarily developed/tested with QPC/QPC2-era environments.

It explicitly notes:

- QPC is much faster than an original interpreted QL.
- SMSQ/E can be more tolerant of unassigned variables than older ROMs.
- Some constructs behave differently between environments.
- Some keywords are Toolkit II or later additions.
- Extended memory may be required.

Therefore:

### For original QL compatibility

Prefer:

- classic SuperBASIC syntax;
- small arrays;
- modest windows;
- direct memory only when justified;
- minimal allocations;
- no dependency on later keywords unless explicitly required.

### For QPC/SMSQ/E

You may exploit:

- larger memory;
- faster execution;
- higher screen modes;
- additional keywords;
- larger applications.

But explicitly label such dependencies.

---

# 46. Performance philosophy

The source repeatedly emphasizes that interpreted SuperBASIC on original hardware can be slow.

For performance-sensitive code:

1. Move repeated calculations outside inner loops.
2. Use arrays rather than repeatedly parsing strings.
3. Use direct memory access where justified.
4. Use `PEEK_W`/`POKE_W` for word-oriented data.
5. Use `LBYTES`/`SBYTES` for binary blocks.
6. Avoid unnecessary screen redraws.
7. Redraw only the changed region.
8. Use separate windows to limit clearing.
9. Keep game state independent from rendering.
10. Compile when the environment permits and speed is critical.

The source notes that QPC/emulation can be dramatically faster than an original interpreted QL.

---

# 47. Avoiding unnecessary redraws

A useful QL-era optimization is to erase/redraw only the object that moved.

For example:

```text
old position
    ↓
erase old object
    ↓
update coordinates
    ↓
draw new object
```

`BLOCK` is useful for clearing rectangular areas.

For vector objects, `OVER` can sometimes be used for reversible drawing/highlighting.

---

# 48. 3D graphics

The 3D section provides a complete conceptual pipeline:

```text
3D nodes
    ↓
rotate X/Y/Z
    ↓
perspective projection
    ↓
translate to screen
    ↓
connect nodes with LINE
```

A cube is represented as eight nodes:

```basic
DIM x(8),y(8),z(8),vx(8),vy(8)
```

Node coordinates are loaded from `DATA`.

---

# 49. 3D rotation equations

For rotation about an axis, the source uses standard sine/cosine transformations.

For example, rotation in the Y/Z plane:

```basic
yt=y(np)
y(np)=c*yt-s*z(np)
z(np)=s*yt+c*z(np)
```

Other axes are handled similarly.

The angle is incremented each frame:

```basic
ra=ra+.1
c=COS(ra)
s=SIN(ra)
```

This is enough to create smooth wireframe rotation.

---

# 50. Perspective projection

The source uses a focal-scale value:

```basic
vx(np)=screen_x+(x(np)*fs)/(z(np)+fs)
vy(np)=screen_y+(y(np)*fs)/(z(np)+fs)
```

The important concept is:

- distant objects shrink;
- closer objects enlarge;
- `fs` controls perspective strength.

The source notes that changing the focal scale can deliberately create stronger distortion.

---

# 51. Nodes, vectors and frames

The 3D object is separated into:

- **Nodes** — 3D points.
- **Vectors** — projected 2D screen positions.
- **Frames** — lists of nodes defining faces/edges.

A frame table can be stored with `DATA`.

Then:

```basic
RESTORE frame_data
READ vn

FOR Frames=1 TO vn
    READ a,b,c,d
    LINE vx(a),vy(a) TO vx(b),vy(b) TO vx(c),vy(c) TO vx(d),vy(d) TO vx(a),vy(a)
END FOR Frames
```

This is a very good general pattern for data-driven graphics.

---

# 52. Organiser/database applications

The Organiser demonstrates that SuperBASIC is capable of larger structured applications if the data model is kept simple.

Useful patterns include:

- arrays for records;
- `DATA` for static tables;
- files for persistent data;
- multiple windows for separate UI panels;
- keyboard navigation;
- calculator-style keypads;
- colour-coded calendar entries.

A record can be represented with parallel arrays or multidimensional arrays when a full record structure is not available.

---

# 53. Calendar technique

The Organiser stores:

- day names;
- month names;
- days-per-month;
- event descriptions;
- event colours.

Example conceptual structure:

```basic
DIM wd$(7)
DIM mth$(12)
DIM md%(12)
DIM Event$(12)
DIM Pcol%(12)
```

Load using `DATA` and `RESTORE`.

This is a compact way to represent fixed application metadata.

---

# 54. Persistent application state

A good QL application can separate:

```text
configuration file
    ↓
program data file
    ↓
runtime arrays
    ↓
screen representation
```

Do not make the screen contents the only copy of application state.

The QBITS applications repeatedly load arrays from files and later save them back.

---

# 55. Editing and overwrite workflow

For user-editable files, the source commonly follows:

```text
check path
    ↓
check if file exists
    ↓
if exists: ask "Overwrite Y/N"
    ↓
DELETE existing file
    ↓
OPEN_NEW
    ↓
write data
    ↓
CLOSE
```

This is a useful pattern for preventing accidental overwrites.

---

# 56. Device-error handling

The source frequently checks for:

- missing files;
- invalid devices;
- unavailable directories;
- failed file operations.

The user interface then reports:

```text
DEVICE ERROR
File Not Found...
Loading...
Saving...
```

This is preferable to allowing a file error to leave the user with an unexplained frozen interface.

---

# 57. Program-to-program navigation

QBITS uses `LRUN` as an application launcher/return mechanism.

Typical pattern:

```basic
LRUN dev$&'Program_bas'
```

A program can keep a return filename:

```basic
dn$=dev$&'QBITSProgs_bas'
```

and return to the main menu using `LRUN dn$`.

This allows a collection of independent `.bas` programs to behave like one application suite.

---

# 58. Hot keys

The source uses `ALTKEY` to create application-level shortcuts where available.

Example concept:

```basic
ALTKEY 'M','LRUN '&dev$&'QBITSProgs_bas'&CHR$(10)
```

This can make a collection of programs feel more integrated.

Because `ALTKEY` is an extended feature, check the target environment before using it in code intended for an unexpanded QL.

---

# 59. Menus

A reusable QBITS menu design:

```text
+--------------------------------------+
|              TITLE                   |
+--------------------------------------+
|                                      |
|  > Menu item                         |
|    Menu item                         |
|    Menu item                         |
|                                      |
+--------------------------------------+
| Short description / help             |
+--------------------------------------+
```

Implementation:

- cursor keys change selection;
- a small marker identifies the current item;
- a lower window displays help;
- Enter activates;
- Esc exits;
- letters provide shortcuts.

Keep menu data in arrays or DATA rather than hard-coding each visual item.

---

# 60. Selection/highlight technique

The source often stores selection as a numeric index rather than as a screen coordinate.

Example:

```basic
y=y-1
IF y<1:y=max

y=y+1
IF y>max:y=1
```

Then the actual screen position is derived:

```basic
screen_y=base_y+(y-1)*row_height
```

This prevents the logical menu state from becoming dependent on graphics coordinates.

---

# 61. Cursor wrap-around

For cyclic menus:

```basic
IF y<1:y=max
IF y>max:y=1
```

For bounded grids:

```basic
IF c<0:c=0
IF c>2:c=2
```

Choose wrap-around or clamping deliberately.

---

# 62. Data-driven arcade graphics

The font editor and games use compact bitmap/coordinate data rather than large amounts of duplicated drawing code.

For an object:

```text
object base position
+
relative geometry
+
colour
+
fill mode
```

This is much more memory-efficient than storing full-screen images on a small QL.

---

# 63. Bitmap versus vector graphics

The source effectively uses both:

### Bitmap-style

- fonts;
- `BLOCK`;
- direct screen memory;
- PEEK/POKE;
- 8×8 graphics.

### Vector-style

- `LINE`;
- `CIRCLE`;
- `ARC`;
- `FILL`;
- `SCALE`.

Use bitmap techniques when pixel-level control matters.

Use vector primitives when an object is geometrically simple and must be repositioned or scaled.

---

# 64. Font rendering as graphics

A font character is essentially a tiny 8×8 bitmap.

Therefore the same techniques used for fonts can be used for:

- sprites;
- icons;
- tile graphics;
- status symbols;
- retro game art.

This is especially useful on the QL because a small bitmap can be manipulated directly in memory.

---

# 65. Font memory layout

The source documents a QL font structure consisting of:

```text
2 bytes  : lowest ASCII code
2 bytes  : number/count information
9 bytes per character
```

The character block contains an 8-row bitmap plus an additional byte used by the QL font structure.

Treat the exact layout as QL/TK2-specific rather than generic BASIC.

---

# 66. Font installation lifecycle

A safe font workflow is:

```text
allocate font memory
    ↓
load binary font
    ↓
CHAR_USE / assign font set
    ↓
use/modify font
    ↓
reset CHAR_USE when finished
    ↓
release allocated memory
```

If persistent memory reservation is deliberately used, the source mentions `RESPR` as an alternative lifecycle.

Do not leak font allocations between programs.

---

# 67. Compatibility with unassigned variables

The source specifically notes that SMSQ/E may be more tolerant of unassigned variables than older QL ROMs.

Therefore:

**Always initialize variables explicitly.**

Do not rely on an emulator silently converting an undefined variable into zero.

This is particularly important for:

- counters;
- arrays;
- state flags;
- colour values;
- filenames;
- loop variables.

---

# 68. Integer variables and compatibility

The source reports historical problems involving integers in:

- `FOR` loops;
- `SELect ON`;
- nested loops.

Therefore, when writing code intended for several QL implementations:

- avoid unnecessary type tricks;
- use straightforward numeric variables;
- test critical loops;
- keep loop variables simple;
- don't assume every emulator/interpreter has identical behaviour.

---

# 69. Avoiding hidden dependencies

When producing code, annotate dependencies:

```basic
REMark Requires Toolkit II: CHAR_USE
REMark Requires extended SBASIC: SCR_BASE
REMark Requires QPC/SMSQ/E: ...
```

If a feature is optional, provide a classic-QL fallback.

This is much better than allowing the LLM to generate code that only runs on QPC.

---

# 70. Building reusable graphics procedures

Recommended template:

```basic
DEFine PROCedure DrawThing(ch,x,y,col)
    INK#ch,col

    REMark all coordinates relative to x,y

    LINE#ch,x-10,y TO x+10,y
    CIRCLE#ch,x,y,5

END DEFine
```

For filled objects:

```basic
FILL#ch,1
LINE#ch,...
FILL#ch,0
```

For animation, redraw at a new `(x,y)`.

---

# 71. Reusable screen initialization

A good template:

```basic
DEFine PROCedure Init_Win
    OPEN#2,scr_
    WINDOW#2,512,224,gx,gy
    PAPER#2,0
    BORDER#2,1,3
    CLS#2

    WINDOW#0,512,32,gx,gy+224
    PAPER#0,0
    BORDER#0,1,3
    CLS#0
END DEFine
```

The exact channel arrangement should be chosen according to the application.

---

# 72. Status/message window

A bottom window is useful for:

- instructions;
- errors;
- current selection;
- score;
- prompts.

Instead of clearing the whole screen:

```basic
CLS#0
CURSOR#0,x,y
PRINT#0,message$
```

This keeps the main display intact.

---

# 73. Application exit

A clean QL application should:

1. stop timers/loops;
2. close temporary channels;
3. restore fonts if changed;
4. release `ALCHP` memory;
5. restore sensible screen settings;
6. optionally `LRUN` the parent/menu program.

The source frequently uses a dedicated exit procedure for this.

---

# 74. Example high-quality QL game skeleton

```basic
100 REMark QL GAME
110 MODE 4
120 gx=0:gy=0
130 WHEN ERRor :CONTINUE:END WHEN
140 Init_Win
150 Init_Game
160 Game_Loop
170 Game_Exit
180 STOP

1000 DEFine PROCedure Init_Win
1010 WINDOW#2,512,224,gx,gy
1020 PAPER#2,0:BORDER#2,1,3:CLS#2
1030 WINDOW#0,512,32,gx,gy+224
1040 PAPER#0,0:BORDER#0,1,3:CLS#0
1050 END DEFine

1100 DEFine PROCedure Game_Loop
1110 REPeat game_lp
1120     k=CODE(INKEY$(-1))
1130     SELect ON k
1140         =192:MoveLeft
1150         =200:MoveRight
1160         =208:MoveUp
1170         =216:MoveDown
1180         =32:Action
1190         =27:EXIT game_lp
1200     END SELect
1210     Draw_Game
1220 END REPeat game_lp
1230 END DEFine
```

This is illustrative of the architecture used in the source, not a claim that every environment accepts every optional keyword.

---

# 75. Example data-driven board checker

```basic
DEFine PROCedure CheckBoard(n)
    RESTORE WinData

    FOR i=1 TO 8
        READ a,b,c,d,e,f

        IF Grid(a,b)=n AND Grid(c,d)=n AND Grid(e,f)=n
            Win
            RETurn
        END IF
    END FOR i

WinData:
    DATA 1,1,1,2,1,3
    DATA 1,1,2,2,3,3
    DATA 1,1,2,1,3,1
    ...
END DEFine
```

The exact syntax/location of labels should follow the target interpreter's accepted SuperBASIC syntax; the key source-derived idea is to encode rule combinations as DATA and traverse them with `READ`.

---

# 76. Example screen-mode abstraction

Use one routine rather than scattering platform checks throughout the application:

```basic
DEFine PROCedure QLScrMode
    scrbase=131072
    llen=128
    xlim=512
    ylim=256
    scrmode=4

    scrbase=SCR_BASE
    llen=SCR_LLEN
    xlim=SCR_XLIM
    ylim=SCR_YLIM
    scrmode=llen/xlim*16
END DEFine
```

Then all image/memory code calls `QLScrMode` before calculating addresses.

This is a particularly good pattern for an LLM to reuse.

---

# 77. Binary resource format design

When inventing a new QL binary format, follow the source's approach:

1. fixed magic/header;
2. fixed-size numeric fields;
3. explicit dimensions;
4. explicit mode/format;
5. raw data immediately after header.

For example:

```text
HEADER
  magic
  width
  height
  row_bytes
  format
DATA
  raw bytes
```

Keep the format simple enough to load with `LBYTES` and inspect with `PEEK`.

---

# 78. QL programming checklist

Before generating code, ask internally:

### Target

- Original QL?
- Toolkit II?
- Minerva?
- SMSQ/E?
- QPC/QPC2/QPC11?
- Q68/other compatible platform?

### Memory

- How much RAM is available?
- Is a screen buffer required?
- Can the program use `ALCHP`?
- Is every allocation released?

### Display

- MODE 4 or MODE 8?
- Original 512×256?
- Extended resolution?
- Need `SCR_BASE`/`SCR_LLEN`?
- Which channels/windows are needed?

### Input

- Cursor keys?
- Space?
- Enter?
- Escape?
- Letter shortcuts?
- Timed input?

### Data

- Array?
- `DATA`/`READ`?
- Text file?
- Binary file?
- Direct memory?

### Performance

- Is the code running interpreted on an original QL?
- Can screen redraws be minimized?
- Can direct memory operations help?
- Is compilation available?

### Cleanup

- close channels;
- restore fonts;
- release memory;
- return to parent program if required.

---

# 79. Strong rules for an LLM generating QL SuperBASIC

When asked to write QL SuperBASIC:

1. **Do not write modern BASIC.**
2. Use QL syntax such as `DEFine PROCedure`, `END DEFine`, `REPeat`, `END REPeat`, `SELect ON`, `END SELect`, `FOR`, `END FOR`.
3. Prefer `CURSOR` for pixel-oriented positioning.
4. Use channel-qualified commands when working with multiple windows.
5. Use `BLOCK` for rectangular UI areas and clearing.
6. Use `LINE`, `CIRCLE`, `ARC`, `FILL` for vector graphics.
7. Use `DATA` + `READ` for compact static tables.
8. Use `RND(1 TO n)` for random integer choices as demonstrated.
9. Use `CODE(INKEY$())` for keyboard dispatch.
10. Use `ALCHP`/`RECHP` for allocated buffers when direct memory is appropriate.
11. Use `LBYTES`/`SBYTES` for binary resources.
12. Use `PEEK`/`POKE` and word variants when manipulating QL memory structures.
13. Use `WHEN ERRor` only for deliberate compatibility fallbacks, not as a blanket way to hide bugs.
14. Initialize variables explicitly.
15. Keep device names in variables such as `dev$`.
16. Keep application state separate from screen drawing.
17. Use named procedures for drawing, input, initialization and cleanup.
18. For games, keep board/state arrays independent from graphics.
19. For geometry, use anchor coordinates and relative offsets.
20. For 3D, separate nodes, projected vectors and frames.
21. For fonts, distinguish raw 8×8 bitmap data from the QL font structure.
22. Never assume QPC/SMSQ/E extensions exist on the original QL.
23. If compatibility is requested, provide a classic-QL path and clearly mark optional extensions.
24. Optimize inner loops and minimize screen redraws because interpreted SuperBASIC on original QL hardware is slow.
25. Treat the supplied QBITS knowledge as an additional source of idioms, not as proof that every extension works on every QL.

---

# 80. Patterns worth remembering as concepts

### Fixed-width output

```basic
FILL$(' ',width-LEN(str$))&str$
```

### Zero padding

```basic
FILL$('0',digits-LEN(n))&n
```

### Keyboard event

```basic
k=CODE(INKEY$(-1))
```

### Keyboard dispatch

```basic
SELect ON k
    ...
END SELect
```

### Main loop

```basic
REPeat loop
    ...
END REPeat loop
```

### Random constrained selection

```basic
REPeat lp
    n=RND(1 TO max)
    IF valid:EXIT lp
END REPeat lp
```

### Allocated binary buffer

```basic
addr=ALCHP(size)
LBYTES file$,addr
...
RECHP addr
```

### Binary save

```basic
SBYTES file$,addr,size
```

### QL font character block

```text
character base + 2 + character_index * 9
```

### Classic screen defaults

```text
screen base = 131072
line length = 128 bytes
width       = 512 pixels
height      = 256 pixels
mode        = 4
```

### Extended-mode detection

```basic
scrmode=SCR_LLEN/SCR_XLIM*16
```

### Perspective projection

```text
screen_x + x*focal/(z+focal)
screen_y + y*focal/(z+focal)
```

---

# 81. What the source demonstrates particularly well

The most valuable knowledge in QBITSProgs_v1 is not a list of keywords; it is the **programming style**:

- Build applications from small procedures.
- Treat windows/channels as UI components.
- Use DATA as compact tables.
- Represent game rules and geometry as data.
- Use arrays for application state.
- Use direct memory for bitmap/binary data.
- Build graphics from relative coordinates.
- Separate logical state from rendering.
- Use keyboard polling for responsive QL applications.
- Design around the severe limitations of original QL hardware.
- Add compatibility layers rather than rewriting every routine for every platform.
- Keep device paths configurable.
- Use simple binary file formats.
- Release allocated memory.
- Design menus consistently.
- Use the QL's unusual graphics model rather than fighting it.

---

# 82. Source limitations and caution

This document is a **condensation of the programming knowledge demonstrated by the supplied PDF**, not a complete Sinclair SuperBASIC language reference.

The PDF itself contains code written for a mixture of environments and eras. Some examples depend on Toolkit II, SMSQ/E, QPC/QPC2 or other extensions.

Therefore an LLM should not infer:

> "It appears in the PDF, therefore it exists on every original QL."

Instead classify each feature as:

- **Classic SuperBASIC / original QL concept**
- **Toolkit II / extended keyword**
- **QPC/SMSQ/E/platform-specific**
- **QBITS application convention**

When exact compatibility is uncertain, state the dependency instead of inventing certainty.

---

# 83. Compact instruction to prepend to an LLM session

Use the following as a system/developer-style instruction when feeding this knowledge to another model:

> You are programming for the Sinclair QL in QL SuperBASIC/SBASIC. Use the attached QBITS knowledge base as an additional source of programming idioms and implementation techniques. Prefer authentic QL SuperBASIC syntax and QL programming patterns. Think in terms of channels, WINDOWS, CURSOR coordinates, BLOCK/LINE/CIRCLE/ARC/FILL graphics, DATA/READ tables, REPeat and SELect loops, PEEK/POKE memory operations, ALCHP/RECHP buffers, LBYTES/SBYTES binary resources, QL device names, and keyboard polling with INKEY$. Separate application state from screen rendering. For original-QL compatibility, assume the classic 512×256 Mode 4 screen and limited memory unless the user specifies otherwise. Treat Toolkit II, SMSQ/E, QPC and extended screen/memory keywords as optional platform capabilities and mark them explicitly. Initialize variables, release allocated memory, close channels, and avoid relying on emulator-specific behaviour. When writing graphics, use reusable procedures with anchor coordinates and relative offsets. When writing games or simulations, encode fixed rules, geometry or lookup tables with DATA/READ where appropriate. Optimize inner loops and minimize screen redraws because interpreted SuperBASIC on original QL hardware is slow.
"""

---

## Provenance

Primary source: **QBITSProgs_v1.pdf**, *QL Retro Computing — A Collection of Progs written in QL SuperBASIC for the Sinclair QL and its Compatible Platforms*, QBITS Software Inc., containing programs and notes covering games, file management, font editing/viewing, 3D graphics, sound, organiser/database programming, Enigma, Lander and other SuperBASIC examples.

This knowledge base deliberately summarizes and reorganizes the programming techniques rather than reproducing the source program listings.
