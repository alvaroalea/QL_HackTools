# SuperBASIC (Sinclair QL) — LLM Coding Reference

This document is a self-contained technical reference to **SuperBASIC**, the BASIC dialect built into the Sinclair QL's QDOS operating system (and its successors: Minerva, SMSQ/E, MultiBASIC/SBASIC). It is meant to be used as background context for an LLM that will read, write, or debug SuperBASIC programs — for example for retro-computing projects targeting the QL (68008/68000), Q-emuLator, QPC, QemuLator, or SMSQ/E-based systems.

It covers: general program structure, all variable/data types, expression and operator rules, control-flow and procedure/function structures, I/O and channel handling, and a categorized command/function reference with syntax and behaviour. Where behaviour differs between the original QL ROM, Minerva, and SMSQ/E, this is noted.

---

## 1. Overview of the Language

- SuperBASIC is a **line-numbered, interpreted** BASIC, but with structured-programming extensions (PROCedures, FuNctions, REPeat/FOR/IF blocks, SELect ON) that make it closer to structured BASICs (e.g. BBC BASIC) than to line-number-only dialects.
- It is **not** an object-oriented or block-scoped language: by default all variables are **global** unless declared `LOCal` inside a PROCedure/FuNction.
- Programs run inside a **Job** (QDOS is multitasking). SuperBASIC itself is Job 0 by default; you can start further BASIC interpreters (`EW`, `EXEC`, MultiBASIC) as separate jobs.
- Line numbers shall not be used for **direct commands** (typed and executed immediately) but required for stored program lines. Convention: increment by 10 (10, 20, 30…) to leave room for insertions via `AUTO`/editing.
- Statements on the same line are separated by `:`.
- Comments: `REMark` (or `REM`) starts a comment to end of line. There is no inline `'`-style comment in standard SuperBASIC (some toolkits add `!` as a shorthand for REMark in certain contexts — treat as non-portable).
- Keywords are case-insensitive but are conventionally written with **significant capital letters marking the minimum abbreviation** that the interpreter will accept, e.g. `PRINT` may be abbreviated `PRINT`, `DEFine PROCedure` may be abbreviated `DEF PROC`, `PROCedure` → `PROC`, `REPeat` → `REP`. In this document, minimum abbreviations are shown with the accepted short form capitalised, e.g. `RETurn` (accepted as `RET`), `CONtinue` (accepted as `CON`).
- The QL ROM keyword set can be extended at runtime by loading **toolkits** (machine-code extensions such as Toolkit II, QPTR, Turbo Toolkit) which add new keywords/commands. Code that uses non-ROM keywords should note which toolkit is required.

### 1.1 Program structure skeleton

```basic
100 REMark Example program skeleton
110 :
120 DEFine PROCedure MAIN
130   LOCal a, b$, i
140   a = 10 : b$ = 'hello'
150   FOR i = 1 TO a
160     PRINT i; ' '; b$
170   END FOR i
180 END DEFine MAIN
190 :
200 MAIN
```

Running the program: `RUN` starts execution at the lowest line number, or at a line number given as a parameter (`RUN 100`).

### 1.2 Multi-statement lines and structure keywords

Loop/condition/definition keywords open a **block** that must be closed with the matching `END` keyword:

| Opens | Closes |
|---|---|
| `IF ... THEN` (multi-line form) | `END IF` |
| `REPeat [name]` | `END REPeat [name]`, exit with `EXIT [name]` |
| `FOR var = start TO end [STEP step]` | `END FOR [var]`, exit with `EXIT [var]` |
| `WHILE condition` (Minerva/SMSQ extension, see §4) | `END WHILE` |
| `SELect ON expr` | `END SELect` |
| `DEFine PROCedure name` | `END DEFine [name]`, or `RETurn` to exit early |
| `DEFine FuNction name` | `END DEFine [name]` (must exit via `RETurn value`) |

A single-line (in-line) form is also legal for `IF` and for `DEFine PROCedure`/`DEFine FuNction` when the whole body fits after a colon on one line — see §5.

---

## 2. Data Types (Variables)

SuperBASIC is **not** a class/struct language — it has exactly three scalar data types, plus arrays of each, plus a few pseudo-types used by extensions/toolkits.

### 2.1 Type-denoting suffixes

The **last character of a variable's name** decides its type:

| Suffix | Type | Notes |
|---|---|---|
| *(none)* | **Floating point** (default numeric type) | 40-bit / effectively double-precision-like accuracy internally (QDOS uses a proprietary extended float format); can hold integral or fractional values |
| `%` | **Integer** | Signed, held internally as a machine word; standard QL SuperBASIC integers are effectively 32-bit (range approx. ±2,147,483,647), though older ROM documentation describes 16-bit-safe ranges — always test on target ROM/emulator if exact range matters |
| `$` | **String** | Sequence of characters, 0–32767 bytes typically (implementation dependent; QDOS strings are length-prefixed, not null-terminated) |

There is **no** separate Boolean type: `TRUE`/`FALSE` conditions are represented as floating-point values, where `0` is false and any **non-zero** value is true; comparison and logical operators return `1` for true and `0` for false (in Minerva/SMSQ, `TRUE`/`FALSE` may also be predefined constants via `SET`/toolkit).

There is **no** separate character/byte type; use one-character strings, or `CODE`/`CHR$` to convert to/from a numeric character code.

### 2.2 Variable naming rules

- Must start with a letter.
- May contain letters and digits after the first character but no spaces.
- The type suffix (`%` or `$`), if any, is part of the name: `A`, `A%`, and `A$` are **three different variables**.
- No reserved-word restriction beyond avoiding exact keyword clashes causing "bad name" style ambiguity — in practice avoid naming variables the same as keywords.
- Names are case-insensitive: `Total` and `TOTAL` refer to the same variable.

### 2.3 Declaring / creating variables

There is no explicit `DIM` for scalars — a scalar variable is **created on first assignment** (implicit declaration):

```basic
100 count = 0        REMark floating point
110 count% = 0       REMark integer
120 name$ = ''        REMark string, empty
```

Reading an undeclared scalar variable before it has been assigned normally causes a run-time error ("Not Found" / "Undefined variable") on the QL ROM interpreter — always initialise before use, especially inside PROCedures/FuNctions.

### 2.4 Arrays

Declared explicitly with `DIM`:

```basic
100 DIM a(10)           REMark floating point array, 11 elements: a(0) to a(10)
110 DIM b%(5,5)         REMark 2-dimensional integer array
120 DIM c$(20,10)       REMark array of 21 strings, each up to 10 characters long
```

- **All array subscripts are 0-based** (element 0 to N inclusive for `DIM name[%|$](N)`).
- Type of the array is inherit of the name subfix, `name%` for integer, `name$` for string
- Up to a ROM-defined maximum number of dimensions (commonly up to 8; check target ROM docs) is allowed, e.g. `DIM t(3,3,3)`.
- For **string arrays**, an optional last parameter after the dimension list sets the **fixed maximum length per element**: `DIM c$(20,10)` — 21 strings, each up to 10 characters; if omitted, a ROM default (commonly 80 chars per string element on older ROMs, but effectively can differ) applies — always specify it explicitly for portability.
- `DIM` can be executed several times per array name, ien each one the memory is cleaned.
- Reference an element with the array name and the index in parentheses: `a(3) = 42`, `PRINT c$(1,2)`.
- The whole array can be referred to by name without parentheses in some contexts (e.g. `LBYTES`/`BLOCK` operations, or passing to a PROCedure by reference) — check specific command docs.

### 2.5 Type coercion / conversion rules

- **Floating point ↔ integer**: automatic when assigning between them; assigning a fractional float value to an integer variable **truncates** (rounds toward zero) — this is a very common source of bugs, be explicit with `INT()` when truncation/rounding must be controlled.
- **Numeric ↔ string**: NOT automatic. You must explicitly convert:
  - Number → string: `STR$(n)` — do **not** rely on any implicit conversion; there is no implicit `+`-based string concatenation of numbers.
  - String → number: bare numeric literals inside expressions are parsed automatically, but converting a string variable's contents to a number requires `VAL(s$)` (or arithmetic functions can raise "bad parameter" if given a string). SuperBASIC does not silently coerce `"5" + 3`.
- **String concatenation** uses `&`, never `+` (`+` on two strings is a syntax/type error): `full$ = first$ & ' ' & last$`.
- Comparisons (`=`, `<>`, `<`, `>`, `<=`, `>=`) work between two strings (lexical/ASCII comparison) or between two numeric values (any mix of integer/float, auto-promoted to float for comparison) — comparing a string to a number is an error.

### 2.6 Constants / literals

- Numeric literals: `123`, `3.14`, `-7`, `1E10` (scientific notation), `1.5E-3`.
- Hexadecimal literals: prefix with `£$` is not used — the standard prefix in ROM syntax tables is a hash/hex marker depending on ROM; the safest, widely portable form is the `HEX('...')` function (see §7) rather than a literal hex prefix, since prefix support (`$`, `&`) varies by toolkit. If your target explicitly supports the `$` (hex) literal prefix (common on Minerva/SMSQ), `$1F` = 31 decimal.
- String literals: enclosed in single quotes `'like this'`. To embed a literal single quote inside a string, double it: `'it''s'` → `it's`. Double quotes are **not** the standard QL string delimiter (unlike many other BASICs) — always use single quotes unless a specific extension explicitly documents double-quote support.
- There is no dedicated `TRUE`/`FALSE` literal in base ROM SuperBASIC; use `1` and `0`, or define your own: `DEFine PROCedure INIT_CONSTS : GLOBAL TRUE, FALSE : TRUE = 1 : FALSE = 0 : END DEFine` (if `GLOBAL` is supported — see §2.7) — or simply use bare `1`/`0` throughout.

### 2.7 Scope: GLOBAL vs LOCal

- By default every variable is **global** to the whole running program (all Jobs' BASIC interpreters have their own separate global variable space, i.e. globals are per-Job, not shared across Jobs unless you use inter-job communication like pipes or shared memory).
- Inside a `DEFine PROCedure`/`DEFine FuNction`, you can declare parameters and `LOCal` variables that exist **only for that call** and shadow any global of the same name:

```basic
100 DEFine PROCedure ADD (x, y)
110   LOCal result
120   result = x + y
130   PRINT result
140 END DEFine
```

- Parameters listed in the `(item, item, ...)` list of a `DEFine PROCedure`/`DEFine FuNction` are passed **by reference** for simple scalar variables in some ROM implementations when the *caller* passes a bare variable name (so the called routine can modify the caller's variable) — behaviour here is ROM/toolkit-dependent and a frequent source of confusion; when in doubt, treat parameters as local copies (pass-by-value) unless you have verified reference semantics on your specific target, and prefer explicit `LOCal` + return values (for FuNctions) or explicit global variables for output parameters.
- `LOCal a, b$, i%` — declares multiple locals of mixed types on one line; must appear as (one of) the first statement(s) in the definition, before other executable statements.

---

## 3. Expressions and Operators

### 3.1 Arithmetic operators (numeric operands only)

| Operator | Meaning |
|---|---|
| `+` | addition |
| `-` | subtraction / unary minus |
| `*` | multiplication |
| `/` | division (float result even for integer operands) |
| `**` or `^` | exponentiation (ROM-dependent which symbol is accepted; `**` is the classic QL ROM form) |
| `MOD` | modulo / remainder |
| `DIV` | integer division (Toolkit/Minerva extension on some ROMs — verify availability; otherwise use `INT(a/b)`) |

Standard operator precedence applies (unary minus / `**` highest, then `*`,`/`,`MOD`, then `+`,`-`), with parentheses `()` to override.

### 3.2 String operator

| Operator | Meaning |
|---|---|
| `&` | concatenation of two strings |

### 3.3 Relational operators

`=`  `<>`  `<`  `>`  `<=`  `>=` — usable on two numbers or two strings (not mixed); result is `1` (true) or `0` (false).

### 3.4 Logical operators

`AND`  `OR`  `NOT` — operate on numeric truth values (0 = false, non-zero = true); typically implemented as bitwise-on-the-underlying-representation in classic BASIC style, so used both for boolean logic in `IF`/`WHILE` conditions and (carefully) for bit manipulation on integers.

### 3.5 Functions used inside expressions

Any built-in or user-defined FuNction can appear inside an expression, e.g. `y = SIN(x) * 2 + SQRT(z)`.

---

## 4. Control Structures

### 4.1 IF ... THEN ... ELSE

Two forms:

**Single line:**
```basic
100 IF a > b THEN PRINT 'a is bigger' : PRINT 'done'
```
(everything after `THEN` on that line executes if true; nothing happens if false — there is no single-line `ELSE` unless the ROM/toolkit explicitly supports `IF...THEN...ELSE` on one line, which classic QL ROM does allow in a restricted form: `IF cond THEN stmt : ELSE stmt` is **not** standard — prefer the block form below when an `ELSE` branch is needed, for portability.)

**Block form:**
```basic
100 IF a > b THEN
110   PRINT 'a is bigger'
120 ELSE
130   PRINT 'b is bigger or equal'
140 END IF
```
`ELSE IF` chains are written as nested `IF`s or, on ROMs supporting it, as `ELSE IF` on one line repeated.

### 4.2 FOR ... END FOR

```basic
100 FOR i = 1 TO 10
110   PRINT i
120 END FOR i
```
- Optional `STEP` value: `FOR i = 10 TO 1 STEP -1`.
- `END FOR` with no name is also accepted; naming it (`END FOR i`) is good practice for nested loops.
- Early exit: `EXIT i` (or bare `EXIT` for innermost loop, ROM-dependent) jumps to the statement after the matching `END FOR`.
- `FOR` also has a single-line form ending the loop body with the whole thing on one line is **not** standard for multi-statement bodies — use the block form for anything beyond a trivial one-liner such as `FOR i=1 TO 10: PRINT i: END FOR i`.

### 4.3 REPeat ... END REPeat (general-purpose loop)

`REPeat` is SuperBASIC's general loop, roughly equivalent to `while(true)` with explicit exits:

```basic
100 REPeat main_loop
110   INPUT 'Value (0 to stop): '; v
120   IF v = 0 THEN EXIT main_loop
130   PRINT v * v
140 END REPeat main_loop
```
- The loop name (`main_loop` above) is optional but strongly recommended for nested loops so `EXIT name` unambiguously targets the correct loop.
- There is no built-in `REPeat ... UNTIL condition` trailing test — you implement the test with `IF ... THEN EXIT` inside the body, as above.

### 4.4 WHILE ... END WHILE

Available on Minerva/SMSQ/E and some toolkits as a pre-tested loop (check target ROM — not present on plain unexpanded QL ROM):
```basic
100 WHILE v <> 0
110   INPUT 'Value (0 to stop): '; v
120   PRINT v * v
130 END WHILE
```
Where unavailable, emulate with `REPeat`/`IF...EXIT` as in §4.3.

### 4.5 SELect ON ... END SELect

Multi-way branch on a numeric or string expression, roughly a `switch`/`case`:

```basic
100 INPUT 'Choice (1-3): '; c
110 SELect ON c
120   = 1 : PRINT 'One'
130   = 2 : PRINT 'Two'
140   = 3 : PRINT 'Three'
150   REMainder : PRINT 'Invalid choice'
160 END SELect
```
- Each branch is introduced by a relational test (`= value`, or `< value`, `1 TO 5`, etc., depending on ROM) directly after the line's clause separator.
- `REMainder` (often abbreviated) is the default/else branch, matched if nothing else matches.
- Exact clause syntax (range tests, comma-separated value lists) varies between ROM/Minerva/SMSQ implementations — confirm against target documentation before relying on advanced clause forms; the simple `= value` form above is universally supported.

### 4.6 GO TO / GO SUB (unstructured, legacy)

```basic
100 GO TO 500
...
500 REMark target
```

```basic
100 GO SUB 500
...
190 STOP
...
500 REMark target
...
590 STOP
```

`GO SUB line` / `RETurn` also exist as the classic unstructured subroutine call, but `DEFine PROCedure`/`DEFine FuNction` (§5) are strongly preferred in idiomatic SuperBASIC — `GO SUB` predates and is largely superseded by PROCedures.

### 4.7 STOP / PAUSE / CONtinue

- `STOP` — halts program execution immediately (drops back to direct command mode); can display a message: `STOP` alone, program can be resumed from the next statement with `CONtinue`.
- `PAUSE [n]` — suspends execution for `n` fiftieths of a second (frame ticks), or waits for a keypress if no parameter is given; commonly used for animation timing or "press any key" prompts.
- `CONtinue` (direct command) — resumes a program halted by `STOP` or by pressing the STOP/ESC-equivalent key.

---

## 5. PROCedures and FuNctions

These are SuperBASIC's primary mechanism for structured, reusable code — always prefer them over `GO SUB` for new code.

### 5.1 DEFine PROCedure

Does **not** return a value; used for side effects (printing, changing globals, I/O, etc.).

```basic
100 DEFine PROCedure GREET (name$)
110   PRINT 'Hello, '; name$; '!'
120 END DEFine
...
200 GREET 'World'
```

- Call syntax: **no parentheses around the arguments** when calling — `GREET 'World'`, not `GREET('World')`. (Parentheses in the *definition* line are for declaring the parameter list only.)
- Multiple parameters: `DEFine PROCedure LINE (x1, y1, x2, y2)` then call as `LINE 0, 0, 100, 100`.
- Early return: `RETurn` (with no value) exits the PROCedure immediately.
- In-line (single statement) form:
  ```basic
  100 DEFine PROCedure BEEP2 : BEEP 100, 10 : END DEFine
  ```

### 5.2 DEFine FuNction

**Must** return a value via `RETurn value`; the FuNction name's suffix (`$`/`%`/none) determines its return type, exactly like a variable.

```basic
100 DEFine FuNction SQUARE(n)
110   RETurn n * n
120 END DEFine
...
200 PRINT SQUARE(5)          REMark prints 25
```

```basic
100 DEFine FuNction GREETING$(name$)
110   RETurn 'Hello, ' & name$ & '!'
120 END DEFine
```

- Call syntax **uses parentheses**, like calling a normal built-in function: `x = SQUARE(5)`.
- Unlike PROCedures, a FuNction **must** execute a `RETurn value` on every code path, or a run-time error occurs ("no RETurn", or similar, ROM-dependent) when the end of the definition is reached without one.
- `LOCal` variables and parameters follow the same rules as PROCedures (§2.7).

### 5.3 Recursion

Both PROCedures and FuNctions can call themselves recursively, subject to available stack/heap memory (limited on real QL hardware — 128K–640K typical RAM depending on expansion; emulators are usually far more generous).

### 5.4 Passing arrays and by-reference behaviour

Whole arrays can generally be passed to a PROCedure/FuNction by including the array name (without subscript) as a parameter; the callee then indexes into the same underlying array storage (this is effectively reference/pointer passing for arrays, distinct from scalar pass semantics discussed in §2.7). Verify exact semantics for the specific ROM/toolkit you are targeting before relying on this for correctness-critical code.

---

## 6. Program Editing / Housekeeping Commands

These commands manage the program in memory rather than performing runtime logic:

| Command | Effect |
|---|---|
| `NEW` | Clears the current program and all variables from memory |
| `CLEAR` | Clears all variable values (keeps the program) |
| `LIST [start[,end]]` | Lists program lines to the screen (or `#channel`) |
| `RUN [line]` | Runs the program, optionally starting at `line` |
| `SAVE devname_filename` | Saves the program to the named device/file, e.g. `SAVE flp1_myprog` |
| `LOAD devname_filename` | Loads a program from disk, replacing the current one |
| `MERGE devname_filename` | Loads a program from disk and merges it (by line number) with the one in memory |
| `DELETE start[,end]` | Deletes a range of program lines |
| `RENumber [newstart[,increment]]` | Renumbers program lines |
| `EDIT line` / `ED` | Enters the line/screen editor on a given line |
| `AUTO [start[,increment]]` | Auto-generates ascending line numbers as you type new lines |
| `TRACE [ON \| OFF]` | Toggles line-number tracing during execution, for debugging |
| `EXTRAS` / `KEYS` | Lists currently available extended keywords (from loaded toolkits) — name varies by ROM |

Devices are named like `flp1_` (floppy drive 1), `mdv1_` (microdrive 1), `win1_` (hard/Winchester drive 1), `ram1_` (RAM disk), `net1_` (network), `ser1_`/`ser2_` (serial), `scr_` (screen). Filenames follow the device name directly (no extra separator needed beyond the trailing underscore that is part of the device name), e.g. `flp1_data_dat`, `win1_source_bas`.

---

## 7. Command & Function Reference by Category

Below, `#n` denotes an optional channel number parameter (see §8). Bracketed `[...]` means optional. This is not the complete ROM keyword set (which numbers in the hundreds once toolkits are included) but covers the commands needed for the large majority of programs; consult the full RWAP/NormanDunbar SuperBASIC manual for exhaustive, ROM-version-specific detail (`https://superbasic-manual.readthedocs.io/`).

### 7.1 Input / Output

| Keyword | Syntax | Behaviour |
|---|---|---|
| `PRINT` | `PRINT [#n,] expr [; \| , expr ...] [;]` | Outputs values. `;` runs items together; `,` tabs to next print zone. Trailing `;`/`,` suppresses the newline. |
| `INPUT` | `INPUT [#n,] ['prompt';] var[, var...]` | Reads value(s) from keyboard (or channel) into variable(s); type of each var determines what is accepted (numeric vs string). |
| `INKEY$` | `INKEY$ (timeout [,#n])` | Reads a single key without waiting for Enter; `timeout` in 1/50ths of a second, `-1` waits indefinitely, `0` polls immediately and returns empty string if nothing pressed. |
| `KEYROW` | `KEYROW (row)` | Low-level scan of a keyboard row's raw key state (bitmask); used for fast game-style input. |
| `BEEP` | `BEEP pitch, duration` | Sounds a tone; `pitch` and `duration` are ROM-defined numeric ranges (higher pitch value = lower frequency on classic ROM — check ROM docs for exact formula). |

### 7.2 Screen / Windows / Graphics

| Keyword | Syntax | Behaviour |
|---|---|---|
| `MODE` | `MODE n` | Sets the screen mode (e.g. `MODE 4` = 256×256, 4 colours [classic QL]; `MODE 8` = 512×256, 2 colours; Minerva/Aurora/Q40/emulators add higher-resolution/higher-colour modes). |
| `WINDOW` | `WINDOW [#n,] xsize, ysize, xorig, yorig` | Defines the size and position of a window on a channel. |
| `PAPER` | `PAPER [#n,] colour` | Sets background colour for a channel/window. |
| `INK` | `INK [#n,] colour` | Sets foreground (text/drawing) colour. |
| `BORDER` | `BORDER [#n,] width [,colour]` | Draws a border of given width/colour around a window. |
| `CLS` | `CLS [#n]` | Clears the specified window/channel to the current PAPER colour. |
| `AT` | `AT [#n,] y, x` | Positions the text cursor at row `y`, column `x` (**note the y,x order** — vertical first — this catches many newcomers). |
| `CURSOR` | `CURSOR [#n,] x, y` | Positions the graphics cursor (pixel coordinates) — used before `LINE`/plotting; some ROMs unify this with `AT`. |
| `POINT` | `POINT [#n,] x, y [,colour]` | Plots a single pixel. |
| `LINE` | `LINE [#n,] x1,y1 TO x2,y2 [,colour]` | Draws a straight line between two points. |
| `CIRCLE` | `CIRCLE [#n,] x, y, radius [,colour]` | Draws a circle. |
| `ARC` | `ARC [#n,] x, y, radius, angle1, angle2 [,colour]` | Draws an arc. |
| `FILL` | `FILL [#n,] switch` | Turns area-fill mode on (`1`)/off (`0`) for subsequent shapes. |
| `BLOCK` | `BLOCK [#n,] xsize, ysize, x, y [,colour]` | Draws a filled rectangular block. |
| `SCROLL` | `SCROLL [#n,] lines` | Scrolls a window's text content. |
| `OVER` | `OVER [#n,] mode` | Sets the drawing logic mode (overwrite/XOR/etc.) for subsequent graphics operations. |
| `FLASH` | `FLASH [#n,] switch` | Turns character flashing on/off. |
| `STRIP` | `STRIP [#n,] switch` | Toggles reverse-video ("strip") mode. |
| `UNDER` | `UNDER [#n,] switch` | Turns underlining on/off. |

### 7.3 String Functions

| Function | Syntax | Behaviour |
|---|---|---|
| `LEN` | `LEN(s$)` | Returns the length (character count) of a string. |
| `LEFT$` | `LEFT$(s$, n)` | Leftmost `n` characters. |
| `RIGHT$` | `RIGHT$(s$, n)` | Rightmost `n` characters. |
| `MID$` | `MID$(s$, start [,length])` | Substring from `start` (1-based), `length` characters (default: rest of string). |
| `CHR$` | `CHR$(code)` | Character corresponding to numeric character `code`. |
| `CODE` | `CODE(s$)` | Numeric character code of the first character of `s$`. |
| `STR$` | `STR$(n)` | Converts a number to its string representation. |
| `VAL` | `VAL(s$)` | Converts a string to its numeric value (error on non-numeric content). |
| `UPPER$` | `UPPER$(s$)` | Converts to uppercase. |
| `LOWER$` | `LOWER$(s$)` | Converts to lowercase. |
| `FILL$` | `FILL$(s$, n)` | Repeats/pads string `s$` to length `n`. |
| `INSTR` (operator/function) | `s1$ INSTR s2$` | Returns the position of `s2$` within `s1$` (0 if not found); note unusual infix-operator-like syntax. |
| `SPACE$` | `SPACE$` or similar padding function | Not always present under this exact name on all ROMs — commonly emulated with `FILL$(' ', n)`. |

### 7.4 Numeric / Math Functions

| Function | Syntax | Behaviour |
|---|---|---|
| `ABS` | `ABS(n)` | Absolute value. |
| `INT` | `INT(n)` | Integer part (rounds toward negative infinity, i.e. floor, on classic BASIC convention — confirm on target ROM as truncation-vs-floor can differ for negative numbers). |
| `SGN` | `SGN(n)` | Sign: -1, 0, or 1. |
| `SQRT` | `SQRT(n)` | Square root. |
| `SIN` / `COS` / `TAN` | `SIN(n)` etc. | Trigonometric functions, radians. |
| `ASIN` / `ACOS` / `ATAN` | | Inverse trig functions. |
| `EXP` | `EXP(n)` | e^n. |
| `LN` | `LN(n)` | Natural logarithm. |
| `LOG` | `LOG(n)` | Base-10 logarithm (naming/availability can vary — verify against target ROM). |
| `PI` | `PI` | Constant π (no parentheses — it is a niladic function/constant). |
| `RND` | `RND(n)` | Pseudo-random number; `RND(n)` for an integer in a ROM-defined range/behaviour depending on argument (e.g. `RND(1)` for 0–1 float, `RND(n)` for 1 to n integer — behaviour is ROM/toolkit dependent, check target docs), `RND` with no seed re-seeds from a system clock/timer source on most implementations. |
| `MOD` | `a MOD b` | Remainder of division (operator, see §3.1). |
| `HEX` | `HEX('xx')` | Converts a hexadecimal string to a numeric value. |
| `HEX$` | `HEX$(n [,digits])` | Converts a number to a hexadecimal string. |

### 7.5 System / Machine-Level Functions

| Keyword | Syntax | Behaviour |
|---|---|---|
| `PEEK` / `PEEK_W` / `PEEK_L` | `PEEK(addr)` | Reads a byte/word/long from memory address `addr`. |
| `POKE` / `POKE_W` / `POKE_L` | `POKE addr, value` | Writes a byte/word/long to memory. |
| `RESPR` | `RESPR(bytes)` | Reserves a block of memory and returns its address (typically used before `LBYTES` of machine code). |
| `RECLAIM` | `RECLAIM addr` | Frees memory previously reserved with `RESPR`. |
| `CALL` | `CALL addr [,param]` | Calls machine code at `addr`. |
| `LBYTES` | `LBYTES devname_filename, addr` | Loads a binary file directly into memory at `addr`. |
| `SBYTES` | `SBYTES devname_filename, addr, length` | Saves a block of memory to a binary file. |
| `DATE` / `DATE$` | `DATE` / `DATE$` | Current system date, numeric/string form. |
| `TIME` / `TIME$` | Current system time. |
| `VER$` | `VER$` | ROM/OS version string. |
| `JOB` | Job/task management functions (list, create, remove jobs) — availability and exact names vary widely by ROM/SMSQ/E version. |

### 7.6 File / Channel Handling

| Keyword | Syntax | Behaviour |
|---|---|---|
| `OPEN` | `OPEN #n, devname_filename` | Opens an existing file on channel `n` for read/write. |
| `OPEN_IN` | `OPEN_IN #n, devname_filename` | Opens a file for input (read) only. |
| `OPEN_NEW` | `OPEN_NEW #n, devname_filename` | Creates a new file, opened for output. |
| `OPEN_OVER` | `OPEN_OVER #n, devname_filename` | Opens (creating if needed) a file for output, overwriting content from the start. |
| `CLOSE` | `CLOSE #n` | Closes a channel. |
| `DELETE` (file) | `DELETE devname_filename` | Deletes a file (distinct from the program-line-delete usage — context-dependent by argument type). |
| `FORMAT` | `FORMAT devname` | Formats a disk/medium. |
| `DIR` | `DIR [devname]` | Lists directory contents. |
| `EOF` | `EOF(#n)` | Returns true (non-zero) at end of file on channel `n`. |
| `FLUSH` | `FLUSH #n` | Flushes buffered output to a channel. |

---

## 8. Channels and I/O Model

- SuperBASIC I/O is **channel-based**: every input/output operation (PRINT, INPUT, graphics, file access) is directed at a numbered channel, referenced as `#n`.
- Default channels on program start: **`#0`** is the *command/input* window, **`#1`** is the *default output* window. If a command's `#n` parameter is omitted, it typically defaults to `#1` (for output-only commands) or `#0` (for input).
- Additional channels are opened explicitly for extra screen windows (`WINDOW`/`OPEN` a `con_`-type "console" channel) or for files/devices (`OPEN`/`OPEN_IN`/`OPEN_NEW` as above).
- Device-name channel prefixes used when opening non-screen channels: `con_` (console window), `flp1_`/`flp2_` (floppy), `mdv1_`/`mdv2_` (microdrive), `win1_` (Winchester/hard disk), `ram1_` (RAM disk), `ser1_`/`ser2_` (serial), `net1_`...`net31_` (QL network), `scr_` (whole-screen graphics channel), `pipe` (inter-job pipes, SMSQ/E/Minerva).
- Always `CLOSE` file channels you `OPEN` once finished, to flush buffers and free the channel number for reuse.

---

## 9. Error Handling

- SuperBASIC has no `try/catch`. The main mechanisms are:
  - **`ERR`** (or `ERRN`, ROM-dependent naming) — a special numeric expression that reflects the error number of the most recent error, testable after an operation.
  - **`ERRT$`** / similar — returns a human-readable error message string for the last error, where supported.
  - **`TRAP` / `MISTake`** — some ROM/Minerva/SMSQ implementations offer explicit error-trapping keywords, e.g. wrapping a risky statement so that on error, control passes to a specified line/handler instead of halting the program with a "Bad parameter"/"Not found"/etc. message. Because trap syntax and availability vary significantly by ROM version (`TRAP`, `ON ERROR`, `MISTake` all appear in different implementations), check your specific target's documentation before relying on structured error handling; if portability across ROMs matters, defensively validate inputs (e.g. check array bounds, check `EOF` before reading) rather than relying on trap/recovery keywords.
- Common runtime error categories you will see reported: `Bad parameter`, `Bad name`, `Not found`, `Division by zero`, `Out of range`, `Out of memory`, `Line not found` — messages are typically printed with the offending line number when a program (not a direct command) fails.

---

## 10. Style / Idiom Notes for Generated Code

When generating or refactoring SuperBASIC for a real QL target, follow these conventions to match idiomatic, portable code:

1. Prefer `DEFine PROCedure`/`DEFine FuNction` over `GO SUB`; keep a single `MAIN` (or similarly named) top-level PROCedure called from the last program line, with all real logic in named PROCedures/FuNctions below it (this mirrors how the manual excerpts and most published QL listings are structured).
2. Declare every scalar used inside a PROCedure/FuNction with `LOCal` unless it is deliberately meant to be a global; do not assume auto-creation is safe when values could leak between calls.
3. Always use `'single quotes'` for string literals, and `&` (never `+`) for string concatenation.
4. Remember `AT #n, y, x` is **row, then column** — the reverse of many other systems' `x, y` ordering; double-check any screen-positioning code you generate.
5. Initialise every scalar variable before first read (no implicit zero/empty default is guaranteed to be safe to rely on across all ROM versions).
6. Explicitly dimension string arrays with a max-length parameter (`DIM a$(n, maxlen)`) rather than relying on a ROM default.
7. Increment line numbers by 10 by default, leaving gaps for future edits, unless the target program will be run through `RENumber` after edits anyway.
8. Close every file channel you open (`CLOSE #n`) and reclaim (`RECLAIM`) every block you `RESPR`.
9. Where a feature's availability differs by ROM (`WHILE`, `TRAP`, hex literal prefixes, `DIV`), either avoid it for portability or clearly comment which ROM/toolkit it requires.
10. Keep in mind SuperBASIC is single-precision-friendly but has no strict typing enforcement beyond the suffix convention — a missing `%`/`$` where one was intended is a very common and silent-until-runtime bug class; be careful and consistent with suffixes across a whole program.

---

## 11. Reference Sources

This document was compiled from general SuperBASIC/QDOS language knowledge together with verification against the community-maintained **RWAP Software SuperBASIC Manual** (originally by Rich Mellor / Norman Dunbar, converted for ReadTheDocs), available at:
- https://superbasic-manual.readthedocs.io/
- https://github.com/NormanDunbar/SuperBASIC-Manual

For exhaustive, ROM-version-specific syntax, exact error messages, and edge-case behaviour of any individual keyword, consult the linked manual directly — it documents differences between the original JS/MG ROMs, Minerva, and SMSQ/E on a per-keyword basis, which this summary intentionally condenses for LLM-context purposes.
