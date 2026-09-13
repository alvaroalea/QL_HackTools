# Sinclair QL — Condensed 68000/68008 Assembler Reference
### Syntax, Registers, and Guidelines for Systems with <1 MB RAM

> **Purpose of this document:** This is a grounding/reference file intended to
> be loaded as context for a local code-assistant LLM (e.g. Qwen-Coder or
> similar) when generating or reviewing 68000/68008 assembly code targeting
> the Sinclair QL / QDOS. It is written as dense, unambiguous factual
> reference (register tables, calling conventions, memory maps, error codes)
> rather than tutorial prose. When generating code from this context, the
> model should:
> - Prefer facts stated in tables over inferred defaults.
> - Never invent trap numbers, vector offsets, or system variable offsets not
>   listed here — flag them as "unknown, verify" instead.
> - Always apply the register-preservation rules for the calling context in
>   use (user trap, device driver, SuperBASIC interface, interrupt task).
> - Always respect the memory-map and low-RAM constraints in §9 when
>   generating code for machines with <1 MB RAM.

---

## 1. The Processor: MC68008 in the QL

The QL uses an **MC68008**: a 68000-class CPU with an 8-bit external data bus
and 20 address lines (1 MB addressable). Internally it is a full 68000 — same
instruction set, same 32-bit register file. Only the external bus width
differs (affects cycle timing, not addressing modes).

- Address space: `$00000`–`$FFFFF` (1 MB).
- No MMU: no virtual memory, no automatic relocation after load. All code
  must run from fixed addresses; **position-independent code is the norm**,
  especially for ROM, Things, ROM drivers, ROM-loaded S*BASIC extensions.
- 16 TRAP vectors (`TRAP #0`–`#15`); QDOS reserves `#0`–`#4`.

---

## 2. Register Map

### 2.1 Data registers D0–D7 (32-bit)
Partial-width access via instruction size suffix:
- `.B` — low byte (bits 0–7)
- `.W` — low word (bits 0–15)
- `.L` — full longword (bits 0–31)

There is no separate 8-bit/16-bit data register — `.B`/`.W`/`.L` are views of
the same Dn.

### 2.2 Address registers A0–A7 (32-bit)
- `A0`–`A6`: general-purpose address registers.
- `A7`: **Stack Pointer**. Physically two registers:
  - **USP** (User Stack Pointer) — active in user mode.
  - **SSP** (Supervisor Stack Pointer) — active in supervisor mode.
  Assembly always references `A7`; the CPU switches automatically based on
  the S bit in SR.
- `.B` operations on An are illegal; only `.W` (sign-extended) and `.L` are
  valid.

### 2.3 PC — Program Counter
32-bit, though only 20 lines are wired on the QL. Not a general operand
except via PC-relative modes (`(d16,PC)`, `(d8,PC,Xn)`).

### 2.4 SR — Status Register (16-bit)

```
 15 14 13 12 11 10  9  8  7  6  5  4  3  2  1  0
  T  S  -  -  I2 I1 I0  -  X  N  Z  V  C
```

- **T** (Trace): trace mode, rarely used in application code.
- **S** (Supervisor): 1 = supervisor mode, 0 = user mode.
- **I2-I0**: interrupt priority mask (0–7).
- **CCR** (low byte, bits 0–4): `X N Z V C` — Extend, Negative, Zero,
  Overflow, Carry. On CPUs ≥68010 (not the base 68008, but relevant for
  compatibility code), reading full SR from user mode traps as **Privilege
  Violation**; QDOS emulates the classic `MOVE SR,Dn` idiom for compatibility.
  Prefer `MOVE CCR,Dn` explicitly in new code.

**Rule:** never assume the state of X/N/Z/V/C after a TRAP call. Only **D0**
is guaranteed as the return value.

---

## 3. Assembler Syntax (QMAC / SMSQ-style convention)

### 3.1 Line format

```
label<TAB>mnemonic<TAB>operands<TAB>; comment
```

- Tab stops at 8 columns.
- System symbols (`SMS.xxx`, `IOA.xxx`, `MT.xxx`, `IOW.xxx`, `IOF.xxx`) are
  UPPERCASE. User labels are lowercase, words separated by `_`
  (`bucle_lee`, `com_check`).
- Comment: `;` to end of line.
- Source files typically open with a version header + dated changelog
  (`YYYY-MM-DD`), followed by `SECTION`, `XDEF`, `XREF`, `INCLUDE`.

```asm
        SECTION mycode
        XDEF    my_routine
        XREF    cv_ctype
        INCLUDE 'dev3_keys_sms_io'
```

### 3.2 Numeric literals

| Format    | Example   | Meaning        |
|-----------|-----------|----------------|
| Decimal   | `123`     | plain integer  |
| Hex       | `$4AFB`   | `$` prefix     |
| Binary    | `%1010`   | `%` prefix     |
| Char      | `'A'`     | ASCII code     |
| String    | `'text'`  | byte sequence  |

### 3.3 Data directives

```asm
label     DC.B  1,2,3,'text'    ; define bytes
label     DC.W  $1234,-1        ; define words
label     DC.L  address         ; define longwords
buffer    DS.B  256             ; reserve 256 uninitialized bytes
table     DS.W  40              ; reserve 40 words
constant  EQU   $18020          ; symbolic alias, no storage
```

Rules:
- `DC.W`/`DC.L` require even alignment. **Always verify manual alignment**
  before executable code or word/long tables — the 68008 raises **Address
  Error** on any word/long access at an odd address.
- `EQU` is compile-time substitution only; it does not reserve or relocate
  memory.

### 3.4 Minimal source file skeleton

```asm
; Example routine V1.00 (C) author
; 2024-01-01 1.00 First release
        SECTION example
        XDEF    br_entry
        XREF    ut_thjmp
        INCLUDE 'dev8_keys_sms_io'

br_entry
        ; ... body ...
        rts

        END
```

### 3.5 Routine header convention (mandatory for reusable code)

Every reusable routine should carry a register-role header. Codes: `c`=call
parameter, `r`=return parameter, `p`=preserved, `u`=updated, `s`=smashed.

```asm
;+++
; br_super — one-line description
;
; d0   cr  error code
; a3   c p pointer to linkage block
; a5   c u updated pointer
;
; status  standard return
;---
```

---

## 4. Addressing Modes (68000/68008)

| Syntax             | Name                                  | Notes |
|---------------------|-----------------------------------------|-------|
| `Dn`                | Data register direct                    | |
| `An`                | Address register direct                 | `.W`/`.L` only |
| `(An)`              | Address register indirect               | |
| `(An)+`             | Indirect, post-increment                | step size = `.B/.W/.L` |
| `-(An)`             | Indirect, pre-decrement                 | manual stack use |
| `(d16,An)`          | Indirect + 16-bit displacement           | |
| `(d8,An,Xn.T)`      | Indexed + 8-bit displacement             | `Xn.T` = index reg, `.W` or `.L` |
| `(d16,PC)`          | PC-relative                              | **key for relocatable code** |
| `(d8,PC,Xn.T)`      | PC-relative indexed                      | same |
| `xxxx.W` / `xxxx.L` | Absolute short/long                      | avoid in relocatable ROM |
| `#imm`              | Immediate                                | |
| `SR`, `CCR`, `USP`  | Special registers                        | supervisor required (except CCR) |

**QL rule:** all code residing in expansion ROM, Things, or dynamically
linked procedures **must be position-independent**: use `(d16,PC)` for
literals/tables, use `BSR`/`BRA` instead of absolute `JSR`/`JMP`, and never
hard-code the routine's own load address.

---

## 5. Calling Conventions — Overview

### 5.1 The five QDOS TRAPs

| Trap | Purpose |
|------|---------|
| `TRAP #0` | Enter supervisor mode (no params; switches active SP only) |
| `TRAP #1` | **Manager traps** — jobs, memory, clock, system control |
| `TRAP #2` | **I/O management traps** — resource-allocating I/O (open/close channel) |
| `TRAP #3` | **I/O traps** — non-resource-allocating I/O (read/write) |
| `TRAP #4` | Special trap for the SuperBASIC interpreter (A6-relative addressing) |
| `TRAP #5`–`#15` | Free / user-redirectable via `SMS.EXV` / `MT.TRAPV` |

### 5.2 General parameter convention

- Function code in **D0** (typically `MOVEQ #code,D0`).
- Parameters in `A0–A3` and `D1–D3`.
- **D4–D7 and A4–A6 are always preserved**, unless explicitly documented
  otherwise for a specific trap.
- Return: **D0** = 0 (success), negative (system error code), or positive
  with bit 31 set (pointer to an error string, offset from `$8000`).
- **The Zero flag does not always reflect the error state** — always test
  with `TST.L D0` immediately after the `TRAP`, never rely on condition
  codes left by the TRAP itself.

### 5.3 Supervisor mode

- `TRAP #0` enters supervisor; only switches the active stack pointer (uses
  SSP thereafter).
- Supervisor stack budget per job: **64 bytes** (SMSQ/E allows 512).
- "Atomic" calls (most TRAP #1 and TRAP #3 calls with timeout=0) do not yield
  the CPU; do not nest long-running operations inside supervisor mode.
- Privileged instructions (`STOP`, full-SR access, `RESET`) are supervisor-
  only; in user mode they raise **Privilege Violation**.

---

## 6. QL Memory Map

### 6.1 Physical map (hardware view, 1 MB total)

| Range              | Contents                                        |
|---------------------|--------------------------------------------------|
| `$00000–$0BFFF`     | Internal ROM (48 KB)                              |
| `$0C000–$0FFFF`     | Plug-in ROM cartridge (16 KB)                     |
| `$10000–$17FFF`     | Internal I/O (partially decoded)                  |
| `$18000–$1801F`     | ZX8301 / ZX8302 registers (see §6.3)              |
| `$20000–$27FFF`     | Screen RAM (32 KB)                                |
| `$28000–$3FFFF`     | On-board user RAM (96 KB, unexpanded QL)          |
| `$40000–$BFFFF`     | Expansion RAM (up to 512 KB additional)           |
| `$C0000–$DFFFF`     | Add-on peripherals (8 slots × 16 KB)              |
| `$E0000–$FFFFF`     | Expansion ROM (up to 128 KB)                      |

On a system with **less than 1 MB total RAM** (e.g. 128 KB, 256 KB, 640 KB),
user RAM spans from `$28000` up to `SYS_RAMT` (a system variable set at
boot). **Never assume a fixed top of RAM — always read `SYS_RAMT`.**

### 6.2 Logical RAM layout (bottom to top)

```
SYS_RAMT ----→ Top of RAM
               │ Resident Procedure Area   (grows downward)
SV_RESPR ----→ ┤
               │ Transient Program Area (Jobs)
SV_TRNSP ----→ ┤
               │ SuperBASIC Area
SV_BASIC ----→ ┤
               │ Free Area / slave blocks (filing system)
SV_FREE  ----→ ┤
               │ Common Heap                (grows upward)
SV_HEAP  ----→ ┤
               │ System management tables
               │ System variables       ← base = SV_BASE (via SMS.INFO)
$28000   ----→ ┤
               │ Screen RAM (32 KB)
$20000   ----→ ┘
```

- System variable base: **always obtained via `SMS.INFO`** (D0=$00,
  `TRAP #1`) → returns pointer in `A0`. Never hard-code `$28000`.
- The common heap grows upward; the areas above it (BASIC, transient,
  resident) grow downward, squeezing the "free area" in between.

### 6.3 Hardware registers (ZX8301/ZX8302)

| Address   | Read                          | Write                       |
|-----------|--------------------------------|-------------------------------|
| `$18000`  | Real-time clock byte 0         | Clock reset                   |
| `$18001`  | Clock byte 1                   | Clock step                    |
| `$18002`  | Clock byte 2                   | Transmit control               |
| `$18003`  | Clock byte 3                   | IPC link control                |
| `$18020`  | Microdrive/RS232 status         | Microdrive control              |
| `$18021`  | Interrupt/IPC link status       | Interrupt control                |
| `$18022`  | Microdrive data (track 1)       | Microdrive/RS232 data           |
| `$18023`  | Microdrive data (track 2)       | Display control                  |
| `$18063`  | —                               | Display control register (write-only) |

**Rule:** direct access to these registers is **discouraged**; always go
through TRAPs/vectors (`SMS.HDOP`, `SMS.DMOD`, `SMS.COMM`, `MD.*`). A
mistimed direct access can hang the system (the IPC link is serial and
unprotected).

---

## 7. Register Conventions by Calling Context

### 7.1 User TRAP calls

- Rules from §5.2 always apply.
- Do not assume D0–D3/A0–A3 are preserved — they are working registers.

### 7.2 Vectored routines (ROM table, base `$C0`)

```asm
        MOVE.W  #vector,An
        JSR     (An)
```
or, for entries marked with `$4000` offset:
```asm
        MOVE.W  #vector,An
        JSR     $4000(An)
```
- `An` used: any register not required by that specific routine.
- No universal error convention: some return an error code in D0, others use
  **multiple alternative return addresses** (`BRA.S` after the call,
  selected by outcome) — **always check the specific routine's
  documentation**.

### 7.3 Device drivers

Standard registers across **all** physical-layer and access-layer calls:

| Register | Constant content |
|----------|--------------------|
| A3       | base of device driver definition block |
| A6       | pointer to system variables |
| A7       | supervisor stack (max 64 bytes usable) |

**Open channel** routine:
- In: `A0` = pointer to device name, `D3` = access code.
- Out: `A0` = channel definition block, `D0` = error code (0 = OK).
- **`A0` must not be modified except to return the result.**

**I/O** routine:
- In: `D0` = IOSS trap code, `D1/D2` = extra info, `D3` = 0 on first call /
  `-1` on retries, `A0` = channel block, `A1/A2` = extra info.
- Must return `ERR.NC` (not complete) if it cannot finish immediately.
- Registers preserved: `A0, A2, A3, A4, A5, A6`. `D0` always holds the
  result.

### 7.4 SuperBASIC interface (machine-code procedures/functions)

- `A6` points to the base of the SuperBASIC work area (**movable** — may
  change between instructions). All access to that area must be relative to
  `A6` or `A7`.
- **Forbidden:** saving `A6` to a variable, using it in arithmetic, or
  altering it. It may only be changed temporarily by entering supervisor
  mode (`TRAP #0`) and must be restored before returning to user mode.
- Stack budget inside a routine called from BASIC: **128 bytes**.
- `D0` returned = error code (long) at end of PROC/FN.
- `D1–D7` and `A0–A5` are volatile; nothing guaranteed after the call.
- `A3` points to the name-table entry of the first parameter, `A5` to the
  last; `(A5-A3)/8` = number of parameters.

### 7.5 Interrupt tasks (physical layer)

Called with:

| Register | Content |
|----------|---------|
| D3       | number of 50/60 Hz interrupts since last call (scheduler loop only) |
| A3       | base of device driver definition block |
| A6       | system variables |
| A7       | supervisor stack (64 bytes) |

Rules:
- Interrupt tasks **must not allocate/release memory**.
- Must check whether the interrupt is theirs before acting.
- Always return with `RTS`; may smash D0–D7/A0–A6.

---

## 8. Exceptions and Vectors

| Offset | Exception |
|--------|-----------|
| `$00`  | Address error |
| `$04`  | Illegal instruction |
| `$08`  | Divide by zero |
| `$0C`  | CHK |
| `$10`  | TRAPV |
| `$14`  | Privilege violation |
| `$18`  | Trace |
| `$1C`  | Level 7 interrupt |
| `$20`–`$48` | TRAP #5 through TRAP #15 (one longword each, 4-byte step) |

- Per-job redirection via `MT.TRAPV`/`SMS.EXV` (`TRAP #1`, `D0=$07`): table of
  longwords, one address per exception, in the order above.
- Any exception-handling routine automatically enters supervisor mode and
  **must return with `RTE`**, never `RTS`.
- **Bus error is not supported** by QL hardware (no external detection
  logic).
- The 68008 raises **Address Error** on any word/long access at an odd
  address: watch alignment of all tables and buffers.

---

## 9. Memory Management on Systems with <1 MB RAM

### 9.1 Principles

- No MMU ⇒ no virtual memory, no post-load relocation: **any allocated block
  stays fixed until explicitly freed**.
- The common heap grows upward from `SV_HEAP`; all other areas grow
  downward. On low-RAM machines the gap between them is critical.

### 9.2 Allocation

| Trap | Purpose |
|------|---------|
| `TRAP #1 D0=$18` (`SMS.ACHP`) | Allocate in common heap |
| `TRAP #1 D0=$19` (`SMS.RCHP`) | Release from common heap |
| `TRAP #1 D0=$0C` (`SMS.ALHP`) | Allocate in generic heap (atomic, A6-based) |
| `TRAP #1 D0=$0D` (`SMS.REHP`) | Return space to generic heap |
| `TRAP #1 D0=$0E` (`SMS.ARPA`) | Allocate in resident procedure area |
| Vector `MEM.ACHP`/`MEM.RCHP` | Same as SMS.ACHP/RCHP, callable from supervisor without a trap |

- `SMS.ARPA` may only be called **while the transient program area is
  empty** (typically immediately after boot).
- The size requested from `SMS.ACHP`/`MEM.ACHP` must include the heap header
  (16 bytes for simple entries, 24 bytes for IOSS channels).

### 9.3 Practical rules for scarce RAM

1. **Reuse buffers**: avoid duplicating translation tables or character
   fonts if the system already provides them (`SD.FOUNT`/`IOW.FONT` support
   default fonts at no extra memory cost).
2. **Resident procedure area** should only hold truly permanent code — once
   added it cannot be freed without a reboot.
3. **Pack tables tightly**: use bytes instead of words/longs whenever the
   value range allows it.
4. **Do not duplicate stack usage**: the 64-byte supervisor and 128-byte
   BASIC-call stack limits exist for a reason — respect them to avoid
   corrupting adjacent structures.
5. **Always check `ERR.OM`** (out of memory, `-3`) after any
   `SMS.ACHP`/`ALHP`/`ARPA` call before proceeding.
6. **Never assume a fixed memory map**: read `SYS_RAMT`, `SV_HEAP`,
   `SV_FREE`, `SV_BASIC`, etc. from system variables, never hard-code them —
   the same binary must work on 128 KB or 640 KB machines.

---

## 10. Key System Variables (offset from base, via `SMS.INFO`)

| Offset  | Name         | Size   | Description |
|---------|--------------|--------|--------------|
| `$0000` | `SYS_IDNT`   | long   | system identifier |
| `$0004` | `SYS_CHPB`   | long   | common heap base |
| `$0008` | `SYS_CHPF`   | long   | common heap free-space pointer |
| `$000C` | `SYS_FSBB`   | long   | slave block area base |
| `$0010` | `SYS_SBAB`   | long   | SuperBASIC area base |
| `$0014` | `SYS_TPAB`   | long   | transient program area base |
| `$0018` | `SYS_TPAF`   | long   | transient program area free space |
| `$001C` | `SYS_RPAB`   | long   | resident procedure area base |
| `$0020` | `SYS_RAMT`   | long   | top of user RAM (+1) |
| `$0038` | `SYS_EXIL`   | long   | external interrupt task list |
| `$003C` | `SYS_POLL`   | long   | polling task list |
| `$0040` | `SYS_SHDL`   | long   | scheduler loop task list |
| `$0044` | `SYS_IODL`   | long   | I/O driver list |
| `$0048` | `SYS_FSDL`   | long   | directory driver list |
| `$0060` | `SYS_JBTG`   | word   | next job tag |
| `$0068` | `SYS_JBTB`   | long   | job table base |
| `$0070` | `SYS_CHTG`   | word   | next channel tag |
| `$0078` | `SYS_CHTB`   | long   | channel table base |
| `$00B8` | `SYS_THGL`   | long   | Thing list pointer |
| `$0180` | —            | —      | supervisor stack start (768-byte reserved area) |

**All** offsets are relative to what `SMS.INFO` returns in `A0`. None of them
are safe as portable constants across ROM versions.

---

## 11. Quick Reference — Most-Used TRAPs

### 11.1 TRAP #1 — Manager (D0 = function code)

| D0    | Name         | Function |
|-------|--------------|----------|
| `$00` | `SMS.INFO`   | System info; A0→system variables |
| `$01` | `SMS.CRJB`   | Create job |
| `$04` | `SMS.RMJB`   | Remove inactive job |
| `$05` | `SMS.FRJB`   | Force-remove job |
| `$06` | `SMS.FRTP`   | Largest free space in transient area |
| `$07` | `SMS.EXV`    | Set per-job exception vector table |
| `$0A` | `SMS.ACJB`   | Activate job |
| `$0B` | `SMS.SPJB`   | Change job priority |
| `$0C` | `SMS.ALHP`   | Allocate in heap (atomic, A6-based) |
| `$0D` | `SMS.REHP`   | Release in heap (atomic, A6-based) |
| `$0E` | `SMS.ARPA`   | Allocate resident area |
| `$11` | `SMS.HDOP`   | Hardware-dependent operation (IPC) |
| `$12` | `SMS.COMM`   | Set baud rate |
| `$13`/`$14`/`$15` | `SMS.RRTC`/`SRTC`/`ARTC` | Read/set/adjust clock |
| `$18`/`$19` | `SMS.ACHP`/`RCHP` | Allocate/release common heap |
| `$1A`–`$23` | `SMS.LEXI/RXI/LPOL/RPOL/LSHD/RSHD/LIOD/RIOD/LFSD/RFSD` | (Un)link tasks and drivers |

### 11.2 TRAP #2 — I/O Management (resource-allocating)

| D0    | Name       | Function |
|-------|------------|----------|
| `$01` | `IOA.OPEN` | Open channel |
| `$02` | `IOA.CLOS` | Close channel |
| `$03` | `IOA.FRMT` | Format medium |
| `$04` | `IOA.DELF` | Delete file |

### 11.3 TRAP #3 — I/O (non-resource-allocating)

| D0    | Name       | Function |
|-------|------------|----------|
| `$00` | `IOB.TEST` | Test for pending input |
| `$01` | `IOB.FBYT` | Fetch a byte |
| `$02` | `IOB.FLIN` | Fetch line (up to LF) |
| `$03` | `IOB.FMUL` | Fetch string of bytes |
| `$05` | `IOB.SBYT` | Send a byte |
| `$07` | `IOB.SMUL` | Send string of bytes |
| `$0C`/`$0D` | `IOW.DEFB`/`DEFW` | Define border/window |
| `$18`–`$1F` | `IOW.SCRA/SCRT/SCRB/PANA/…` | Window scroll/pan |
| `$20`–`$24` | `IOW.CLRA/CLRT/CLRB/CLRL/CLRR` | Clear window areas |
| `$30`–`$36` | `IOG.DOT/LINE/ARC/ELIP/SCAL/FILL/SGCR` | Graphics |
| `$40`–`$4F` | `IOF.CHEK…IOF.XINF` | File operations |

Uniform convention across all I/O traps: `A0` = channel ID, `D3.W` = timeout,
return in `D0` (0 = OK, negative = error, `ERR.NC` = not complete, retry).

---

## 12. Quick Reference — Vectored Routines (table at `$C0`)

| Vector  | Name       | Function |
|---------|------------|----------|
| `$C0`   | `MEM.ACHP` | Allocate common heap (no trap) |
| `$C2`   | `MEM.RCHP` | Release common heap |
| `$C4`/`$C6`/`$C8` | `UT.WINDW`/`UT.CON`/`UT.SCR` | Create window/console/screen |
| `$D8`/`$DA` | `MEM.ALLOC`/`MEM.LNKFR` (or `MM.ALHP`/`MM.REHP`) | Generic heap |
| `$E8`/`$EA` | `IOU.SSQ`/`IOU.SSIO` | Standard serial I/O for drivers |
| `$110`  | `SB.INIPR`/`BP.INIT` | Link procedures/functions into SuperBASIC |
| `$112`–`$118` | `SB.GTINT/GTFP/GTSTR/GTLIN` | Fetch BASIC parameters onto arithmetic stack |
| `$120`  | `SB.PUTP`/`BP.LET` | Assign value to BASIC parameter/variable |
| `$122`  | `IOU.DNAM` | Decode device name |
| `$124`–`$12A` | `MD.READ/WRITE/VERIF/RDHDR` | Direct Microdrive access |

Convention: working `An` free per §7.2; addresses relative to `A6` whenever
documented as such (SuperBASIC/arithmetic routines).

---

## 13. Programming Guidelines — Checklist

1. **Alignment**: any `.W`/`.L` destination must be at an even address.
   `DC.W`/`DC.L` following an odd-length `DC.B` needs manual padding.
2. **Relocatability**: no absolute addresses embedded in ROM/Things; use
   `(d16,PC)` and `BSR`/`BRA`.
3. **Register preservation**: always follow the table for the active context
   (§7); document any published routine with a `c/r/p/u/s` header.
4. **Error checking**: `TST.L D0` after every TRAP; do not trust condition
   codes left by the TRAP itself.
5. **Stack budgets**: max 64 bytes in supervisor mode (classic QDOS), max
   128 bytes in routines called from SuperBASIC.
6. **A6 in BASIC context**: never save it, never operate on it except inside
   a `TRAP #0` / immediate-restore section.
7. **Dynamic memory**: always check `ERR.OM` (-3); free at every exit path
   (including error paths) to avoid leaks — critical with <1 MB total RAM.
8. **No direct hardware access** (`$18000`–`$18063`) unless strictly
   documented as necessary; always prefer the equivalent TRAP/vector.
9. **Interrupts**: physical-layer interrupt tasks must not allocate memory
   and must confirm the interrupt is theirs before processing it.
10. **Exceptions**: routines installed via `SMS.EXV` end with `RTE`, never
    `RTS`; must save/restore every register they use.
11. **Code size**: on <1 MB systems, minimize duplication — share routines
    via `XREF`/linked `_rel` libraries, do not copy-paste code between
    source files.
12. **Device names**: always decode with `IOU.DNAM`, never hand-parse
    channel-open strings.

---

## 14. Assembler Expression Operator Precedence (EQU/DC expressions)

Highest to lowest precedence, typical for QMAC:
1. Parentheses `( )`
2. Unary `+`/`-`, `~` (bitwise NOT)
3. `*`, `/` (integer multiply/divide)
4. `+`, `-` (add/subtract)
5. Shifts `<<`/`>>` (if supported by the assembler)
6. `&` (bitwise AND), `!`/`|` (OR), `^` (XOR)

**Note:** these are compile-time assembler-expression operators, not to be
confused with 68000 runtime operations (`AND.B`, `OR.W`, etc.), which are
encoded as ordinary mnemonics.

---

## 15. Common Error Code Summary (negative D0)

| Code   | Constant    | Meaning |
|--------|-------------|---------|
| `-1`   | `ERR.NC`    | Operation not complete (retry) |
| `-2`   | `ERR.IJOB`  | Invalid job |
| `-3`   | `ERR.OM`    | Out of memory |
| `-4`   | `ERR.OR`    | Out of range |
| `-5`   | `ERR.BO`/`ERR.BFFL` | Buffer full/overflow |
| `-6`   | `ERR.NO`/`ERR.ICHN` | Channel not open |
| `-7`   | `ERR.NF`/`ERR.ITNF` | File/item not found |
| `-8`   | `ERR.EX`    | File already exists |
| `-9`   | `ERR.IU`/`ERR.FDIU` | Device/file in use |
| `-10`  | `ERR.EF`    | End of file |
| `-12`  | `ERR.BN`/`ERR.INAM` | Invalid device/file name |
| `-15`  | `ERR.BP`/`ERR.IPAR` | Invalid parameter |
| `-18`  | `ERR.OV`    | Arithmetic overflow |
| `-19`  | `ERR.NI`/`ERR.NIMP` | Not implemented |

---

## 16. Notes for LLM-Assisted Code Generation

- When the user asks for a routine that calls a TRAP not listed in §11/§12,
  respond that the exact D0 code / register convention is not in this
  reference and should be verified against the full QDOS/SMS reference
  manual before committing to hardware.
- Default assumption for any new user-written subroutine, unless told
  otherwise: **D0 returns an error code, D1–D3/A0–A3 are scratch, D4–D7/A4–A6
  are preserved** — this mirrors the QDOS trap convention and is a safe
  default for QL-targeted code.
- Default assumption for stack discipline in generated code: keep local
  stack frames small (well under 64 bytes) unless the routine is confirmed
  to run in user mode with a normal job stack.
- When memory allocation is required, generate calls that check `D0` for
  `ERR.OM` (`-3`) and branch to an explicit error path — do not silently
  continue on allocation failure.
- Prefer `MOVEQ` over `MOVE.L #n,Dn` for small immediate loads (`-128..127`)
  — this is idiomatic in QDOS-era QL source and saves code size, relevant on
  <1 MB systems.
- When asked to write reusable/library code, always emit the `;+++ / ;---`
  register-role header block from §3.5.

---

*End of condensed manual. Reference material derived from the official
QDOS/SMS documentation and the QL Software Developer's Guide (Sinclair
Research / Tony Tebby, David Karlin). For full detail on any individual
trap, vector, or data structure, consult the complete original
documentation — this file intentionally omits rarely-used calls to stay
within a compact context budget.*
