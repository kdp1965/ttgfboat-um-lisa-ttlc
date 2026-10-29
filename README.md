![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg)

## LISA (Little ISA) 8-bit microcontroller SoC on GF180

The third LISA chip ([ttsky26d-um-lisa-ttlc](https://github.com/kdp1965/ttsky26d-um-lisa-ttlc),
rc30) ported to GF180 for the Tiny Tapeout "Best Of All Time" shuttle:
the same RTL without the BF16 unit and the TTLC (GF180's cells are three
times sky130's, and the whole design did not fit the 4x4 tile, the largest
there is), hardened on gf180mcuD (the 7-track library at 3.3 V).  What the port changed, the area
arithmetic that dropped BF16, the GF180 RAM32 macro and the hardening are
in [GF180.md](GF180.md); the design's history - the TT07 silicon's issues
and the second and third chips' fixes and extensions - is
[RESPIN.md](RESPIN.md) and [REV3.md](REV3.md), carried over as they were.

LISA is a microcontroller built around a custom 8-bit accumulator core
(16-bit instructions, 15-bit program counter, Harvard), with:

   - a debug interface on a UART (auto-detected port and baud rate): registers,
     halt / resume / breakpoints, RAM access, (Q)SPI flash erase and program
   - a (Q)SPI arbiter with four channels: debugger, LISA instruction fetch,
     LISA data (through the data cache), the WS2812B driver's DMA; two chip
     enables, each SPI or QSPI, flash or RAM, 16- or 24-bit addresses,
     programmable SCLK divider, CE delay, dummy cycles and base addresses;
     DDR (EDh) instruction reads from a DTR flash as an option
   - 128 bytes of on-chip RAM, used directly or as an 8-line data cache in
     front of a 32 KB SPI RAM
   - a streaming instruction fetch (`inst_stream.v`: the flash read is kept
     open and the core runs from a window of 8 words)
   - UART (shared with the debugger), a dedicated UART2, two 16-bit timers,
     Timer 3 (PWM, capture, PDM), an 8-bit input port, 8-bit output port,
     4-bit bidirectional port, I2C master, SPI master, a WS2812B driver with
     DMA, a cycle counter
   - 8x8 multiplier, 16/16 divider (the sky130 chips' BF16 unit is not on
     this one: GF180.md)
   - (the sky130 chips' TTLC, the MC14500B-compatible logic controller with
     its 74HC595 / 74HC165 chains, is not on this one: GF180.md; its I/O
     block's output bytes 0-5 remain as the WS2812B driver's pixel store)
   - an I/O mux for the pinout

The datasheet text is [docs/info.md](docs/info.md); the instruction set is
described in `lisa_isa.md` in the workspace above this repository.

## Layout

```
src/            the RTL (info.yaml lists the files); src/config.json is the LibreLane config
test/           cocotb testbench: the DUT with a SPI flash model (firmware.hex), a SPI RAM
                model and a UART on the debug port; run_suite.sh runs the SDCC suite
docs/           datasheet (info.md and its figures)
macros/         the RAM32 DFFRAM macro for gf180mcuD (GDS, LEF, libs, netlist, SPEF)
harden/         the local LibreLane flow: configure.py, flow.py (+ the macro's stripe step),
                macro.json, the 4x4 floorplan template
fpga/           the Arty A7 build of the same RTL (Vivado)
gds/ lef/ pnl/  the hardened tile, what the gds workflow submits
```

## Building

`harden/` hardens the design on this machine with LibreLane (the GitHub
runners are an order of magnitude slower than the Mac). It needs a LibreLane
checkout with its nix dev shell (`LIBRELANE`, default
`~/projects/tiny_tapeout/librelane`) and the gf180mcuD PDK the Tiny Tapeout
GF180 action enables, open_pdks 54435919 (`ciel enable --pdk-family
gf180mcu 54435919abffb937387ec956209f9cf5fd2dfbee`; harden/Makefile names
its version directory as `PDK_ROOT`, because a newer one the ciel symlink
may point at is read by this LibreLane with an empty cell library):

```sh
make -C harden macro      # the RAM32 DFFRAM macro (macros/) placed by harden/macro.json
make -C harden            # the standard Tiny Tapeout flow: the RAM synthesized from src/RAM32.v
make -C harden synth      # synthesis only: the area (runs/synth-<tag>/*-yosys-synthesis/reports)
make -C harden shell      # the nix shell itself
make -C harden macro TO=OpenROAD.GlobalRouting   # stop after the congestion report
make -C harden macro OVERLAY=trial.json          # a trial: that JSON's variables merged last
make -C harden status [RUN=runs/<tag>]           # a run's steps and the router's progress
```

`configure.py` builds the configuration the way tt-support-tools'
`tt_tool.py --create-user-config --gf` does (the sources, the tile's die
area and floorplan template, the 3.3 V corners) over `src/config.json`,
with `macro.json` on top for the macro flow; `flow.py` runs LibreLane's
Classic flow with one extra step for the macro (`Tile.ExtendPowerStripes`,
`odb_stripes.py`: the tile's Metal4 power stripes drawn full height over
the macro's pin columns, which the single-layer tile PDN does not reach by
itself; `pdn_macro.tcl` first gives any macro pin column off the stripe
grid a stripe of its own).  The macro sits with its origin x on the tile's
stripe grid (x = 2.24 + k x 38.87 um) so its columns are the tile's.
Results: `harden/runs/<tag>/final/`; the build to submit is copied to
`gds/`, `lef/` and `pnl/` and pushed: the `gds` workflow publishes it with
`custom_gds@ttgf26c`, runs the Tiny Tapeout precheck and deploys the
viewer.  The RAM32 macro itself is built in DFFRAM.librelane
(`python3 dffram.py --pdk gf180mcuD -b ram_ao -C 30 32x32`, GF180.md).

The timing constraints are `src/lisa.sdc`: LibreLane's `base.sdc` (the
clock from `CLOCK_PERIOD`, 40 ns here - the chip is specified at 45 ns, 22.2 MHz, see GF180.md) plus the core's multi-cycle paths
(what the PC, the instruction window, the registered instruction, the
breakpoint latches and the debugger's registers reach is written two or
three clocks later).  The registers are found through their Q nets, so
there is no netlist renaming step; every STA log opens with `lisa.sdc: pc
15 win_count 4 ...`, the registers each group resolved to.

On GitHub, `test.yaml` runs the chip-level testbench under icarus on every
push, `docs.yaml` builds the datasheet, and `gds.yaml` publishes the
committed GDS as the submission's artifact with the precheck and the
viewer, all at the ttgf26c actions (the shuttle's own standard flow,
hardening in the action, cannot place the macro).

## Testing

```sh
cd test && make          # RTL, icarus + cocotb (2.1 in CI; 1.9 works too)
make GATES=yes           # gate level, with gate_level_netlist.v from the harden
```

The testbench (`test/tb.v`) wires `tt_um_pettit_lisa` to a SPI flash model loaded
from `firmware.hex`, a SPI RAM model on CE1 and a UART on the auto-detected
debug port; `test.py` checks the debugger answers. The program-level tests
(the SDCC suite through the flash model, the data cache through the RAM
model) are part of the work in RESPIN.md.

The board-side tools - the LISA Commander web app, `uartPass.py`, the
hardware test - stay in `tt07-um-lisa-ttlc/lisa-test`; the debugger protocol
is unchanged, so they serve this chip too.

## What is Tiny Tapeout?

Tiny Tapeout is an educational project that aims to make it easier and cheaper than ever to get your digital and analog designs manufactured on a real chip.
To learn more and get started, visit https://tinytapeout.com.

- [FAQ](https://tinytapeout.com/faq/)
- [Build your design locally](https://www.tinytapeout.com/guides/local-hardening/)
- [Join the community](https://tinytapeout.com/discord)
